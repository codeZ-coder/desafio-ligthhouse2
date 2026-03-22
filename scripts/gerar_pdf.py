"""
Gera um PDF tecnico bonito a partir de docs/desafio_respondido.md
com suporte a imagens inline via ![alt](path).

Uso:
    python -u scripts/gerar_pdf.py
    python -u scripts/gerar_pdf.py --input docs/desafio_resposta_banca_final.md --output docs/desafio_resposta_banca_final.pdf
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import html
import re
import unicodedata
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY  = colors.HexColor("#1B3A5C")
TEAL  = colors.HexColor("#0E7C86")
LIGHT = colors.HexColor("#D5E8F0")
GRAY  = colors.HexColor("#F5F5F5")
DKGRAY= colors.HexColor("#333333")
WHITE = colors.white
W     = 17.0 * cm
REQUIRED_QUESTOES = tuple(range(1, 9))


def make_styles():
    base = getSampleStyleSheet()
    add = lambda name, **kw: base.add(ParagraphStyle(name, **kw))
    add("Title1",    fontName="Helvetica-Bold",   fontSize=24, textColor=NAVY,   leading=28, spaceAfter=6)
    add("Title2",    fontName="Helvetica",         fontSize=12, textColor=TEAL,   leading=15, spaceAfter=10)
    add("H1",        fontName="Helvetica-Bold",   fontSize=14, textColor=NAVY,   leading=18, spaceBefore=10, spaceAfter=6)
    add("H2",        fontName="Helvetica-Bold",   fontSize=11, textColor=TEAL,   leading=14, spaceBefore=8,  spaceAfter=4)
    add("H3",        fontName="Helvetica-Bold",   fontSize=10, textColor=DKGRAY, leading=13, spaceBefore=6,  spaceAfter=2)
    add("Body",      fontName="Helvetica",         fontSize=9.5,textColor=DKGRAY, leading=14, alignment=TA_JUSTIFY, spaceAfter=4)
    add("List",      fontName="Helvetica",         fontSize=9.5,textColor=DKGRAY, leading=13, leftIndent=12, bulletIndent=2, spaceAfter=2)
    add("Quote",     fontName="Helvetica-Oblique", fontSize=9,  textColor=TEAL,   leading=13, leftIndent=12, spaceAfter=4)
    add("Small",     fontName="Helvetica",         fontSize=8,  textColor=colors.HexColor("#777777"), leading=10)
    add("SmallItal", fontName="Helvetica-Oblique", fontSize=8,  textColor=colors.HexColor("#777777"), leading=10, alignment=TA_CENTER)
    add("CodeBlock", fontName="Courier",            fontSize=8.3,textColor=colors.HexColor("#1f2937"), leading=10.8)
    add("Center",    fontName="Helvetica",         fontSize=9,  textColor=DKGRAY, alignment=TA_CENTER)
    return base


S = make_styles()


def section_header(text: str, color=NAVY):
    p = Paragraph(f"<font color='white'><b>{html.escape(text)}</b></font>", S["Center"])
    t = Table([[p]], colWidths=[W])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), color),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return t


def hr():
    return HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=4, spaceAfter=6)


def _inline_md_to_rl(text: str) -> str:
    esc = html.escape(text)
    esc = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc)
    esc = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", esc)
    return esc


def _safe_mono_text(text: str) -> str:
    text = text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2500", "-")
    return unicodedata.normalize("NFKD", text).encode("ascii", errors="ignore").decode("utf-8")


def _normalize_search(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.lower()
    return re.sub(r"\s+", " ", folded).strip()


def _parse_markdown_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for ln in lines:
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        rows.append(cells)
    return rows


def _table_flowable(rows: list[list[str]]):
    if not rows:
        return None
    col_count = max(len(r) for r in rows)
    normalized = [r + [""] * (col_count - len(r)) for r in rows]
    data = []
    for i, row in enumerate(normalized):
        rendered = []
        for cell in row:
            val = _inline_md_to_rl(cell)
            if i == 0:
                rendered.append(Paragraph(f"<b>{val}</b>", S["Center"]))
            else:
                rendered.append(Paragraph(val, S["Body"]))
        data.append(rendered)
    widths = [W / col_count] * col_count
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("GRID",          (0,0), (-1,-1), 0.25, colors.HexColor("#CFCFCF")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, GRAY]),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t


def _embed_image(img_path: Path, alt: str, story: list):
    """Embeda imagem no PDF com caption."""
    if not img_path.exists():
        story.append(Paragraph(f"(Imagem não encontrada: {img_path})", S["Small"]))
        return
    try:
        reader = ImageReader(str(img_path))
        iw, ih = reader.getSize()
        ratio = ih / iw if iw else 0.56
        target_w = W
        target_h = min(target_w * ratio, 13.5 * cm)
        story.append(Spacer(1, 6))
        story.append(Image(str(img_path), width=target_w, height=target_h))
        if alt:
            story.append(Paragraph(f"<i>{html.escape(alt)}</i>", S["SmallItal"]))
        story.append(Spacer(1, 8))
    except Exception as e:
        story.append(Paragraph(f"(Erro ao renderizar imagem: {e})", S["Small"]))


def _resolve_ref_path(path_token: str, base: Path, md_base: Path) -> Path:
    p = Path(path_token.strip())
    if p.is_absolute():
        return p.resolve()

    p_posix = Path(str(p).replace("\\", "/"))
    roots = [
        md_base,
        base,
        base / "data" / "processed",
        base / "arquivos" / "data" / "processed",
        base / "docs",
        base / "arquivos" / "docs",
    ]
    candidates: list[Path] = []
    for root in roots:
        candidates.append((root / p_posix).resolve())

    parts = p_posix.parts
    if parts and parts[0].lower() == "arquivos":
        candidates.append((base / Path(*parts[1:])).resolve())
    if len(parts) >= 2 and parts[0].lower() == "data" and parts[1].lower() == "processed":
        candidates.append((base / "arquivos" / p_posix).resolve())

    return next((c for c in candidates if c.exists()), candidates[0])


def validate_markdown_coverage(md_text: str) -> list[str]:
    normalized = _normalize_search(md_text)
    missing = []
    for q in REQUIRED_QUESTOES:
        if f"questao {q}" not in normalized:
            missing.append(f"Questao {q}")
    return missing


def load_q_summaries(base: Path) -> tuple[dict[str, dict], list[str]]:
    processed = base / "data" / "processed"
    payloads: dict[str, dict] = {}
    missing: list[str] = []
    for q in REQUIRED_QUESTOES:
        key = f"q{q}"
        path = processed / f"{key}_summary.json"
        if not path.exists():
            missing.append(str(path))
            continue
        try:
            payloads[key] = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            missing.append(f"{path} (json invalido)")
    return payloads, missing


def _metric_rows(summaries: dict[str, dict]) -> list[list[str]]:
    def pick(key: str, field: str, default: str = "N/A") -> str:
        value = summaries.get(key, {}).get(field, default)
        if isinstance(value, float):
            return f"{value}"
        return str(value)

    return [
        ["Q1", "total_max", pick("q1", "total_max")],
        ["Q2", "duplicates_removed", pick("q2", "duplicates_removed")],
        ["Q3", "rows_after_normalization", pick("q3", "rows_after_normalization")],
        ["Q4", "top_id_product_percentual_perda", pick("q4", "top_id_product_percentual_perda")],
        ["Q5", "top_categoria_qtd", pick("q5", "top_categoria_qtd")],
        ["Q6", "pior_dia_semana", pick("q6", "pior_dia_semana")],
        ["Q7", "mae_jan_2024", pick("q7", "mae_jan_2024")],
        ["Q8", "id_product_mais_similar", pick("q8", "id_product_mais_similar")],
    ]


def append_automatic_audit_section(
    story: list,
    *,
    input_path: Path,
    output_path: Path,
    coverage_missing: list[str],
    summary_missing: list[str],
    summaries: dict[str, dict],
) -> None:
    story.append(PageBreak())
    story.append(section_header("ANEXO - AUDITORIA AUTOMATICA", TEAL))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Checklist gerado automaticamente na etapa de build do PDF.", S["Body"]))
    story.append(Paragraph(f"Entrada: <font name='Courier'>{html.escape(str(input_path))}</font>", S["Small"]))
    story.append(Paragraph(f"Saida: <font name='Courier'>{html.escape(str(output_path))}</font>", S["Small"]))
    story.append(Paragraph(
        f"Gerado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        S["Small"],
    ))
    story.append(Spacer(1, 5))

    status_rows = [["Verificacao", "Status", "Detalhe"]]
    status_rows.append([
        "Cobertura Q1-Q8 no markdown",
        "OK" if not coverage_missing else "FALHA",
        "completo" if not coverage_missing else ", ".join(coverage_missing),
    ])
    status_rows.append([
        "Artefatos q*_summary.json",
        "OK" if not summary_missing else "FALHA",
        "todos presentes" if not summary_missing else ", ".join(summary_missing),
    ])
    status_tbl = _table_flowable(status_rows)
    if status_tbl is not None:
        story.append(status_tbl)
        story.append(Spacer(1, 6))

    metric_rows = [["Questao", "Variavel", "Valor"]] + _metric_rows(summaries)
    metric_tbl = _table_flowable(metric_rows)
    if metric_tbl is not None:
        story.append(Paragraph("Variaveis-chave derivadas dos JSONs processados:", S["Body"]))
        story.append(metric_tbl)
        story.append(Spacer(1, 6))


def write_audit_json(
    base: Path,
    *,
    input_path: Path,
    output_path: Path,
    coverage_missing: list[str],
    summary_missing: list[str],
    summaries: dict[str, dict],
) -> Path:
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "output": str(output_path),
        "coverage_missing": coverage_missing,
        "summary_missing": summary_missing,
        "metrics": _metric_rows(summaries),
    }
    out = base / "data" / "processed" / "audit_relatorio_final.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _append_file_preview(path: Path, story: list) -> None:
    if not path.exists():
        story.append(Paragraph(f"(Arquivo referenciado nao encontrado: {path})", S["Small"]))
        return

    suffix = path.suffix.lower()
    story.append(Spacer(1, 3))
    story.append(Paragraph(f"<b>Previa:</b> {html.escape(str(path))}", S["Small"]))

    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        _embed_image(path, path.stem, story)
        return

    if suffix == ".json":
        text = path.read_text(encoding="utf-8", errors="ignore")
        try:
            payload = json.loads(text)
            text = json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception:
            pass
        snippet = "\n".join(text.splitlines()[:80])
        story.append(Preformatted(_safe_mono_text(snippet), S["CodeBlock"]))
        story.append(Spacer(1, 5))
        return

    if suffix == ".csv":
        rows = []
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                rows.append(row)
                if i >= 8:
                    break
        tbl = _table_flowable(rows)
        if tbl is not None:
            story.append(tbl)
            story.append(Spacer(1, 5))
        return

    if suffix in {".py", ".sql", ".md", ".txt", ".log"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        snippet = "\n".join(text.splitlines()[:120])
        story.append(Preformatted(_safe_mono_text(snippet), S["CodeBlock"]))
        story.append(Spacer(1, 5))
        return

    story.append(Paragraph("(Sem previa para este tipo de arquivo)", S["Small"]))
    story.append(Spacer(1, 5))


def markdown_to_story(md_text: str, base: Path, md_base: Path):
    story     = []
    lines     = md_text.splitlines()
    i         = 0
    in_code   = False
    code_buf: list[str] = []
    last_kind = "start"
    first_questao = True
    used_images: set[Path] = set()
    missing_images: list[Path] = []
    previewed_files: set[Path] = set()

    def next_nonempty(start_idx: int) -> str:
        j = start_idx
        while j < len(lines):
            s = lines[j].strip()
            if s:
                return s
            j += 1
        return ""

    def append_code_block(code_text: str):
        if not code_text:
            return
        story.append(Preformatted(_safe_mono_text(code_text), S["CodeBlock"]))
        story.append(Spacer(1, 6))

    while i < len(lines):
        line    = lines[i]
        stripped = line.strip()

        # ── Bloco de código por indentação (4 espaços / tab) ──────────────
        if (line.startswith("    ") or line.startswith("\t")) and not in_code:
            indented_buf = []
            while i < len(lines):
                cur = lines[i]
                if cur.startswith("    ") or cur.startswith("\t"):
                    indented_buf.append(cur[4:] if cur.startswith("    ") else cur[1:])
                    i += 1
                    continue
                if cur.strip() == "":
                    indented_buf.append("")
                    i += 1
                    continue
                break
            code_text = "\n".join(indented_buf).rstrip()
            if code_text:
                append_code_block(code_text)
                last_kind = "code"
            continue

        # ── Fence de código ``` ────────────────────────────────────────────
        if stripped.startswith("```"):
            if not in_code:
                in_code   = True
                code_buf  = []
            else:
                code_text = "\n".join(code_buf).rstrip()
                if code_text:
                    append_code_block(code_text)
                    last_kind = "code"
                in_code  = False
                code_buf = []
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # ── Linha vazia ────────────────────────────────────────────────────
        if not stripped:
            if last_kind not in {"start", "spacer", "hr", "section"}:
                story.append(Spacer(1, 3))
                last_kind = "spacer"
            i += 1
            continue

        # ── Separador horizontal ───────────────────────────────────────────
        if stripped in {"---", "***", "___"}:
            nxt = next_nonempty(i + 1)
            if not nxt.startswith("# "):
                story.append(hr())
                last_kind = "hr"
            i += 1
            continue

        # ── Tabela markdown ────────────────────────────────────────────────
        if stripped.startswith("|"):
            tbl_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl_lines.append(lines[i])
                i += 1
            tbl = _table_flowable(_parse_markdown_table(tbl_lines))
            if tbl is not None:
                story.append(tbl)
                story.append(Spacer(1, 6))
                last_kind = "table"
            continue

        # ── IMAGEM INLINE: ![alt](path) ────────────────────────────────────
        img_match = re.match(r'!\[([^]]*)]\(([^)]+)\)', stripped)
        if img_match:
            alt      = img_match.group(1)
            img_rel  = img_match.group(2).strip()
            resolved = _resolve_ref_path(img_rel, base, md_base)

            if resolved.exists():
                used_images.add(resolved)
            else:
                missing_images.append(resolved)

            _embed_image(resolved, alt, story)
            last_kind = "image"
            i += 1
            continue

        # ── Headings ───────────────────────────────────────────────────────
        if stripped.startswith("# "):
            txt       = _inline_md_to_rl(stripped[2:].strip())
            raw_title = re.sub("<[^>]+>", "", txt)
            if "QUESTAO" in raw_title.upper().replace("Ç","C").replace("Ã","A"):
                if not first_questao:
                    story.append(PageBreak())
                first_questao = False
            story.append(section_header(raw_title, NAVY))
            story.append(Spacer(1, 4))
            last_kind = "section"
            i += 1
            continue

        if stripped.startswith("## "):
            txt = _inline_md_to_rl(stripped[3:].strip())
            story.append(Paragraph(txt, S["H1"]))
            last_kind = "h1"
            i += 1
            continue

        if stripped.startswith("### "):
            txt = _inline_md_to_rl(stripped[4:].strip())
            story.append(Paragraph(txt, S["H2"]))
            last_kind = "h2"
            i += 1
            continue

        # ── Blockquote ─────────────────────────────────────────────────────
        if stripped.startswith(">"):
            txt = _inline_md_to_rl(stripped.lstrip("> ").strip())
            story.append(Paragraph(txt, S["Quote"]))
            last_kind = "quote"
            i += 1
            continue

        # ── Lista com bullet ───────────────────────────────────────────────
        if re.match(r"^[-*]\s+", stripped):
            txt = _inline_md_to_rl(re.sub(r"^[-*]\s+", "", stripped))
            story.append(Paragraph(f"• {txt}", S["List"]))

            only_path_bullet = re.match(r"^[-*]\s+`([^`]+)`$", stripped)
            if only_path_bullet:
                ref_path = _resolve_ref_path(only_path_bullet.group(1), base, md_base)
                if ref_path not in previewed_files:
                    _append_file_preview(ref_path, story)
                    previewed_files.add(ref_path)

            last_kind = "list"
            i += 1
            continue

        # ── Parágrafo normal ───────────────────────────────────────────────
        para = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                break
            if (nxt.startswith(("#", "|", "```", ">"))
                    or nxt in {"---","***","___"}
                    or re.match(r"^[-*]\s+", nxt)
                    or re.match(r'!\[', nxt)):
                break
            para.append(nxt)
            i += 1
        story.append(Paragraph(_inline_md_to_rl(" ".join(para)), S["Body"]))

        paragraph_text = " ".join(para)
        if any(k in paragraph_text.lower() for k in ["evidencia", "arquivo enviado", "arquivo:"]):
            for token in re.findall(r"`([^`]+)`", paragraph_text):
                if "/" in token or "\\" in token or "." in token:
                    ref_path = _resolve_ref_path(token, base, md_base)
                    if ref_path not in previewed_files:
                        _append_file_preview(ref_path, story)
                        previewed_files.add(ref_path)

        last_kind = "paragraph"

    return story, used_images, missing_images


def append_graphs_section(story: list, graphs_dir: Path, used_images: set[Path] | None = None) -> None:
    """Anexa graficos extras no final (apenas os que nao foram referenciados inline)."""
    if not graphs_dir.exists():
        return
    imgs = sorted(graphs_dir.glob("*.png"))
    if not imgs:
        return

    used_images = used_images or set()
    imgs_to_append = [img.resolve() for img in imgs if img.resolve() not in used_images]
    if not imgs_to_append:
        return

    story.append(PageBreak())
    story.append(section_header("ANEXO - GRAFICOS ADICIONAIS", TEAL))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Graficos gerados automaticamente pelo pipeline a partir dos dados processados.",
        S["Body"],
    ))
    story.append(Spacer(1, 6))
    for img_path in imgs_to_append:
        story.append(Paragraph(f"<b>{html.escape(img_path.name)}</b>", S["H2"]))
        _embed_image(img_path, img_path.stem.replace("_", " "), story)


def draw_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(2.0 * cm, 1.2 * cm, "LH Nautical - Documentacao Tecnica")
    canvas.drawRightString(A4[0] - 2.0 * cm, 1.2 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


def resolve_input(base: Path, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        resolved = p if p.is_absolute() else (base / p)
        if not resolved.exists():
            raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {resolved}")
        return resolved
    candidates = [
        base / "docs" / "desafio_resposta_banca_final.md",
        base / "arquivos" / "docs" / "desafio_resposta_banca_final.md",
        base / "docs" / "desafio_resposta_final_simples.md",
        base / "arquivos" / "docs" / "desafio_resposta_final_simples.md",
        base / "docs" / "desafio_respondido_passo_a_passo.md",
        base / "arquivos" / "docs" / "desafio_respondido_passo_a_passo.md",
        base / "docs" / "desafio_respondido.md",
        base / "arquivos" / "docs" / "desafio_respondido.md",
        base / "docs" / "desafio_respondido",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("Nao encontrei markdown de entrada em docs/ ou arquivos/docs/. Use --input para informar o arquivo.")


def main():
    parser = argparse.ArgumentParser(description="Gera PDF tecnico do desafio respondido")
    parser.add_argument("--base",       default=None, help="Raiz do projeto")
    parser.add_argument("--input",      default=None, help="Arquivo markdown de entrada")
    parser.add_argument("--output",     default=None, help="Arquivo PDF de saida")
    parser.add_argument("--graphs-dir", default=None, help="Dir de graficos PNG para anexar no final")
    parser.add_argument("--no-annex",   action="store_true", help="Nao gera o anexo de graficos no final")
    parser.add_argument("--no-strict",  action="store_true", help="Permite gerar PDF mesmo com gaps de cobertura/artefatos")
    args = parser.parse_args()

    default_base = Path(__file__).resolve().parents[1]
    base = Path(args.base).resolve() if args.base else default_base

    inp = resolve_input(base, args.input)
    out = (Path(args.output).resolve() if args.output
           else base / "docs" / "desafio_resposta_banca_final.pdf")
    graphs_dir = (Path(args.graphs_dir).resolve() if args.graphs_dir
                  else base / "data" / "processed")

    md_text = inp.read_text(encoding="utf-8", errors="ignore")
    md_base = inp.parent
    out.parent.mkdir(parents=True, exist_ok=True)

    coverage_missing = validate_markdown_coverage(md_text)
    summaries, summary_missing = load_q_summaries(base)

    print(f"[INFO] Markdown selecionado: {inp}")
    if coverage_missing:
        print(f"[WARN] Cobertura incompleta no markdown: {', '.join(coverage_missing)}")
    if summary_missing:
        print("[WARN] Artefatos ausentes/invalidos:")
        for item in summary_missing:
            print(f" - {item}")

    strict = not args.no_strict
    if strict and (coverage_missing or summary_missing):
        raise RuntimeError("Preflight falhou. Corrija os gaps ou rode com --no-strict para forcar a geracao.")

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.8 * cm,
        title="Desafio Respondido - LH Nautical",
        author="LH Nautical",
    )

    story = [
        Paragraph("Desafio Lighthouse - LH Nautical", S["Title1"]),
        Paragraph("Documentacao Tecnica das Respostas", S["Title2"]),
        hr(),
        Spacer(1, 6),
    ]
    content_story, used_images, missing_images = markdown_to_story(md_text, base, md_base)
    story.extend(content_story)

    if not args.no_annex:
        append_graphs_section(story, graphs_dir, used_images)

    append_automatic_audit_section(
        story,
        input_path=inp,
        output_path=out,
        coverage_missing=coverage_missing,
        summary_missing=summary_missing,
        summaries=summaries,
    )

    story.append(Spacer(1, 8))
    story.append(Paragraph("Fim do documento", S["Small"]))

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    audit_path = write_audit_json(
        base,
        input_path=inp,
        output_path=out,
        coverage_missing=coverage_missing,
        summary_missing=summary_missing,
        summaries=summaries,
    )
    print(f"[OK] PDF gerado: {out}")
    print(f"[OK] Auditoria JSON: {audit_path}")
    if missing_images:
        print("[WARN] Imagens nao encontradas:")
        for p in sorted({str(x) for x in missing_images}):
            print(f" - {p}")


if __name__ == "__main__":
    main()

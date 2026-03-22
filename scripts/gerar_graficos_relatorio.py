"""
Gera graficos complementares para o relatorio final do desafio.

Entradas esperadas em data/processed:
- q4_prejuizo_por_produto.csv
- q6_media_por_dia_semana.csv
- q5_top10_clientes_fieis.csv

Saidas em data/processed:
- grafico_prejuizo_produtos.png
- grafico_dias_semana.png
- grafico_clientes_top10_ticket.png
- *_base.csv (bases agregadas para auditoria)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"


def _ensure_columns(df: pd.DataFrame, required: list[str], path: Path) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Arquivo {path.name} sem colunas obrigatorias: {missing}")


def gerar_grafico_prejuizo_produtos() -> Path:
    src = PROC / "q4_prejuizo_por_produto.csv"
    if not src.exists():
        raise FileNotFoundError(f"Arquivo ausente: {src}")

    df = pd.read_csv(src)
    _ensure_columns(df, ["id_product", "prejuizo_total_brl"], src)

    base = df[df["prejuizo_total_brl"] > 0].copy()
    base["prejuizo_abs"] = base["prejuizo_total_brl"].astype(float)
    base = base.nlargest(15, "prejuizo_abs").sort_values("prejuizo_abs", ascending=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(base["id_product"].astype(str), base["prejuizo_abs"], color="#C0392B")
    ax.set_title("Top 15 produtos por prejuizo total")
    ax.set_xlabel("id_product")
    ax.set_ylabel("Prejuizo total (BRL)")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_img = PROC / "grafico_prejuizo_produtos.png"
    out_csv = PROC / "grafico_prejuizo_produtos_base.csv"
    fig.savefig(out_img, dpi=160)
    plt.close(fig)
    base.to_csv(out_csv, index=False)
    return out_img


def gerar_grafico_dias_semana() -> Path:
    src = PROC / "q6_media_por_dia_semana.csv"
    if not src.exists():
        raise FileNotFoundError(f"Arquivo ausente: {src}")

    df = pd.read_csv(src)
    _ensure_columns(df, ["dia_semana", "media_vendas"], src)

    ordem = [
        "Segunda-feira",
        "Terca-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sabado",
        "Domingo",
    ]
    base = df.copy()
    base["ord"] = base["dia_semana"].map({d: i for i, d in enumerate(ordem)})
    base = base.sort_values("ord")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(base["dia_semana"], base["media_vendas"], color="#0E7C86")
    ax.set_title("Media de vendas por dia da semana (com dias sem venda)")
    ax.set_xlabel("Dia da semana")
    ax.set_ylabel("Media de vendas (BRL)")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_img = PROC / "grafico_dias_semana.png"
    out_csv = PROC / "grafico_dias_semana_base.csv"
    fig.savefig(out_img, dpi=160)
    plt.close(fig)
    base.to_csv(out_csv, index=False)
    return out_img


def gerar_grafico_clientes_top10() -> Path:
    src = PROC / "q5_top10_clientes_fieis.csv"
    if not src.exists():
        raise FileNotFoundError(f"Arquivo ausente: {src}")

    df = pd.read_csv(src)
    _ensure_columns(df, ["id_client", "ticket_medio"], src)

    base = df.sort_values("ticket_medio", ascending=False).head(10).copy()
    base["cliente_label"] = "Cliente " + base["id_client"].astype(str)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(base["cliente_label"], base["ticket_medio"], color="#1B3A5C")
    ax.set_title("Top 10 clientes por ticket medio")
    ax.set_xlabel("Ticket medio (BRL)")
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_img = PROC / "grafico_clientes_top10_ticket.png"
    out_csv = PROC / "grafico_clientes_top10_ticket_base.csv"
    fig.savefig(out_img, dpi=160)
    plt.close(fig)
    base.to_csv(out_csv, index=False)
    return out_img


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    generated = [
        gerar_grafico_prejuizo_produtos(),
        gerar_grafico_dias_semana(),
        gerar_grafico_clientes_top10(),
    ]

    print("[OK] Graficos gerados:")
    for p in generated:
        print(f" - {p}")


if __name__ == "__main__":
    main()


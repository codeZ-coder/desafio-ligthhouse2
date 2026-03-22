# ================================================
# LH Nautical Challenge - Questao 5
# Analise de clientes fieis (ticket medio + diversidade)
# ================================================

import json
from pathlib import Path

import pandas as pd
import unidecode
from rapidfuzz import process

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"

CANONICAS = ["eletronicos", "propulsao", "ancoragem"]


def normalizar_categoria(texto: str) -> str:
    texto_limpo = unidecode.unidecode(str(texto).strip().lower()).replace(" ", "")
    match, score, _ = process.extractOne(texto_limpo, CANONICAS)
    return match if score >= 70 else "outros"


def main() -> None:
    vendas = pd.read_csv(RAW_DIR / "vendas_2023_2024.csv")
    produtos = pd.read_csv(RAW_DIR / "produtos_raw.csv")

    produtos["category"] = produtos["actual_category"].apply(normalizar_categoria)
    produtos = produtos.drop_duplicates(subset="code", keep="first")

    base = vendas.merge(
        produtos[["code", "category"]], left_on="id_product", right_on="code", how="left"
    )

    clientes = base.groupby("id_client", as_index=False).agg(
        faturamento_total=("total", "sum"),
        frequencia=("id", "count"),
        diversidade_categorias=("category", "nunique"),
    )
    clientes["ticket_medio"] = clientes["faturamento_total"] / clientes["frequencia"]

    top10 = (
        clientes[clientes["diversidade_categorias"] >= 3]
        .sort_values(["ticket_medio", "id_client"], ascending=[False, True])
        .head(10)
        .copy()
    )

    categoria_top10 = (
        base[base["id_client"].isin(top10["id_client"])]
        .groupby("category", as_index=False)
        .agg(qtd_total=("qtd", "sum"))
        .sort_values(["qtd_total", "category"], ascending=[False, True])
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    top10.to_csv(OUT_DIR / "q5_top10_clientes_fieis.csv", index=False)
    categoria_top10.to_csv(OUT_DIR / "q5_categorias_top10.csv", index=False)

    resumo = {
        "top_categoria_qtd": str(categoria_top10.iloc[0]["category"]),
        "top_categoria_qtd_total": float(categoria_top10.iloc[0]["qtd_total"]),
        "top10_primeiro_id_client": int(top10.iloc[0]["id_client"]),
        "top10_primeiro_ticket_medio": float(top10.iloc[0]["ticket_medio"]),
    }
    (OUT_DIR / "q5_summary.json").write_text(json.dumps(resumo, indent=2), encoding="utf-8")

    print("=== Q5 | Clientes fieis ===")
    for k, v in resumo.items():
        print(f"{k}: {v}")
    print(f"\nArquivos salvos em: {OUT_DIR}")


if __name__ == "__main__":
    main()


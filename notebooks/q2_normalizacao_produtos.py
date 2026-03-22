# ================================================
# LH Nautical Challenge - Questao 2
# Normalizacao do arquivo produtos_raw.csv
# ================================================

import json
from pathlib import Path

import pandas as pd
import unidecode
from rapidfuzz import process

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "produtos_raw.csv"
OUT_CSV = ROOT / "data" / "processed" / "q2_produtos_normalizados.csv"
OUT_JSON = ROOT / "data" / "processed" / "q2_summary.json"

CANONICAS = ["eletronicos", "propulsao", "ancoragem"]


def normalizar_categoria(texto: str) -> str:
    texto_limpo = unidecode.unidecode(str(texto).strip().lower()).replace(" ", "")
    match, score, _ = process.extractOne(texto_limpo, CANONICAS)
    return match if score >= 70 else "outros"


def main() -> None:
    df = pd.read_csv(RAW)

    duplicatas_antes = int(df.duplicated(subset="code").sum())

    df["category"] = df["actual_category"].apply(normalizar_categoria)
    df["price"] = (
        df["price"]
        .astype(str)
        .str.replace("R$", "", regex=False)
        .str.strip()
        .astype(float)
    )

    df = df.drop_duplicates(subset="code", keep="first").copy()

    summary = {
        "rows_before": int(pd.read_csv(RAW).shape[0]),
        "rows_after": int(df.shape[0]),
        "duplicates_removed": duplicatas_antes,
        "unique_categories_after": sorted(df["category"].dropna().unique().tolist()),
        "price_min": float(df["price"].min()),
        "price_max": float(df["price"].max()),
    }

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== Q2 | Produtos normalizados ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nCSV salvo em: {OUT_CSV}")
    print(f"Resumo salvo em: {OUT_JSON}")


if __name__ == "__main__":
    main()


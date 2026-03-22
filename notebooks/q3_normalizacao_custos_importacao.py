# ================================================
# LH Nautical Challenge - Questao 3
# Normalizacao do JSON custos_importacao.json
# ================================================

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "custos_importacao.json"
OUT_CSV = ROOT / "data" / "processed" / "q3_custos_importacao_normalizado.csv"
OUT_JSON = ROOT / "data" / "processed" / "q3_summary.json"


def main() -> None:
    data = json.loads(RAW.read_text(encoding="utf-8"))

    rows = []
    for item in data:
        for hist in item.get("historic_data", []):
            rows.append(
                {
                    "product_id": item.get("product_id"),
                    "product_name": item.get("product_name"),
                    "category": item.get("category"),
                    "start_date": hist.get("start_date"),
                    "usd_price": hist.get("usd_price"),
                }
            )

    df = pd.DataFrame(rows)
    df["start_date"] = pd.to_datetime(df["start_date"], dayfirst=True, errors="coerce")
    df = df.sort_values(["product_id", "start_date"]).reset_index(drop=True)

    summary = {
        "products_in_json": int(len(data)),
        "rows_after_normalization": int(df.shape[0]),
        "start_date_min": df["start_date"].min().strftime("%Y-%m-%d"),
        "start_date_max": df["start_date"].max().strftime("%Y-%m-%d"),
    }

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== Q3 | Custos de importacao normalizados ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nCSV salvo em: {OUT_CSV}")
    print(f"Resumo salvo em: {OUT_JSON}")


if __name__ == "__main__":
    main()


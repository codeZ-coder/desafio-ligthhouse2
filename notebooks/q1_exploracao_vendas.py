import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "vendas_2023_2024.csv"
OUT_JSON = ROOT / "data" / "processed" / "q1_summary.json"


def main() -> None:
    # Premissa da Q1: apenas leitura bruta, sem limpeza/tratamento.
    df = pd.read_csv(RAW)

    summary = {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "sale_date_min_raw": str(df["sale_date"].min()),
        "sale_date_max_raw": str(df["sale_date"].max()),
        "total_min": float(df["total"].min()),
        "total_max": float(df["total"].max()),
        "total_mean": float(df["total"].mean()),
        "nulls_by_column": df.isna().sum().astype(int).to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== Q1 | EDA vendas_2023_2024 (bruto) ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nResumo salvo em: {OUT_JSON}")


if __name__ == "__main__":
    main()

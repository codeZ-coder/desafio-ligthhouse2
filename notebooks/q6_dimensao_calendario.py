# ================================================
# LH Nautical Challenge - Questao 6
# Dimensao calendario para medias com dias sem venda
# ================================================

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "vendas_2023_2024.csv"
OUT_DIR = ROOT / "data" / "processed"


def parse_sale_date(series: pd.Series) -> pd.Series:
    parsed_iso = pd.to_datetime(series, errors="coerce", format="%Y-%m-%d")
    parsed_br = pd.to_datetime(series, errors="coerce", format="%d-%m-%Y")
    return parsed_iso.fillna(parsed_br)


def main() -> None:
    vendas = pd.read_csv(RAW)
    vendas["sale_date"] = parse_sale_date(vendas["sale_date"])

    vendas_dia = vendas.groupby("sale_date", as_index=False).agg(valor_venda=("total", "sum"))

    calendario = pd.DataFrame(
        {"sale_date": pd.date_range(vendas["sale_date"].min(), vendas["sale_date"].max(), freq="D")}
    )
    calendario = calendario.merge(vendas_dia, on="sale_date", how="left")
    calendario["valor_venda"] = calendario["valor_venda"].fillna(0.0)

    map_dia = {
        0: "Segunda-feira",
        1: "Terca-feira",
        2: "Quarta-feira",
        3: "Quinta-feira",
        4: "Sexta-feira",
        5: "Sabado",
        6: "Domingo",
    }
    calendario["dia_semana"] = calendario["sale_date"].dt.weekday.map(map_dia)

    medias = (
        calendario.groupby("dia_semana", as_index=False)
        .agg(media_vendas=("valor_venda", "mean"))
        .sort_values("media_vendas")
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    calendario.to_csv(OUT_DIR / "q6_calendario_vendas.csv", index=False)
    medias.to_csv(OUT_DIR / "q6_media_por_dia_semana.csv", index=False)

    pior = medias.iloc[0]
    resumo = {
        "pior_dia_semana": str(pior["dia_semana"]),
        "pior_media_vendas": round(float(pior["media_vendas"]), 2),
    }
    (OUT_DIR / "q6_summary.json").write_text(json.dumps(resumo, indent=2), encoding="utf-8")

    print("=== Q6 | Dimensao calendario ===")
    for k, v in resumo.items():
        print(f"{k}: {v}")
    print(f"\nArquivos salvos em: {OUT_DIR}")


if __name__ == "__main__":
    main()


# ================================================
# LH Nautical Challenge - Questao 7
# Baseline de previsao com media movel de 7 dias
# ================================================

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"
TARGET_NAME = "Motor de Popa Yamaha Evo Dash 155HP"


def parse_sale_date(series: pd.Series) -> pd.Series:
    parsed_iso = pd.to_datetime(series, errors="coerce", format="%Y-%m-%d")
    parsed_br = pd.to_datetime(series, errors="coerce", format="%d-%m-%Y")
    return parsed_iso.fillna(parsed_br)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def main() -> None:
    vendas = pd.read_csv(RAW_DIR / "vendas_2023_2024.csv")
    produtos = pd.read_csv(RAW_DIR / "produtos_raw.csv")

    vendas["sale_date"] = parse_sale_date(vendas["sale_date"])

    alvo = produtos.loc[produtos["name"] == TARGET_NAME, "code"]
    if alvo.empty:
        alvo = produtos.loc[produtos["name"].str.contains("Motor de Popa Yamaha Evo Dash 155HP", na=False), "code"]
    if alvo.empty:
        raise RuntimeError("Produto alvo da questao 7 nao encontrado no catalogo.")
    id_alvo = int(alvo.iloc[0])

    serie = vendas[vendas["id_product"] == id_alvo].groupby("sale_date", as_index=False).agg(qtd_dia=("qtd", "sum"))

    calendario = pd.DataFrame(
        {"sale_date": pd.date_range(vendas["sale_date"].min(), vendas["sale_date"].max(), freq="D")}
    )
    serie = calendario.merge(serie, on="sale_date", how="left")
    serie["qtd_dia"] = serie["qtd_dia"].fillna(0.0)

    train = serie[serie["sale_date"] <= pd.Timestamp("2023-12-31")].copy()
    test = serie[
        (serie["sale_date"] >= pd.Timestamp("2024-01-01"))
        & (serie["sale_date"] <= pd.Timestamp("2024-01-31"))
    ].copy()

    history = train["qtd_dia"].tolist()
    previsoes = []
    for _, row in test.iterrows():
        pred = float(np.mean(history[-7:])) if len(history) >= 7 else float(np.mean(history))
        previsoes.append(pred)
        # Atualizacao recursiva com valor real do dia para previsao 1-step ahead.
        history.append(float(row["qtd_dia"]))

    test = test.copy()
    test["forecast_qtd_dia"] = previsoes

    metric_mae = mae(test["qtd_dia"].to_numpy(), test["forecast_qtd_dia"].to_numpy())
    soma_semana1 = int(round(test.head(7)["forecast_qtd_dia"].sum()))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    test.to_csv(OUT_DIR / "q7_previsao_jan_2024.csv", index=False)

    resumo = {
        "id_product_alvo": id_alvo,
        "produto_alvo": TARGET_NAME,
        "mae_jan_2024": metric_mae,
        "soma_previsao_primeira_semana_jan_2024": soma_semana1,
    }
    (OUT_DIR / "q7_summary.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("=== Q7 | Previsao baseline ===")
    for k, v in resumo.items():
        print(f"{k}: {v}")
    print(f"\nArquivos salvos em: {OUT_DIR}")


if __name__ == "__main__":
    main()


# ================================================
# LH Nautical Challenge - Questao 4
# Prejuizo por produto com cambio diario (PTAX)
# ================================================

import json
from pathlib import Path
from urllib.request import urlopen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"
CAMBIO_CACHE = OUT_DIR / "q4_cambio_ptax_diario.csv"


def parse_sale_date(series: pd.Series) -> pd.Series:
    parsed_iso = pd.to_datetime(series, errors="coerce", format="%Y-%m-%d")
    parsed_br = pd.to_datetime(series, errors="coerce", format="%d-%m-%Y")
    return parsed_iso.fillna(parsed_br)


def carregar_cambio_ptax(data_inicial: pd.Timestamp, data_final: pd.Timestamp) -> pd.DataFrame:
    data_inicial = pd.Timestamp(data_inicial).normalize()
    data_final = pd.Timestamp(data_final).normalize()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if CAMBIO_CACHE.exists():
        cache = pd.read_csv(CAMBIO_CACHE)
        cache["sale_date"] = pd.to_datetime(cache["sale_date"], errors="coerce").dt.normalize()
        cache = (
            cache.dropna(subset=["sale_date", "cotacao_venda"])
            .drop_duplicates(subset=["sale_date"], keep="last")
            .sort_values("sale_date")
            .reset_index(drop=True)
        )
    else:
        cache = pd.DataFrame(columns=["sale_date", "cotacao_venda"])

    if cache.empty:
        tem_cobertura = False
    else:
        tem_cobertura = (
            cache["sale_date"].min() <= data_inicial and cache["sale_date"].max() >= data_final
        )

    if not tem_cobertura:
        ds_ini = data_inicial.strftime("%m-%d-%Y")
        ds_fim = data_final.strftime("%m-%d-%Y")
        url = (
            "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?"
            f"@dataInicial=%27{ds_ini}%27&@dataFinalCotacao=%27{ds_fim}%27&$top=10000&$format=json"
        )

        response = json.loads(urlopen(url, timeout=10).read().decode("utf-8"))
        ptax = pd.DataFrame(response.get("value", []))

        if not ptax.empty:
            ptax["dataHoraCotacao"] = pd.to_datetime(ptax["dataHoraCotacao"], errors="coerce")
            ptax = ptax.dropna(subset=["dataHoraCotacao", "cotacaoVenda"]).copy()
            ptax["sale_date"] = ptax["dataHoraCotacao"].dt.normalize()
            ptax = (
                ptax.sort_values("dataHoraCotacao")
                .drop_duplicates(subset=["sale_date"], keep="last")
                .rename(columns={"cotacaoVenda": "cotacao_venda"})[["sale_date", "cotacao_venda"]]
            )
            cache = (
                pd.concat([cache, ptax], ignore_index=True)
                .drop_duplicates(subset=["sale_date"], keep="last")
                .sort_values("sale_date")
                .reset_index(drop=True)
            )
            cache.to_csv(CAMBIO_CACHE, index=False)

    calendario = pd.DataFrame({"sale_date": pd.date_range(data_inicial, data_final, freq="D")})
    cambio = calendario.merge(cache[["sale_date", "cotacao_venda"]], on="sale_date", how="left")
    # Fim de semana/feriado: reaproveita a ultima cotacao valida disponivel.
    cambio["cotacao_venda"] = cambio["cotacao_venda"].ffill().bfill()

    if cambio["cotacao_venda"].isna().any():
        raise RuntimeError("Nao foi possivel carregar cotacao PTAX para todo o periodo solicitado.")

    return cambio


def main() -> None:
    vendas = pd.read_csv(RAW_DIR / "vendas_2023_2024.csv")
    vendas["sale_date"] = parse_sale_date(vendas["sale_date"])
    vendas = vendas.dropna(subset=["sale_date", "id_product"]).copy()
    vendas["id_product"] = vendas["id_product"].astype(int)

    custos_raw = json.loads((RAW_DIR / "custos_importacao.json").read_text(encoding="utf-8"))
    custos = []
    for item in custos_raw:
        for hist in item.get("historic_data", []):
            custos.append(
                {
                    "id_product": item["product_id"],
                    "start_date": pd.to_datetime(hist["start_date"], dayfirst=True, errors="coerce"),
                    "usd_price": hist["usd_price"],
                }
            )

    custos_df = pd.DataFrame(custos).dropna(subset=["id_product", "start_date", "usd_price"]).copy()
    custos_df["id_product"] = custos_df["id_product"].astype(int)
    custos_df = custos_df.sort_values(["start_date", "id_product"]).reset_index(drop=True)
    vendas = vendas.sort_values(["sale_date", "id_product"]).reset_index(drop=True)

    merged = pd.merge_asof(
        vendas,
        custos_df,
        by="id_product",
        left_on="sale_date",
        right_on="start_date",
        direction="backward",
    )

    cambio = carregar_cambio_ptax(merged["sale_date"].min(), merged["sale_date"].max())
    merged = merged.merge(cambio, on="sale_date", how="left")

    merged["custo_unitario_brl"] = merged["usd_price"] * merged["cotacao_venda"]
    merged["custo_total_brl"] = merged["custo_unitario_brl"] * merged["qtd"]
    merged["prejuizo_brl"] = (merged["custo_total_brl"] - merged["total"]).clip(lower=0)

    produto = (
        merged.groupby("id_product", as_index=False)
        .agg(receita_total_brl=("total", "sum"), prejuizo_total_brl=("prejuizo_brl", "sum"))
    )
    produto["percentual_perda"] = np.where(
        produto["receita_total_brl"] > 0,
        produto["prejuizo_total_brl"] / produto["receita_total_brl"],
        np.nan,
    )
    produto = produto.sort_values("percentual_perda", ascending=False)

    somente_prejuizo = produto[produto["prejuizo_total_brl"] > 0].copy()
    top20 = somente_prejuizo.nlargest(20, "prejuizo_total_brl").sort_values("prejuizo_total_brl")

    plt.figure(figsize=(12, 8))
    plt.barh(top20["id_product"].astype(str), top20["prejuizo_total_brl"], color="#d9534f")
    plt.title("Top 20 produtos com maior prejuizo total (BRL)")
    plt.xlabel("Prejuizo total (R$)")
    plt.ylabel("id_product")
    plt.tight_layout()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chart_path = OUT_DIR / "q4_prejuizo_por_produto.png"
    plt.savefig(chart_path, dpi=150)
    plt.close()

    produto.to_csv(OUT_DIR / "q4_prejuizo_por_produto.csv", index=False)
    cambio.to_csv(OUT_DIR / "q4_cambio_ptax_diario.csv", index=False)

    top_row = produto.iloc[0]
    summary = {
        "top_id_product_percentual_perda": int(top_row["id_product"]),
        "top_percentual_perda": float(top_row["percentual_perda"]),
        "taxa_cambio_usada": "PTAX cotacaoVenda diaria do Banco Central (preenchimento ffill para dias sem cotacao)",
        "regra_prejuizo": "max(custo_total_brl - total_venda_brl, 0)",
    }
    (OUT_DIR / "q4_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("=== Q4 | Prejuizo por produto ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nArquivos salvos em: {OUT_DIR}")


if __name__ == "__main__":
    main()


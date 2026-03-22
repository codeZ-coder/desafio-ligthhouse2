# ================================================
# LH Nautical Challenge - Questao 8
# Recomendacao por similaridade de cosseno (produto x produto)
# ================================================

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"
TARGET_NAME = "GPS Garmin Vortex Maré Drift"


def cosine_similarity_matrix(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = matrix / norms
    return normalized @ normalized.T


def main() -> None:
    vendas = pd.read_csv(RAW_DIR / "vendas_2023_2024.csv")
    produtos = pd.read_csv(RAW_DIR / "produtos_raw.csv")

    inter = vendas.groupby(["id_client", "id_product"]).size().reset_index(name="cnt")
    inter["value"] = 1

    matriz = inter.pivot_table(index="id_client", columns="id_product", values="value", fill_value=0)

    alvo = produtos.loc[produtos["name"] == TARGET_NAME, "code"]
    if alvo.empty:
        alvo = produtos.loc[produtos["name"].str.contains("GPS Garmin Vortex", na=False), "code"]
    if alvo.empty:
        raise RuntimeError("Produto alvo da questao 8 nao encontrado no catalogo.")
    id_alvo = int(alvo.iloc[0])

    product_ids = matriz.columns.to_numpy()
    produto_cliente = matriz.to_numpy().T
    sim = cosine_similarity_matrix(produto_cliente)

    sim_df = pd.DataFrame(sim, index=product_ids, columns=product_ids)
    ranking = sim_df[id_alvo].drop(index=id_alvo).sort_values(ascending=False).head(5).reset_index()
    ranking.columns = ["id_product", "similaridade"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ranking.to_csv(OUT_DIR / "q8_top5_similares.csv", index=False)

    resumo = {
        "id_product_referencia": id_alvo,
        "produto_referencia": TARGET_NAME,
        "id_product_mais_similar": int(ranking.iloc[0]["id_product"]),
        "similaridade_mais_alta": float(ranking.iloc[0]["similaridade"]),
    }
    (OUT_DIR / "q8_summary.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("=== Q8 | Sistema de recomendacao ===")
    for k, v in resumo.items():
        print(f"{k}: {v}")
    print(f"\nArquivos salvos em: {OUT_DIR}")


if __name__ == "__main__":
    main()


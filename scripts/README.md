# Scripts de Entrega

## Geracao de graficos complementares

Script: `scripts/gerar_graficos_relatorio.py`

Entradas esperadas em `data/processed/`:
- `q4_prejuizo_por_produto.csv`
- `q6_media_por_dia_semana.csv`
- `q5_top10_clientes_fieis.csv`

Saidas geradas em `data/processed/`:
- `grafico_prejuizo_produtos.png`
- `grafico_dias_semana.png`
- `grafico_clientes_top10_ticket.png`
- `grafico_prejuizo_produtos_base.csv`
- `grafico_dias_semana_base.csv`
- `grafico_clientes_top10_ticket_base.csv`

Comando:
```powershell
python -u scripts/gerar_graficos_relatorio.py
```

## Geracao de PDF

Script: `scripts/gerar_pdf.py`

Comando:
```powershell
python -u scripts/gerar_pdf.py
```

Observacao:
- Saida padrao: `docs/desafio_resposta_banca_final.pdf`.
- O script procura automaticamente o markdown em `docs/` e `arquivos/docs/`.
- O anexo de graficos e gerado automaticamente a partir dos PNGs em `data/processed/`.
- O preflight valida cobertura de `Questao 1` a `Questao 8` e existencia de `q*_summary.json`.

Modo permissivo (quando quiser gerar mesmo com avisos):
```powershell
python -u scripts/gerar_pdf.py --no-strict
```

## Nota sobre auditoria Q9

Os artefatos de auditoria Q9 foram movidos para:
`arquivo/workspace_limpo_2026-03-22/`

Objetivo: manter o workspace principal focado na cadeia Q1-Q8 e no PDF final de entrega.

"""Testa se cada loja responde à busca a partir desta máquina (útil rodando no GitHub Actions)."""

from compras.coletores import mercado_livre

ml = mercado_livre.Cliente()
for termo in ["arroz", "detergente", "cafe"]:
    try:
        produtos, _ = ml.buscar(termo)
        exemplo = f" | ex.: {produtos[0].descricao[:50]} R$ {produtos[0].preco}" if produtos else ""
        print(f"ML API ({termo}): {len(produtos)} produtos do Supermercado{exemplo}", flush=True)
    except Exception as e:
        print(f"ML API ({termo}): ERRO {e}", flush=True)

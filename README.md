# Compras da Casa

Robôs coletam preços de mercado todo dia, e um site mostra onde comprar cada item mais barato,
já com os descontos de cada loja (ex.: -20% Qualitá com o cartão Pão de Açúcar) e o frete.

**Site:** https://gilscheiffer.github.io/sistema-de-compras/

## Como funciona

```
GitHub Actions (todo dia, 6h)          Supabase (Postgres + login)           Site (GitHub Pages)
  robôs PdA, Amazon,  ─────────────▶   catálogo, produtos, histórico  ◀────  onboarding, preços,
  ML e Guanabara                       casa, itens escolhidos (RLS)           plano do mês
```

- **Catálogo** ([catalogo.toml](catalogo.toml)): itens genéricos ("Arroz branco", "Detergente") com as
  regras para reconhecer o produto certo na loja (`comeca`, `incluir`, `excluir`). As regras foram afinadas
  contra a busca real, e os casos difíceis viraram testes em [tests/test_catalogo.py](tests/test_catalogo.py).
- **Robôs** ([compras/coletores/](compras/coletores/)): buscam cada item, leem o tamanho da embalagem
  ([compras/unidades.py](compras/unidades.py)) e gravam no Supabase. O histórico só registra preços que mudaram.
- **Site** ([web/](web/)): React + Supabase. O cálculo de ofertas e do plano (combinação de lojas com frete)
  fica em [web/src/calculo.ts](web/src/calculo.ts).
- **Banco** ([supabase/migrations/](supabase/migrations/)): dados públicos (preços) só são lidos por quem
  está logado e só os robôs escrevem; os dados da casa só aparecem para os membros.

## Desenvolvimento

```powershell
# robôs (Python)
python -m venv .venv; .\.venv\Scripts\activate
pip install -e ".[dev]"
pytest
python -m compras.coletar pao_de_acucar --teste            # mostra o que encontraria, sem gravar
python -m compras.coletar pao_de_acucar --item cafe-po --teste

# site
cd web; npm install; npm run dev                           # precisa de web/.env (VITE_SUPABASE_URL/KEY)
npm test

# SQL no Supabase (usa SUPABASE_ACCESS_TOKEN do .env)
python scripts/sql.py supabase/migrations/0002_seguranca_indices.sql
```

O `.env` na raiz (fora do git) guarda `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_PROJECT_REF`
e `SUPABASE_ACCESS_TOKEN`. No GitHub, os robôs leem `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` dos secrets.
O Mercado Livre usa também `ML_CLIENT_ID` e `ML_CLIENT_SECRET` (app "ComparaPrecosGSx" no DevCenter), no `.env` e nos secrets.

## Lojas

| Loja | Situação | Como |
| --- | --- | --- |
| Pão de Açúcar | ✅ diário | API de busca do site, loja do Multicenter Itaipu (`storeId` 2272) |
| Guanabara | ✅ diário* | imagens do encarte lidas pelo Claude Code (`claude -p`), uma vez por página |
| Amazon | ✅ diário | página de busca via `curl` (a Amazon recusa clientes HTTP do Python) |
| Mercado Livre | ✅ diário | API oficial com token do app (`client_credentials`): mais vendidos da categoria + busca no catálogo, só anúncios do ML Supermercado |
| Shopee | — | requisições assinadas e anti-robô pesado |

\* Precisa do secret `CLAUDE_CODE_OAUTH_TOKEN` (gerado com `claude setup-token`); sem ele o job do Guanabara é pulado.

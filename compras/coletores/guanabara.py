"""Ofertas do Guanabara, lidas das imagens do encarte pelo Claude Code.

O Guanabara não vende online nem publica preços em texto: as ofertas saem só como imagens
(encarte da semana e "super ofertas do dia"). Cada página é lida uma vez pelo `claude -p`,
que devolve os produtos em JSON; o resultado fica guardado em `encartes_lidos` e é
reaproveitado nas coletas seguintes enquanto a imagem continuar no site.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import httpx

from compras.coletores import ProdutoColetado
from compras.supabase import Supabase
from compras.texto import normalizar

LOJA_ID = "guanabara"
SITE = "https://www.supermercadosguanabara.com.br"
PAGINAS_COM_OFERTAS = ("/encarte", "/super-ofertas-do-dia")
MODELO = "sonnet"

# Imagens aparecem como /sites/default/files/styles/<estilo>/(adaptive-image/)?public/<pasta>/<arquivo>.jpg;
# o original (2220x1300, bom para ler) fica em /sites/default/files/<pasta>/<arquivo>.jpg.
_RE_IMAGEM = re.compile(r'/sites/default/files/(?:styles/[^"\']*?/public/)?(encarte|ofertasdodia)/([\w\-]+\.jpe?g)')
_RE_VALIDADE = re.compile(r"v[aá]lida de (\d{2}/\d{2}/\d{4}) at[eé] (\d{2}/\d{2}/\d{4})", re.IGNORECASE)

PROMPT = """Leia a imagem {arquivo}: é uma página do encarte de ofertas do Supermercados Guanabara.
Liste TODOS os produtos que têm preço. Regras:
- Um objeto por produto. Se o encarte diz "X ou Y" (marcas, sabores ou tipos diferentes), crie um objeto para cada um, com o mesmo preço.
- "nome": tipo do produto + variação + marca, como na prateleira, SEMPRE começando pelo tipo do produto (ex.: "Arroz Branco Tipo 1 Tio João", "Feijão Preto Kicaldo", "Café Torrado e Moído Pilão Tradicional").
- "marca": só a marca.
- "quantidade" (número) e "unidade" ("g", "kg", "ml", "L" ou "un"): tamanho da embalagem. Se o encarte diz só "kg" (ex.: "Açúcar União kg"), use 1 e "kg". Para pacotes com várias unidades, use o total de unidades com "un" (ex.: papel higiênico 12 rolos = 12 "un"). Para packs de bebida, use o volume total (ex.: 12 latas de 350ml = 4200 e "ml").
- "preco": o preço em reais, como número. "por": "kg" quando for preço por quilo de produto pesado na hora (carnes, frios, hortifrúti); senão "embalagem".
- "leve" e "pague": números quando for promoção do tipo "leve 3 pague 2"; senão null.
- "obs": condições especiais (ex.: "só no cartão Guanabara", "a partir de 2 unidades") ou "".
Responda SOMENTE com JSON, sem texto antes ou depois:
{{"produtos": [{{"nome": "", "marca": "", "quantidade": 0, "unidade": "", "preco": 0.0, "por": "embalagem", "leve": null, "pague": null, "obs": ""}}]}}"""


def log(msg: str) -> None:
    print(msg, flush=True)


def paginas_do_encarte(http: httpx.Client) -> tuple[dict[str, str], date | None]:
    """chave -> URL da imagem original, e a data final da promoção (se o site informar)."""
    imagens: dict[str, str] = {}
    validade = None
    for caminho in PAGINAS_COM_OFERTAS:
        html = http.get(SITE + caminho).text
        for pasta, arquivo in _RE_IMAGEM.findall(html):
            # O mesmo encarte aparece nas duas páginas com sufixos numéricos diferentes.
            chave = re.sub(r"\d{8,}(?=\.jpe?g$)", "", arquivo)
            imagens.setdefault(chave, f"{SITE}/sites/default/files/{pasta}/{arquivo}")
        if m := _RE_VALIDADE.search(html):
            d, mes, a = m.group(2).split("/")
            fim = date(int(a), int(mes), int(d))
            validade = max(validade, fim) if validade else fim
    return imagens, validade


def ler_com_claude(imagem: Path) -> list[dict]:
    claude = shutil.which("claude")
    if not claude:
        raise RuntimeError("Claude Code CLI não encontrado (npm install -g @anthropic-ai/claude-code)")
    # O prompt vai pela entrada padrão: no Windows o claude.CMD perde argumentos com quebra de linha
    # (e com eles o --model, caindo no modelo padrão do usuário).
    saida = subprocess.run(
        [claude, "-p", "--allowedTools", "Read", "--model", MODELO, "--output-format", "json"],
        input=PROMPT.format(arquivo=imagem.name),
        cwd=imagem.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    if saida.returncode != 0:
        raise RuntimeError(f"claude falhou ({saida.returncode}): {(saida.stderr or saida.stdout)[:500]}")
    resposta = json.loads(saida.stdout)
    if resposta.get("is_error"):
        raise RuntimeError(f"claude: {resposta.get('result', '')[:500]}")
    texto = resposta["result"]
    return json.loads(texto[texto.find("{") : texto.rfind("}") + 1])["produtos"]


def _descricao(p: dict) -> str:
    """Nome + tamanho, no formato que o reconhecimento do catálogo entende ("Arroz Branco Tio João 5kg")."""
    if p.get("por") == "kg":
        return f"{p['nome']} 1kg"
    q = p.get("quantidade")
    if not q:
        return p["nome"]
    q = int(q) if float(q).is_integer() else q
    return f"{p['nome']} {q}{p.get('unidade') or ''}"


def converter(p: dict, validade: date | None) -> ProdutoColetado | None:
    try:
        preco = float(p["preco"])
    except (KeyError, TypeError, ValueError):
        return None
    if preco <= 0 or not p.get("nome"):
        return None
    descricao = _descricao(p)
    promocao = {"origem": "encarte"}
    if validade:
        promocao["fim"] = validade.isoformat()
    if p.get("leve") and p.get("pague"):
        promocao |= {"leve": p["leve"], "pague": p["pague"]}
    if p.get("obs"):
        promocao["obs"] = p["obs"]
    return ProdutoColetado(
        # Nome normalizado como identificador: a mesma oferta em semanas diferentes vira o mesmo produto.
        sku=normalizar(descricao)[:200],
        descricao=descricao,
        preco=preco,
        marca=p.get("marca") or None,
        promocao=promocao,
        url=SITE + "/encarte",
    )


def listar(db: Supabase | None, gravar_cache: bool = True) -> list[ProdutoColetado]:
    http = httpx.Client(headers={"User-Agent": "Mozilla/5.0"}, timeout=60, follow_redirects=True)
    imagens, validade = paginas_do_encarte(http)
    if not imagens:
        raise RuntimeError("nenhuma imagem de encarte encontrada no site")
    log(f"  {len(imagens)} páginas de encarte, válido até {validade or '?'}")
    cache = {c["chave"]: c for c in db.select("encartes_lidos", loja_id=f"eq.{LOJA_ID}")} if db else {}

    produtos: dict[str, ProdutoColetado] = {}
    with tempfile.TemporaryDirectory() as pasta:
        for chave, url in sorted(imagens.items()):
            if chave in cache:
                lidos = cache[chave]["produtos"]
                log(f"  {chave}: {len(lidos)} produtos (já lido)")
            else:
                arquivo = Path(pasta) / chave
                arquivo.write_bytes(http.get(url).content)
                lidos = ler_com_claude(arquivo)
                log(f"  {chave}: {len(lidos)} produtos (lido agora)")
                if db and gravar_cache:
                    db.insert(
                        "encartes_lidos",
                        [{"chave": chave, "loja_id": LOJA_ID, "url": url, "produtos": lidos,
                          "validade": validade.isoformat() if validade else None}],
                    )
            for p in lidos:
                c = converter(p, validade)
                if c and (c.sku not in produtos or c.preco < produtos[c.sku].preco):
                    produtos[c.sku] = c
    return list(produtos.values())

import { useMemo, useState } from "react";
import { ofertasDoItem, type Oferta } from "../calculo";
import type { Dados } from "../dados";
import { brl, data, qtd } from "../formato";
import type { ItemCatalogo, Produto } from "../tipos";

export default function Precos({ dados, irParaItens }: { dados: Dados; irParaItens: () => void }) {
  const [filtro, setFiltro] = useState<"todos" | "promo">("todos");
  const condicoes = dados.casa!.condicoes;
  const lojas = useMemo(() => new Map(dados.lojas.map((l) => [l.id, l.nome])), [dados.lojas]);
  const catalogo = useMemo(() => new Map(dados.catalogo.map((c) => [c.id, c])), [dados.catalogo]);

  const linhas = useMemo(
    () =>
      dados.itensCasa
        .map((ic) => ({ item: catalogo.get(ic.catalogo_id)!, consumo: ic.consumo_mensal, ofertas: ofertasDoItem(ic, dados.produtos, dados.regras, condicoes) }))
        .filter((l) => l.item)
        .sort((a, b) => a.item.categoria.localeCompare(b.item.categoria) || a.item.nome.localeCompare(b.item.nome)),
    [dados, catalogo, condicoes],
  );
  const emPromo = linhas.filter((l) => l.ofertas[0] && emPromocao(l.ofertas[0].produto));
  const visiveis = filtro === "promo" ? emPromo : linhas;

  if (linhas.length === 0) {
    return (
      <div className="vazio">
        <p>Vocês ainda não escolheram nenhum item.</p>
        <button onClick={irParaItens}>Escolher itens</button>
      </div>
    );
  }

  return (
    <section>
      <div className="filtros">
        <button className={`chip ${filtro === "todos" ? "ligado" : ""}`} onClick={() => setFiltro("todos")}>
          Todos ({linhas.length})
        </button>
        <button className={`chip ${filtro === "promo" ? "ligado" : ""}`} onClick={() => setFiltro("promo")}>
          🔥 Em promoção ({emPromo.length})
        </button>
      </div>
      {visiveis.map((l) => (
        <CartaoItem key={l.item.id} item={l.item} consumo={l.consumo} ofertas={l.ofertas} lojas={lojas} />
      ))}
    </section>
  );
}

function emPromocao(p: Produto): boolean {
  return !!p.preco_regular || p.promocao?.origem === "encarte";
}

function CartaoItem({
  item,
  consumo,
  ofertas,
  lojas,
}: {
  item: ItemCatalogo;
  consumo: number | null;
  ofertas: Oferta[];
  lojas: Map<string, string>;
}) {
  const [aberto, setAberto] = useState(false);
  const [melhor, ...outras] = ofertas;
  return (
    <article className="cartao-item">
      <header>
        <h3>{item.nome}</h3>
        {consumo && <span className="sutil">{qtd(consumo, item.unidade)}/mês</span>}
      </header>
      {melhor ? (
        <>
          <LinhaOferta oferta={melhor} unidade={item.unidade} loja={lojas.get(melhor.produto.loja_id)} destaque comConsumo={!!consumo} />
          {outras.length > 0 && (
            <button className="link" onClick={() => setAberto(!aberto)}>
              {aberto ? "esconder" : `ver mais ${Math.min(outras.length, 5)} opções`}
            </button>
          )}
          {aberto &&
            outras.slice(0, 5).map((o) => (
              <LinhaOferta key={o.produto.id} oferta={o} unidade={item.unidade} loja={lojas.get(o.produto.loja_id)} comConsumo={!!consumo} />
            ))}
        </>
      ) : (
        <p className="sutil">Nenhum preço encontrado ainda{item ? " (confira as marcas escolhidas)" : ""}.</p>
      )}
    </article>
  );
}

function LinhaOferta({
  oferta: o,
  unidade,
  loja,
  destaque = false,
  comConsumo,
}: {
  oferta: Oferta;
  unidade: ItemCatalogo["unidade"];
  loja?: string;
  destaque?: boolean;
  comConsumo: boolean;
}) {
  const p = o.produto;
  const pct = p.preco_regular ? Math.round((1 - p.preco / p.preco_regular) * 100) : 0;
  return (
    <div className={`oferta ${destaque ? "destaque" : ""}`}>
      <div className="oferta-preco">
        <strong>{brl(comConsumo ? o.custo : o.efetivo)}</strong>
        {comConsumo && o.pacotes > 1 && <span className="sutil"> ({o.pacotes}× {brl(o.efetivo)})</span>}
        <span className="por-unidade">
          {brl(o.porUnidade)}/{unidade}
        </span>
      </div>
      <div className="oferta-produto">
        {p.url ? (
          <a href={p.url} target="_blank" rel="noreferrer">
            {p.descricao}
          </a>
        ) : (
          p.descricao
        )}
        <span className="sutil"> · {loja ?? p.loja_id} · {qtd(p.quantidade, unidade)}</span>
      </div>
      <div className="selos">
        {o.ajustes.map((a) => (
          <span key={a} className="selo desconto">
            {a}
          </span>
        ))}
        {p.preco_regular && (
          <span className="selo promo">
            🔥 -{pct}% (de {brl(p.preco_regular)}){p.promocao?.fim && ` até ${data(p.promocao.fim)}`}
          </span>
        )}
        {!p.preco_regular && p.promocao?.origem === "encarte" && (
          <span className="selo promo">📰 encarte{p.promocao.fim && ` até ${data(p.promocao.fim)}`}</span>
        )}
        {p.promocao?.obs && <span className="selo">{p.promocao.obs}</span>}
        {p.promocao?.leve && p.promocao?.pague && (
          <span className="selo promo">
            leve {p.promocao.leve} pague {p.promocao.pague}
          </span>
        )}
      </div>
    </div>
  );
}

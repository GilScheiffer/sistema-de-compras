import { useMemo, useState } from "react";
import { melhorPorLoja, ofertasDoItem, planejar } from "../calculo";
import type { Dados } from "../dados";
import { brl, qtd } from "../formato";

export default function Plano({ dados, irParaItens }: { dados: Dados; irParaItens: () => void }) {
  const [maxLojas, setMaxLojas] = useState(2);
  const condicoes = dados.casa!.condicoes;
  const catalogo = useMemo(() => new Map(dados.catalogo.map((c) => [c.id, c])), [dados.catalogo]);

  const { itens, planos } = useMemo(() => {
    const naLista = dados.itensCasa.filter((i) => i.na_lista && catalogo.has(i.catalogo_id));
    const porItem = new Map(naLista.map((i) => [i.catalogo_id, melhorPorLoja(ofertasDoItem(i, dados.produtos, dados.regras, condicoes))]));
    const itens = naLista.map((i) => catalogo.get(i.catalogo_id)!);
    return { itens, planos: planejar(itens, porItem, dados.lojas, condicoes, maxLojas) };
  }, [dados, catalogo, condicoes, maxLojas]);

  if (itens.length === 0) {
    return (
      <div className="vazio">
        <p>Escolha os itens da casa para montar o plano do mês.</p>
        <button onClick={irParaItens}>Escolher itens</button>
      </div>
    );
  }
  if (planos.length === 0) return <p className="vazio">Ainda não há preços para os itens escolhidos.</p>;

  const [melhor, ...alternativas] = planos;
  const semConsumo = dados.itensCasa.filter((i) => i.na_lista && !i.consumo_mensal).length;

  return (
    <section>
      <div className="cartao-plano">
        <span className="sutil">Melhor plano para o mês</span>
        <div className="total">{brl(melhor.total)}</div>
        <span>{melhor.lojas.map((l) => l.nome).join(" + ")}</span>
        {semConsumo > 0 && (
          <p className="aviso">
            {semConsumo} item(ns) sem consumo mensal: contei 1 embalagem de cada.{" "}
            <button className="link" onClick={irParaItens}>
              Ajustar
            </button>
          </p>
        )}
      </div>

      {melhor.lojas.map((loja) => {
        const ofertas = [...melhor.alocacao.entries()].filter(([, o]) => o.produto.loja_id === loja.id);
        const fixo = melhor.custosFixos.get(loja.id) ?? 0;
        return (
          <article key={loja.id} className="cartao-item">
            <header>
              <h3>{loja.nome}</h3>
              <strong>{brl(melhor.subtotais.get(loja.id) ?? 0)}</strong>
            </header>
            {fixo > 0 && (
              <p className="sutil">
                + {loja.tipo === "online" ? "frete" : "ida"} {brl(fixo)}
              </p>
            )}
            <ul className="lista-compra">
              {ofertas.map(([itemId, o]) => {
                const item = catalogo.get(itemId)!;
                return (
                  <li key={itemId}>
                    <span>
                      <strong>{item.nome}</strong>
                      <span className="sutil">
                        {" "}
                        · {o.pacotes}× {o.produto.descricao} ({qtd(o.produto.quantidade, item.unidade)})
                      </span>
                      {o.ajustes.length > 0 && <span className="selo desconto">{o.ajustes.join(", ")}</span>}
                      {o.produto.preco_regular && <span className="selo promo">promo</span>}
                    </span>
                    <span>{brl(o.custo)}</span>
                  </li>
                );
              })}
            </ul>
          </article>
        );
      })}

      {melhor.faltando.length > 0 && (
        <p className="aviso">Sem preço ainda: {melhor.faltando.map((i) => i.nome).join(", ")}</p>
      )}

      {alternativas.length > 0 && (
        <div className="alternativas">
          <h3>Outras opções</h3>
          {alternativas.slice(0, 4).map((p) => (
            <div key={p.lojas.map((l) => l.id).join("+")} className="alternativa">
              <span>{p.lojas.map((l) => l.nome).join(" + ")}</span>
              <span>
                {brl(p.total)} <span className="sutil">(+{brl(p.total - melhor.total)})</span>
                {p.faltando.length > 0 && <span className="sutil"> · faltam {p.faltando.length}</span>}
              </span>
            </div>
          ))}
        </div>
      )}

      <label className="sutil max-lojas">
        Aceitar dividir em até
        <select value={maxLojas} onChange={(e) => setMaxLojas(Number(e.target.value))}>
          {[1, 2, 3].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        loja(s)
      </label>
    </section>
  );
}

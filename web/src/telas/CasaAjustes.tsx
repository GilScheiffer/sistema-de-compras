import { useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { salvarCondicoes, type Dados } from "../dados";
import { supabase } from "../supabase";

// Condições que as regras de desconto e frete consultam (casas.condicoes).
const CONDICOES = [
  { chave: "cartao_pao_de_acucar", rotulo: "Temos o cartão Pão de Açúcar", ajuda: "Aplica 20% de desconto nos produtos Qualitá." },
  { chave: "amazon_prime", rotulo: "Temos Amazon Prime", ajuda: "Zera o frete da Amazon." },
];

export default function CasaAjustes({ dados, setDados }: { dados: Dados; setDados: Dispatch<SetStateAction<Dados | null>> }) {
  const casa = dados.casa!;
  const [copiado, setCopiado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function alternar(chave: string) {
    const anteriores = casa.condicoes;
    const novas = { ...anteriores, [chave]: !anteriores[chave] };
    setDados((d) => (d ? { ...d, casa: { ...casa, condicoes: novas } } : d));
    try {
      setErro(null);
      await salvarCondicoes(casa, novas);
    } catch (e) {
      setDados((d) => (d ? { ...d, casa: { ...casa, condicoes: anteriores } } : d));
      setErro(`Não salvou: ${e instanceof Error ? e.message : e}`);
    }
  }

  async function compartilhar() {
    const texto = `Entra na nossa casa no Compras da Casa: ${location.origin}${import.meta.env.BASE_URL} — código ${casa.codigo_convite}`;
    if (navigator.share) {
      await navigator.share({ text: texto }).catch(() => {});
    } else {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    }
  }

  return (
    <section>
      <article className="cartao-item">
        <h3>{casa.nome}</h3>
        <p className="sutil">Para a outra pessoa entrar: ela faz login no site e usa este código.</p>
        <div className="convite">
          <code>{casa.codigo_convite}</code>
          <button onClick={compartilhar}>{copiado ? "Copiado!" : "Compartilhar"}</button>
        </div>
      </article>

      <article className="cartao-item">
        <h3>Descontos e fretes</h3>
        {CONDICOES.map((c) => (
          <label key={c.chave} className="interruptor">
            <input type="checkbox" checked={!!casa.condicoes[c.chave]} onChange={() => alternar(c.chave)} />
            <span>
              {c.rotulo}
              <span className="sutil">{c.ajuda}</span>
            </span>
          </label>
        ))}
        {erro && <p className="erro">{erro}</p>}
      </article>

      <article className="cartao-item">
        <h3>Lojas acompanhadas</h3>
        <ul className="lojas">
          {dados.lojas.map((l) => {
            const n = dados.produtos.filter((p) => p.loja_id === l.id).length;
            return (
              <li key={l.id}>
                <span>{l.nome}</span>
                <span className="sutil">{n ? `${n} produtos` : "em breve"}</span>
              </li>
            );
          })}
        </ul>
      </article>

      <button className="secundario sair" onClick={() => supabase.auth.signOut()}>
        Sair
      </button>
    </section>
  );
}

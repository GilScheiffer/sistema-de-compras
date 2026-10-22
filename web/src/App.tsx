import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import { useDados } from "./dados";
import { quandoFoi } from "./formato";
import Login from "./telas/Login";
import SemCasa from "./telas/SemCasa";
import Itens from "./telas/Itens";
import Precos from "./telas/Precos";
import Plano from "./telas/Plano";
import CasaAjustes from "./telas/CasaAjustes";

type Aba = "precos" | "plano" | "itens" | "casa";
const ABAS: { id: Aba; rotulo: string; icone: string }[] = [
  { id: "precos", rotulo: "Preços", icone: "🏷️" },
  { id: "plano", rotulo: "Plano", icone: "🧾" },
  { id: "itens", rotulo: "Itens", icone: "📝" },
  { id: "casa", rotulo: "Casa", icone: "🏠" },
];

export default function App() {
  const [sessao, setSessao] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSessao(data.session));
    const { data } = supabase.auth.onAuthStateChange((_evento, s) => setSessao(s));
    return () => data.subscription.unsubscribe();
  }, []);

  if (sessao === undefined) return <p className="centro">Carregando…</p>;
  if (!sessao) return <Login />;
  return <Principal />;
}

function Principal() {
  const { dados, setDados, erro, recarregar } = useDados();
  const [aba, setAba] = useState<Aba>(() => {
    const h = location.hash.slice(1) as Aba;
    return ABAS.some((a) => a.id === h) ? h : "precos";
  });

  useEffect(() => {
    history.replaceState(null, "", `#${aba}`);
    window.scrollTo(0, 0);
  }, [aba]);

  // Casa nova, sem itens: começa pelo onboarding.
  useEffect(() => {
    if (dados?.casa && dados.itensCasa.length === 0) setAba("itens");
  }, [dados?.casa?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (erro) {
    return (
      <div className="centro">
        <p>Não consegui carregar os dados: {erro}</p>
        <button onClick={recarregar}>Tentar de novo</button>
      </div>
    );
  }
  if (!dados) return <p className="centro">Carregando preços…</p>;
  if (!dados.casa) return <SemCasa aoConcluir={recarregar} />;

  return (
    <div className="app">
      <header className="topo">
        <h1>Compras da Casa</h1>
        <span className="sutil">
          {dados.casa.nome}
          {dados.ultimaColeta && ` · preços de ${quandoFoi(dados.ultimaColeta)}`}
        </span>
      </header>
      <main>
        {aba === "precos" && <Precos dados={dados} irParaItens={() => setAba("itens")} />}
        {aba === "plano" && <Plano dados={dados} irParaItens={() => setAba("itens")} />}
        {aba === "itens" && <Itens dados={dados} setDados={setDados} />}
        {aba === "casa" && <CasaAjustes dados={dados} setDados={setDados} />}
      </main>
      <nav className="abas">
        {ABAS.map((a) => (
          <button key={a.id} className={a.id === aba ? "ativa" : ""} onClick={() => setAba(a.id)}>
            <span aria-hidden>{a.icone}</span>
            {a.rotulo}
          </button>
        ))}
      </nav>
    </div>
  );
}

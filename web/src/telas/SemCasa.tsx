import { useState } from "react";
import { criarCasa, entrarNaCasa } from "../dados";
import { supabase } from "../supabase";

export default function SemCasa({ aoConcluir }: { aoConcluir: () => void }) {
  const [nome, setNome] = useState("Nossa casa");
  const [codigo, setCodigo] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function executar(acao: () => Promise<void>) {
    setOcupado(true);
    setErro(null);
    try {
      await acao();
      aoConcluir();
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e));
      setOcupado(false);
    }
  }

  return (
    <div className="login">
      <div className="cartao">
        <h1>Bem-vindos! 🏡</h1>
        <p className="sutil">Os itens e preços ficam ligados a uma casa, compartilhada entre vocês dois.</p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            executar(() => criarCasa(nome.trim()));
          }}
        >
          <h2>Criar a casa</h2>
          <input value={nome} onChange={(e) => setNome(e.target.value)} required maxLength={60} />
          <button type="submit" disabled={ocupado}>
            Criar
          </button>
        </form>

        <div className="ou">ou</div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            executar(() => entrarNaCasa(codigo));
          }}
        >
          <h2>Entrar com o código de convite</h2>
          <input
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            placeholder="ex.: a1b2c3d4"
            required
            autoCapitalize="none"
          />
          <button type="submit" className="secundario" disabled={ocupado}>
            Entrar
          </button>
        </form>

        {erro && <p className="erro">{erro}</p>}
        <button className="link" onClick={() => supabase.auth.signOut()}>
          Sair
        </button>
      </div>
    </div>
  );
}

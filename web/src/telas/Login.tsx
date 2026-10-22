import { useState } from "react";
import { supabase } from "../supabase";

export default function Login() {
  const [email, setEmail] = useState("");
  const [estado, setEstado] = useState<"digitando" | "enviando" | "enviado">("digitando");
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setEstado("enviando");
    setErro(null);
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: location.origin + import.meta.env.BASE_URL },
    });
    if (error) {
      setErro(error.message);
      setEstado("digitando");
    } else {
      setEstado("enviado");
    }
  }

  return (
    <div className="login">
      <div className="cartao">
        <h1>🛒 Compras da Casa</h1>
        {estado === "enviado" ? (
          <>
            <p>
              Mandamos um link para <strong>{email}</strong>.
            </p>
            <p className="sutil">Abra o e-mail neste aparelho e toque no link para entrar. Pode levar um minutinho.</p>
            <button className="secundario" onClick={() => setEstado("digitando")}>
              Usar outro e-mail
            </button>
          </>
        ) : (
          <form onSubmit={enviar}>
            <p className="sutil">Entre com seu e-mail. Sem senha: você recebe um link para entrar.</p>
            <input
              type="email"
              required
              autoComplete="email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <button type="submit" disabled={estado === "enviando"}>
              {estado === "enviando" ? "Enviando…" : "Receber link"}
            </button>
            {erro && <p className="erro">{erro}</p>}
          </form>
        )}
      </div>
    </div>
  );
}

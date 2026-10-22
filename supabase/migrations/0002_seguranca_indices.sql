-- eh_membro só é usada pelas políticas de RLS: sai do schema exposto pela API.
-- As políticas guardam a função pelo OID, então continuam funcionando após a mudança.
create schema if not exists privado;
grant usage on schema privado to authenticated;
alter function public.eh_membro(uuid) set schema privado;

-- criar_casa e entrar_na_casa continuam públicas de propósito: o site as chama,
-- e ambas exigem usuário logado (auth.uid()).

create index if not exists casa_membros_user_idx on public.casa_membros (user_id);
create index if not exists itens_casa_catalogo_idx on public.itens_casa (catalogo_id);
create index if not exists regras_loja_loja_idx on public.regras_loja (loja_id);

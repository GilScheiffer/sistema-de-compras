-- Páginas de encarte já lidas pelo Claude: cada imagem é lida uma vez só,
-- e as coletas seguintes reaproveitam o resultado enquanto ela estiver no site.
create table public.encartes_lidos (
    chave    text primary key,  -- nome do arquivo sem o sufixo numérico
    loja_id  text not null references public.lojas,
    url      text not null,
    lido_em  timestamptz not null default now(),
    validade date,
    produtos jsonb not null
);

-- Só os robôs (service role) usam esta tabela.
alter table public.encartes_lidos enable row level security;

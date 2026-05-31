create table if not exists public.users (
    user_id text primary key,
    tier text not null default 'free',
    created_at timestamptz not null default now()
);

create table if not exists public.aaoifi_documents (
    document_id text primary key,
    title text not null,
    standard_number text,
    standard_type text,
    source_url text,
    version text not null default '1.0',
    status text not null default 'active',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.semantic_chunks (
    chunk_id text primary key,
    document_id text references public.aaoifi_documents(document_id),
    chunk_index integer not null,
    content text not null,
    token_count integer,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.compliance_rulings (
    ruling_id text primary key,
    session_id text,
    status text not null,
    reasoning text not null,
    citations jsonb not null default '[]'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
    audit_id text primary key,
    request_id text,
    session_id text,
    query text not null,
    status text not null,
    answer text not null,
    citations jsonb not null default '[]'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null
);

create index if not exists idx_semantic_chunks_document_id on public.semantic_chunks(document_id);
create index if not exists idx_compliance_rulings_session_id on public.compliance_rulings(session_id);
create index if not exists idx_audit_logs_session_id on public.audit_logs(session_id);
create index if not exists idx_audit_logs_created_at on public.audit_logs(created_at);

alter table public.users enable row level security;
alter table public.aaoifi_documents enable row level security;
alter table public.semantic_chunks enable row level security;
alter table public.compliance_rulings enable row level security;
alter table public.audit_logs enable row level security;

comment on table public.audit_logs is
    'Mushir compliance answer audit log. Server-side database connection only; no anon/authenticated RLS policy.';
comment on table public.aaoifi_documents is
    'Mushir governed AAOIFI document metadata/dataset table.';
comment on table public.semantic_chunks is
    'Mushir chunk metadata/table storage. Primary vector retrieval remains Qdrant for demo deployment.';

-- 错题本 + 间隔复习（Wrong Book / SRS）跨设备同步表 —— 课程包可选迁移
-- 与 CSP 生产站迁移 008 完全同构：每个用户 + 证书 + 题目一行，按 cert_slug 隔离。
-- 已在站点库执行过该迁移时无需重复执行（create table if not exists + drop/create policy 幂等）。
-- 前端只用 publishable/anon key + RLS；access_token 由站点 /assets/sync.js 会话提供。
-- 绝不把 service_role / sb_secret_ 放进前端或技能包。

create table if not exists public.user_wrongbook (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users(id) on delete cascade,
  cert_slug text not null,
  item_id text not null,
  state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  unique (owner_id, cert_slug, item_id)
);

create index if not exists user_wrongbook_owner_cert_idx
  on public.user_wrongbook (owner_id, cert_slug);

alter table public.user_wrongbook enable row level security;

drop policy if exists "wrongbook_owner_select" on public.user_wrongbook;
create policy "wrongbook_owner_select" on public.user_wrongbook
  for select to authenticated using (auth.uid() = owner_id);

drop policy if exists "wrongbook_owner_insert" on public.user_wrongbook;
create policy "wrongbook_owner_insert" on public.user_wrongbook
  for insert to authenticated with check (auth.uid() = owner_id);

drop policy if exists "wrongbook_owner_update" on public.user_wrongbook;
create policy "wrongbook_owner_update" on public.user_wrongbook
  for update to authenticated using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

drop policy if exists "wrongbook_owner_delete" on public.user_wrongbook;
create policy "wrongbook_owner_delete" on public.user_wrongbook
  for delete to authenticated using (auth.uid() = owner_id);

revoke all on public.user_wrongbook from anon;
grant select, insert, update, delete on public.user_wrongbook to authenticated;

-- daily_challenge_cert.sql — 可选：给「新证书每日一题」开全网正确率统计
-- 来源：CSP 站 006_daily_challenge.sql（2026-11-23）按 cert_slug 维度扩展。
--
-- 重要：本迁移建的是【独立新表 public.daily_answers_cert】，
--   绝不修改、不删除生产库里 CSP 正在使用的 public.daily_answers 与旧 RPC。
--   默认（cert.json 未配置 engagement.daily.stats）不执行本文件，站点走纯本地练习模式。
-- 执行方式：Supabase SQL Editor 粘贴执行，或 python tools/supabase_exec.py file.sql。
--   凭据只用 anon / publishable key，绝不使用 service_role / sb_secret_。

create table if not exists public.daily_answers_cert (
  id bigint generated always as identity primary key,
  cert_slug text not null,
  day_date text not null check (day_date ~ '^\d{4}-\d{2}-\d{2}$'),
  q_day int not null,
  choice int not null check (choice between 0 and 3),
  is_correct boolean not null default false,
  owner_id text,
  device_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint daily_answers_cert_device_len check (device_id is null or char_length(device_id) <= 64)
);

create unique index if not exists uq_daily_answers_cert_day_device
  on public.daily_answers_cert (cert_slug, day_date, coalesce(device_id, owner_id));
create index if not exists idx_daily_answers_cert_date
  on public.daily_answers_cert (cert_slug, day_date);

alter table public.daily_answers_cert enable row level security;

-- 提交作答：同证书 + 同设备/用户 + 同日重复提交 → 覆盖
create or replace function public.daily_challenge_submit_cert(
  p_date text, p_cert text, p_q_day int, p_choice int, p_correct boolean, p_device_id text
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  v_owner text := nullif(current_setting('request.jwt.claim.sub', true), '');
  v_device text := lower(coalesce(p_device_id, ''));
begin
  if p_cert is null or p_cert = '' then raise exception 'cert required'; end if;
  if v_device is null or v_device = '' then
    if v_owner is null then raise exception 'device_id required'; end if;
  elsif v_device !~ '^[0-9a-f]{8,64}$' then
    raise exception 'bad device_id';
  end if;
  insert into daily_answers_cert (cert_slug, day_date, q_day, choice, is_correct, owner_id, device_id)
  values (p_cert, p_date, p_q_day, p_choice, p_correct, v_owner, nullif(v_device, ''))
  on conflict (cert_slug, day_date, coalesce(device_id, owner_id)) do update
    set choice = excluded.choice,
        is_correct = excluded.is_correct,
        q_day = excluded.q_day,
        updated_at = now();
  return jsonb_build_object('ok', true);
end $$;

-- 统计：某证书当日作答数 / 正确数（匿名可查；STABLE 函数，提交与统计须分两次调用）
create or replace function public.daily_challenge_stats_cert(p_date text, p_cert text)
  returns table (attempts bigint, correct bigint)
language sql security definer set search_path = public stable as $$
  select count(*)::bigint, count(*) filter (where is_correct)::bigint
  from daily_answers_cert where day_date = p_date and cert_slug = p_cert;
$$;

revoke all on function public.daily_challenge_submit_cert(text, text, int, int, boolean, text) from public;
revoke all on function public.daily_challenge_stats_cert(text, text) from public;
grant execute on function public.daily_challenge_submit_cert(text, text, int, int, boolean, text) to anon, authenticated;
grant execute on function public.daily_challenge_stats_cert(text, text) to anon, authenticated;

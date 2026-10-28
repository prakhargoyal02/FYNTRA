CREATE TABLE IF NOT EXISTS public.fyntra_state (
 user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
 state jsonb NOT NULL CHECK(jsonb_typeof(state)='object' AND octet_length(state::text)<=5242880),
 revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
 updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.fyntra_state ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.fyntra_state FROM anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.fyntra_state TO authenticated;
CREATE POLICY fyntra_owner_select ON public.fyntra_state FOR SELECT TO authenticated USING ((select auth.uid())=user_id);
CREATE POLICY fyntra_owner_insert ON public.fyntra_state FOR INSERT TO authenticated WITH CHECK ((select auth.uid())=user_id);
CREATE POLICY fyntra_owner_update ON public.fyntra_state FOR UPDATE TO authenticated USING ((select auth.uid())=user_id) WITH CHECK ((select auth.uid())=user_id);
CREATE POLICY fyntra_owner_delete ON public.fyntra_state FOR DELETE TO authenticated USING ((select auth.uid())=user_id);

CREATE TABLE IF NOT EXISTS public.fyntra_statements (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
 name text NOT NULL,
 source_filename text NOT NULL,
 source_type text NOT NULL,
 account_id text,
 period_start date,
 period_end date,
 rows jsonb NOT NULL DEFAULT '[]'::jsonb,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.fyntra_statements ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.fyntra_statements FROM anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.fyntra_statements TO authenticated;
CREATE POLICY fyntra_statement_owner_select ON public.fyntra_statements FOR SELECT TO authenticated USING ((select auth.uid())=user_id);
CREATE POLICY fyntra_statement_owner_insert ON public.fyntra_statements FOR INSERT TO authenticated WITH CHECK ((select auth.uid())=user_id);
CREATE POLICY fyntra_statement_owner_update ON public.fyntra_statements FOR UPDATE TO authenticated USING ((select auth.uid())=user_id) WITH CHECK ((select auth.uid())=user_id);
CREATE POLICY fyntra_statement_owner_delete ON public.fyntra_statements FOR DELETE TO authenticated USING ((select auth.uid())=user_id);

CREATE TABLE IF NOT EXISTS public.fyntra_statement_exports (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
 name text NOT NULL,
 scope text NOT NULL CHECK(scope IN ('individual','selected','all','account')),
 format text NOT NULL CHECK(format IN ('csv','zip')),
 account_id text,
 statement_ids jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_typeof(statement_ids)='array'),
 rows jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_typeof(rows)='array' AND octet_length(rows::text)<=5242880),
 created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.fyntra_statement_exports ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.fyntra_statement_exports FROM anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.fyntra_statement_exports TO authenticated;
CREATE POLICY fyntra_statement_export_owner_select ON public.fyntra_statement_exports FOR SELECT TO authenticated USING ((select auth.uid())=user_id);
CREATE POLICY fyntra_statement_export_owner_insert ON public.fyntra_statement_exports FOR INSERT TO authenticated WITH CHECK ((select auth.uid())=user_id);
CREATE POLICY fyntra_statement_export_owner_update ON public.fyntra_statement_exports FOR UPDATE TO authenticated USING ((select auth.uid())=user_id) WITH CHECK ((select auth.uid())=user_id);
CREATE POLICY fyntra_statement_export_owner_delete ON public.fyntra_statement_exports FOR DELETE TO authenticated USING ((select auth.uid())=user_id);

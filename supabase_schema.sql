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

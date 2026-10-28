"""Optional private cloud storage. Auth clients are per-session, never cached globally."""
import json
import base64
import math
from datetime import datetime,timezone
from supabase import create_client, ClientOptions

class SyncConflict(RuntimeError):
    pass

def _json_safe(value):
    """Convert pandas/NumPy-style non-finite values into valid JSON values."""
    if isinstance(value, dict):
        return {key:_json_safe(item) for key,item in value.items()}
    if isinstance(value, (list,tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value,"item"):
        try:
            return _json_safe(value.item())
        except (ValueError,TypeError):
            pass
    return value

class Cloud:
    def __init__(self,url,key):
        if not url.startswith("https://"):
            raise ValueError("Supabase requires HTTPS.")
        role = ""
        if key.count(".")==2:
            try:
                part = key.split(".")[1]
                role = json.loads(base64.urlsafe_b64decode(part+"="*(-len(part)%4))).get("role","")
            except (ValueError,TypeError):
                raise ValueError("Invalid Supabase key.")
        if key.startswith("sb_secret_") or role=="service_role":
            raise ValueError("Use a publishable key, never a secret key.")
        self.client = create_client(url,key,options=ClientOptions(
            auto_refresh_token=False,persist_session=False,postgrest_client_timeout=15))
        self.user_id = None
        self.revision = 0

    def sign_in(self,email,password):
        result = self.client.auth.sign_in_with_password({"email":email,"password":password})
        self.user_id = str(result.user.id)
        return result.session

    def restore(self,refresh_token):
        result = self.client.auth.refresh_session(refresh_token)
        self.user_id = str(result.user.id)
        return result.session

    def session(self):
        return self.client.auth.get_session()

    def pull(self,store):
        # Ownership is enforced by RLS, and this filter also uses the primary key.
        result = self.client.table("fyntra_state").select("state,revision").eq("user_id",self.user_id).execute()
        if result.data:
            store.restore_state(result.data[0]["state"])
            self.revision = result.data[0]["revision"]
        else:
            self.revision = 0
        return self.revision

    def push(self,store):
        state = _json_safe(store.dump_state())
        encoded = json.dumps(state,allow_nan=False).encode()
        if len(encoded)>5*1024*1024:
            raise ValueError("Cloud backup exceeds 5 MB. Export your data and reduce history.")
        payload = dict(user_id=self.user_id,state=state,revision=self.revision+1,updated_at=datetime.now(timezone.utc).isoformat())
        if self.revision==0:
            try:
                result = self.client.table("fyntra_state").insert(payload).execute()
            except Exception as exc:
                raise SyncConflict("Cloud state may already exist. Export local changes before reloading cloud.") from exc
        else:
            result = self.client.table("fyntra_state").update(payload).eq("user_id",self.user_id).eq("revision",self.revision).execute()
        if not result.data:
            raise SyncConflict("A newer cloud version exists. Export local changes, then reload cloud.")
        self.revision = result.data[0]["revision"]

    def sign_out(self):
        self.client.auth.sign_out({"scope":"local"})

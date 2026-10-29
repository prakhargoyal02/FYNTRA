"""Two-step sign-in and an explicit browser refresh-token bridge.

Passwords are transient form inputs and are never persisted. Refresh tokens are
sensitive bearer credentials. sessionStorage is the default; 'Remember' opts into
localStorage. Do not use Remember on a shared device.
"""
import os
import tempfile
from pathlib import Path

import streamlit as st

from database import Store
from cloud_sync import Cloud


_BRIDGE = st.components.v2.component(
    "fyntra_auth_bridge",
    html="<span></span>",
    js="""
export default function ({data,setStateValue}) {
  const key="fyntra.refresh.v1";
  try {
    if(data.action==="clear"){
      sessionStorage.removeItem(key);localStorage.removeItem(key);
      setStateValue("result",{ready:true,token:null,remember:false});
    } else if(data.action==="write"){
      const target=data.remember?localStorage:sessionStorage;
      const other=data.remember?sessionStorage:localStorage;
      other.removeItem(key);
      target.setItem(key,data.token);
      setStateValue("result",{ready:true,token:data.token,remember:!!data.remember});
    } else {
      const local=localStorage.getItem(key);
      setStateValue("result",{ready:true,token:sessionStorage.getItem(key)||local,remember:!!local});
    }
  } catch(e){setStateValue("result",{ready:true,token:null,error:"Browser storage unavailable"});}
}
""",
)


def config():
    try:
        section = dict(st.secrets.get("supabase", {}))
    except Exception:
        section = {}
    return (
        os.getenv("FYNTRA_SUPABASE_URL", section.get("url", "")),
        os.getenv("FYNTRA_SUPABASE_KEY", section.get("publishable_key", "")),
    )


def private_store():
    directory = tempfile.TemporaryDirectory(prefix="fyntra-private-")
    st.session_state.private_directory = directory
    return Store(Path(directory.name) / "finance.db")


def _session_email(session):
    user = getattr(session, "user", None)
    return str(getattr(user, "email", "") or "").strip()


def _accept(cloud, session, remember):
    private = private_store()
    cloud.pull(private)
    st.session_state.cloud = cloud
    st.session_state.store = private
    st.session_state.mode = "private"
    st.session_state.remember = remember
    st.session_state.auth_email = _session_email(session)
    st.session_state.auth_command = {
        "action": "write",
        "token": session.refresh_token,
        "remember": remember,
    }
    st.session_state.pop("sync_error", None)


def account_identity():
    """Return a short visible name plus the signed-in email when available."""
    if st.session_state.get("mode") != "private":
        return "Sign in", ""
    email = str(st.session_state.get("auth_email", "") or "")
    profile_name = ""
    store = st.session_state.get("store")
    if store:
        try:
            profile = store.get("profile", "profile") or {}
            profile_name = str(profile.get("display_name", "") or "").strip()
        except Exception:
            profile_name = ""
    if not profile_name or profile_name == "My finances":
        local = email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
        profile_name = local.title() if local else "My account"
    return profile_name, email


def restore_browser_session():
    url, key = config()
    if not url or not key or os.getenv("FYNTRA_TESTING") == "1":
        return
    command = st.session_state.get("auth_command", {"action": "read"})
    bridge = _BRIDGE(key="fyntra-auth-bridge", data=command, on_result_change=lambda: None, height=0)
    result = bridge.result
    if result and result.get("ready"):
        if command["action"] in {"write", "clear"}:
            if (command["action"] == "clear" and not result.get("token")) or result.get("token") == command.get("token"):
                st.session_state.auth_command = {"action": "read"}
                st.session_state.auth_checked = True
                st.session_state.last_written_token = result.get("token")
        elif not st.session_state.get("auth_checked"):
            st.session_state.auth_checked = True
            if result.get("token"):
                try:
                    cloud = Cloud(url, key)
                    session = cloud.restore(result["token"])
                    _accept(cloud, session, result.get("remember", False))
                    st.rerun()
                except Exception:
                    st.session_state.auth_command = {"action": "clear"}
                    st.session_state.auth_notice = "Your saved session could not be restored. Sign in again."
    cloud = st.session_state.get("cloud")
    if cloud:
        try:
            session = cloud.session()
            if session:
                email = _session_email(session)
                if email:
                    st.session_state.auth_email = email
            if session and session.refresh_token and st.session_state.get("last_written_token") != session.refresh_token:
                st.session_state.auth_command = {
                    "action": "write",
                    "token": session.refresh_token,
                    "remember": st.session_state.get("remember", False),
                }
        except Exception:
            pass


def _sign_out():
    cloud = st.session_state.pop("cloud", None)
    if cloud:
        try:
            cloud.sign_out()
        except Exception:
            st.session_state.auth_notice = "Server sign-out could not be confirmed. Browser credentials were cleared."
    st.session_state.auth_command = {"action": "clear"}
    st.session_state.auth_checked = True
    st.session_state.mode = "demo"
    st.session_state.pop("auth_email", None)
    st.session_state.pop("store", None)
    st.session_state.pop("sync_error", None)
    st.session_state.pop("notes_loaded_key", None)
    directory = st.session_state.pop("private_directory", None)
    if directory:
        directory.cleanup()
    st.rerun()


def _login_contents(url, key):
    if not url or not key:
        st.caption("Private cloud is not configured on this copy. The fictional demo is fully available.")
        return
    if st.session_state.get("auth_notice"):
        st.caption(st.session_state.pop("auth_notice"))
    if not st.session_state.get("login_email"):
        with st.form("email-step"):
            email = st.text_input("Email", placeholder="you@example.com")
            if st.form_submit_button("Continue", use_container_width=True):
                if "@" not in email or "." not in email.split("@")[-1]:
                    st.error("Enter a valid email address.")
                else:
                    st.session_state.login_email = email.strip()
                    st.rerun()
    else:
        st.caption(st.session_state.login_email)
        with st.form("password-step", clear_on_submit=True):
            password = st.text_input("Password", type="password")
            remember = st.checkbox("Remember on this device", value=False)
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            try:
                cloud = Cloud(url, key)
                session = cloud.sign_in(st.session_state.login_email, password)
                password = ""
                _accept(cloud, session, remember)
                st.rerun()
            except Exception:
                st.error("Sign-in failed. Check your email/password and the cloud configuration.")
        if st.button("Use a different email", use_container_width=True):
            st.session_state.pop("login_email", None)
            st.rerun()
        st.caption("Use your FYNTRA email/password account. No bank credentials are needed.")


def login_panel(compact=False):
    """Render sign-in/sign-out controls. Compact mode is designed for the top-bar account popover."""
    url, key = config()
    if st.session_state.get("mode") == "private":
        name, email = account_identity()
        st.write(f"**{name}**")
        if email:
            st.caption(email)
        st.success("Private workspace", icon=":material/lock:")
        st.caption("Your changes sync to your account.")
        if st.session_state.get("sync_error"):
            st.warning("Export unsynced changes in Data & settings before signing out.")
        confirmed = st.checkbox("I exported unsynced changes") if st.session_state.get("sync_error") else True
        if st.button("Sign out", use_container_width=True, disabled=not confirmed, key="fyntra-sign-out"):
            _sign_out()
        return

    if compact:
        st.caption("PRIVATE SIGN IN")
        _login_contents(url, key)
    else:
        with st.expander("Private sign in", icon=":material/lock:"):
            _login_contents(url, key)

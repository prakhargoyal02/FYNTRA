"""Small personal utilities that live in FYNTRA's product shell."""
from __future__ import annotations

import ast
import json
import math
import operator
import os
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st


_NOTES_BRIDGE = st.components.v2.component(
    "fyntra_notes_bridge",
    html="<span></span>",
    js="""
export default function ({data,setStateValue}) {
  try {
    const key=data.key;
    if(data.action==="write"){
      localStorage.setItem(key,data.payload||"[]");
      setStateValue("result",{ready:true,key:key,payload:data.payload||"[]",action:"write"});
    } else {
      setStateValue("result",{ready:true,key:key,payload:localStorage.getItem(key)||"[]",action:"read"});
    }
  } catch(e){
    setStateValue("result",{ready:true,key:data.key,payload:"[]",error:"Browser storage unavailable"});
  }
}
""",
)

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def calculate(expression: str) -> float:
    """Evaluate a deliberately small arithmetic language without Python eval()."""
    expression = str(expression or "").strip()
    if not expression:
        raise ValueError("Enter a calculation.")
    if len(expression) > 120:
        raise ValueError("Keep calculations under 120 characters.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("That calculation is not valid.") from exc

    def solve(node):
        if isinstance(node, ast.Expression):
            return solve(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](solve(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = solve(node.left), solve(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 12:
                raise ValueError("Exponent is too large.")
            try:
                value = _BIN_OPS[type(node.op)](left, right)
            except ZeroDivisionError as exc:
                raise ValueError("Cannot divide by zero.") from exc
            if not math.isfinite(float(value)) or abs(float(value)) > 1e15:
                raise ValueError("Result is outside the supported range.")
            return float(value)
        raise ValueError("Use numbers, parentheses, +, -, *, /, //, %, or ** only.")

    return solve(tree)


def _note_key():
    cloud = st.session_state.get("cloud")
    user_id = getattr(cloud, "user_id", None) if cloud else None
    return f"fyntra.notes.v1.{user_id or 'demo'}"


def _clean_notes(value):
    if not isinstance(value, list):
        return []
    notes = []
    for raw in value[:30]:
        if not isinstance(raw, dict):
            continue
        ident = str(raw.get("id") or uuid4())
        title = str(raw.get("title") or "Untitled")[:80]
        body = str(raw.get("body") or "")[:1000]
        created = str(raw.get("created") or "")[:40]
        notes.append({"id": ident, "title": title, "body": body, "pinned": bool(raw.get("pinned")), "created": created})
    return notes


def _decode_notes(payload):
    try:
        return _clean_notes(json.loads(payload or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _load_notes():
    key = _note_key()
    if os.getenv("FYNTRA_TESTING") == "1":
        if st.session_state.get("notes_loaded_key") != key:
            st.session_state.notes_cache = []
            st.session_state.notes_loaded_key = key
        return _clean_notes(st.session_state.get("notes_cache", []))

    command = st.session_state.get("notes_command")
    if not command or command.get("key") != key:
        command = {"action": "read", "key": key}
        st.session_state.notes_command = command
    bridge = _NOTES_BRIDGE(key="fyntra-notes-bridge", data=command, on_result_change=lambda: None, height=0)
    result = bridge.result
    if result and result.get("ready") and result.get("key") == key:
        notes = _decode_notes(result.get("payload"))
        st.session_state.notes_cache = notes
        st.session_state.notes_loaded_key = key
        if command.get("action") == "write":
            st.session_state.notes_command = {"action": "read", "key": key}
        if result.get("error"):
            st.session_state.notes_storage_error = result["error"]
    elif st.session_state.get("notes_loaded_key") != key:
        st.session_state.notes_cache = []
    return _clean_notes(st.session_state.get("notes_cache", []))


def _persist_notes(notes):
    notes = _clean_notes(notes)
    st.session_state.notes_cache = notes
    st.session_state.notes_loaded_key = _note_key()
    if os.getenv("FYNTRA_TESTING") != "1":
        st.session_state.notes_command = {
            "action": "write",
            "key": _note_key(),
            "payload": json.dumps(notes, separators=(",", ":")),
        }


def _calculator_panel():
    st.caption("CALCULATOR")
    expression = st.text_input(
        "Calculation",
        key="fyntra-calculator-expression",
        placeholder="Example: (12500 + 4200) / 3",
        label_visibility="collapsed",
    )
    if st.button("Calculate", key="fyntra-calculate", type="primary", use_container_width=True):
        try:
            st.session_state.fyntra_calculator_result = calculate(expression)
            st.session_state.pop("fyntra_calculator_error", None)
        except ValueError as exc:
            st.session_state.fyntra_calculator_error = str(exc)
    if st.session_state.get("fyntra_calculator_error"):
        st.error(st.session_state.fyntra_calculator_error)
    elif "fyntra_calculator_result" in st.session_state:
        result = st.session_state.fyntra_calculator_result
        text = f"{result:,.10f}".rstrip("0").rstrip(".")
        st.metric("Result", text)
    st.caption("Supports +, −, ×, ÷, //, %, powers and parentheses.")


def _set_edit(note_id):
    st.session_state.fyntra_note_edit = note_id


def _new_note():
    st.session_state.fyntra_note_edit = "new"


def _notepad_panel():
    st.caption("STICKY NOTEPAD")
    notes = _load_notes()
    if st.session_state.get("notes_storage_error"):
        st.caption("Browser storage is unavailable, so notes may not survive a refresh.")

    ordered = sorted(notes, key=lambda item: (not item["pinned"], item.get("created", "")))
    if not ordered:
        st.caption("No notes yet. Pin the important ones and they will stay at the top.")
    for note in ordered:
        with st.container(border=True, key=f"sticky-note-{note['id']}"):
            marker = "📌 " if note["pinned"] else ""
            st.write(f"**{marker}{note['title']}**")
            if note["body"]:
                st.write(note["body"])
            pin_col, edit_col, delete_col = st.columns(3, gap="small")
            if pin_col.button("Unpin" if note["pinned"] else "Pin", key=f"pin-{note['id']}", use_container_width=True):
                updated = [{**item, "pinned": (not item["pinned"] if item["id"] == note["id"] else item["pinned"])} for item in notes]
                _persist_notes(updated)
                st.rerun()
            edit_col.button("Edit", key=f"edit-{note['id']}", use_container_width=True, on_click=_set_edit, args=(note["id"],))
            if delete_col.button("Delete", key=f"delete-{note['id']}", use_container_width=True):
                _persist_notes([item for item in notes if item["id"] != note["id"]])
                if st.session_state.get("fyntra_note_edit") == note["id"]:
                    st.session_state.pop("fyntra_note_edit", None)
                st.rerun()

    if len(notes) < 30:
        st.button("+ New note", key="new-sticky-note", use_container_width=True, on_click=_new_note)
    else:
        st.caption("30-note limit reached. Delete an old note to add another.")

    editing = st.session_state.get("fyntra_note_edit")
    if editing:
        row = next((item for item in notes if item["id"] == editing), None) if editing != "new" else None
        row = row or {"title": "", "body": "", "pinned": False}
        with st.form("sticky-note-editor"):
            title = st.text_input("Title", row["title"], max_chars=80)
            body = st.text_area("Note", row["body"], max_chars=1000, height=130)
            pinned = st.checkbox("Pin this note", value=row["pinned"])
            submitted = st.form_submit_button("Save note", type="primary", use_container_width=True)
        if submitted:
            if not title.strip() and not body.strip():
                st.error("Write a title or note first.")
            else:
                if editing == "new":
                    notes.append({
                        "id": str(uuid4()),
                        "title": title.strip() or "Untitled",
                        "body": body.strip(),
                        "pinned": pinned,
                        "created": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    notes = [
                        {**item, "title": title.strip() or "Untitled", "body": body.strip(), "pinned": pinned}
                        if item["id"] == editing else item
                        for item in notes
                    ]
                _persist_notes(notes)
                st.session_state.pop("fyntra_note_edit", None)
                st.rerun()


def tools_panel():
    """Render calculator and sticky notes in a compact panel."""
    tool = st.radio(
        "Utility",
        ["Calculator", "Notepad"],
        horizontal=True,
        key="fyntra-utility",
        label_visibility="collapsed",
    )
    if tool == "Notepad":
        _notepad_panel()
    else:
        _calculator_panel()


def _pick_quick_tool(name):
    st.session_state.fyntra_quick_tool = name


def _toggle_dock():
    current = st.session_state.get("fyntra_tools_dock", "right")
    st.session_state.fyntra_tools_dock = "left" if current == "right" else "right"


def floating_tools():
    """Always-visible, dockable utility launcher outside the navigation menu."""
    side = st.session_state.setdefault("fyntra_tools_dock", "right")
    tool = st.session_state.setdefault("fyntra_quick_tool", "Calculator")
    with st.container(key=f"floating-tools-{side}"):
        with st.popover("Tools", icon=":material/apps:"):
            st.caption("QUICK TOOLS")
            calc_col, note_col = st.columns(2, gap="small")
            calc_col.button(
                "Calculator",
                icon=":material/calculate:",
                key="quick-tool-calculator",
                type="primary" if tool == "Calculator" else "secondary",
                use_container_width=True,
                on_click=_pick_quick_tool,
                args=("Calculator",),
            )
            note_col.button(
                "Notes",
                icon=":material/sticky_note_2:",
                key="quick-tool-notes",
                type="primary" if tool == "Notepad" else "secondary",
                use_container_width=True,
                on_click=_pick_quick_tool,
                args=("Notepad",),
            )
            st.divider()
            if st.session_state.get("fyntra_quick_tool", "Calculator") == "Notepad":
                _notepad_panel()
            else:
                _calculator_panel()
            st.divider()
            st.button(
                "Dock left" if side == "right" else "Dock right",
                icon=":material/swap_horiz:",
                key="quick-tool-dock",
                use_container_width=True,
                on_click=_toggle_dock,
            )

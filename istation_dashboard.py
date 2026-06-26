#!/usr/bin/env python3
"""
istation_dashboard.py
=====================
Local Streamlit dashboard for the Istation Historical Data Pull tool.

Run with:
    streamlit run istation_dashboard.py
"""

import csv
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ── PATHS ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent
REQUEST_CSV  = SCRIPT_DIR / "Historical Data Request - Sheet1.csv"
EXTRACTOR    = SCRIPT_DIR / "istation_extractor.py"
PREFS_PATH   = SCRIPT_DIR / ".dashboard_prefs.json"

CSV_FIELDS   = ["District", "State", "Product", "School Year(s)", "Requested By", "Completed"]
PRODUCTS     = ["Reading", "Lectura", "Math"]

# ── THEME ─────────────────────────────────────────────────────────────────────

_PALETTES = {
    "blue": {
        "canvas": "#0E1117", "surface": "#161B2E", "surface_raised": "#1E2640",
        "border_sub": "#1E2640", "border": "#2D3A55",
        "text_hi": "#E2E8F0", "text_mid": "#94A3B8", "text_lo": "#4A5568",
        "tab_inactive": "#7A8499", "tab_active_bg": "#1E2640",
        "btn_primary": "linear-gradient(135deg,#1D4ED8 0%,#3B82F6 100%)",
        "btn_primary_text": "#ffffff",
        "btn_secondary_border": "#2D3A55", "btn_secondary_text": "#94A3B8",
        "btn_secondary_hover_border": "#3B82F6", "btn_secondary_hover_text": "#E2E8F0",
        "input_border": "#2D3A55", "input_focus": "#3B82F6",
        "input_focus_shadow": "rgba(59,130,246,.2)", "placeholder": "#4A5568",
        "tag_bg": "rgba(59,130,246,.15)", "tag_border": "rgba(59,130,246,.4)",
        "tag_text": "#93C5FD", "popover_hover": "#1E2640",
        "section_label": "#4A5568", "helper": "#4A5568", "caption": "#4A5568",
        "metric_top": "#2D3A55",
        "log_bg": "#0D1117", "log_text": "#7dd3a8", "log_border": "#1E2640",
        "header_label": "#4A5568", "header_title": "#E2E8F0",
        "header_rule": "linear-gradient(90deg,#1D4ED8,#3B82F6)",
        "ready_label": "#4A5568", "ready_text": "#94A3B8",
        "step_done": ("#052E16", "#22C55E", "#86EFAC"),
        "step_active": ("#1E2D4F", "#3B82F6", "#E2E8F0"),
        "step_idle": ("#161B2E", "#2D3A55", "#4A5568"),
        "step_done_line": "#22C55E", "step_idle_line": "#1E2640",
        "step_nav_bg": "#0E1117", "step_nav_border": "#1E2640",
    },
    "dark": {
        "canvas": "#0E1117", "surface": "#262730", "surface_raised": "#31333F",
        "border_sub": "#31333F", "border": "#41434F",
        "text_hi": "#FAFAFA", "text_mid": "#808495", "text_lo": "#555770",
        "tab_inactive": "#808495", "tab_active_bg": "#31333F",
        "btn_primary": "linear-gradient(135deg,#7C3AED 0%,#A78BFA 100%)",
        "btn_primary_text": "#ffffff",
        "btn_secondary_border": "#41434F", "btn_secondary_text": "#808495",
        "btn_secondary_hover_border": "#A78BFA", "btn_secondary_hover_text": "#FAFAFA",
        "input_border": "#41434F", "input_focus": "#A78BFA",
        "input_focus_shadow": "rgba(167,139,250,.2)", "placeholder": "#555770",
        "tag_bg": "rgba(167,139,250,.15)", "tag_border": "rgba(167,139,250,.4)",
        "tag_text": "#C4B5FD", "popover_hover": "#31333F",
        "section_label": "#555770", "helper": "#555770", "caption": "#555770",
        "metric_top": "#41434F",
        "log_bg": "#090A0D", "log_text": "#7dd3a8", "log_border": "#31333F",
        "header_label": "#555770", "header_title": "#FAFAFA",
        "header_rule": "linear-gradient(90deg,#7C3AED,#A78BFA)",
        "ready_label": "#555770", "ready_text": "#808495",
        "step_done": ("#1E1030", "#7C3AED", "#C4B5FD"),
        "step_active": ("#1E1A30", "#A78BFA", "#FAFAFA"),
        "step_idle": ("#262730", "#41434F", "#555770"),
        "step_done_line": "#7C3AED", "step_idle_line": "#31333F",
        "step_nav_bg": "#0E1117", "step_nav_border": "#31333F",
    },
    "light": {
        "canvas": "#F8F9FA", "surface": "#FFFFFF", "surface_raised": "#F0F2F6",
        "border_sub": "#E2E8F0", "border": "#CBD5E1",
        "text_hi": "#0F172A", "text_mid": "#475569", "text_lo": "#94A3B8",
        "tab_inactive": "#64748B", "tab_active_bg": "#E2E8F0",
        "btn_primary": "linear-gradient(135deg,#0EA5E9 0%,#38BDF8 100%)",
        "btn_primary_text": "#ffffff",
        "btn_secondary_border": "#CBD5E1", "btn_secondary_text": "#475569",
        "btn_secondary_hover_border": "#0EA5E9", "btn_secondary_hover_text": "#0F172A",
        "input_border": "#CBD5E1", "input_focus": "#0EA5E9",
        "input_focus_shadow": "rgba(14,165,233,.2)", "placeholder": "#94A3B8",
        "tag_bg": "rgba(14,165,233,.1)", "tag_border": "rgba(14,165,233,.35)",
        "tag_text": "#0369A1", "popover_hover": "#F0F2F6",
        "section_label": "#64748B", "helper": "#94A3B8", "caption": "#94A3B8",
        "metric_top": "#CBD5E1",
        "log_bg": "#F1F5F9", "log_text": "#166534", "log_border": "#E2E8F0",
        "header_label": "#94A3B8", "header_title": "#0F172A",
        "header_rule": "linear-gradient(90deg,#0EA5E9,#38BDF8)",
        "ready_label": "#94A3B8", "ready_text": "#475569",
        "step_done": ("#DCFCE7", "#16A34A", "#15803D"),
        "step_active": ("#EFF6FF", "#0EA5E9", "#0C4A6E"),
        "step_idle": ("#F0F2F6", "#CBD5E1", "#94A3B8"),
        "step_done_line": "#16A34A", "step_idle_line": "#CBD5E1",
        "step_nav_bg": "#F8F9FA", "step_nav_border": "#E2E8F0",
    },
}


def _theme_css(p: dict) -> str:
    return f"""
.stDeployButton,[data-testid="stToolbarActions"],#MainMenu,footer{{display:none!important;}}
header[data-testid="stHeader"]{{background:transparent;}}
.stApp{{background-color:{p['canvas']};}}
[data-testid="stAppViewContainer"]>.main>.block-container{{
    padding-top:3rem;padding-bottom:4rem;max-width:1100px;
}}
[data-testid="stVerticalBlockBorderWrapper"]{{
    background:{p['surface']}!important;
    border:1px solid {p['border_sub']}!important;border-radius:10px!important;
}}
.stTabs [data-baseweb="tab-list"]{{
    gap:4px;background-color:{p['surface']};border-radius:10px;padding:4px;
    border:1px solid {p['border_sub']};
}}
.stTabs [data-baseweb="tab"]{{
    border-radius:8px;padding:0.4rem 1.2rem;font-weight:500;
    color:{p['tab_inactive']};background-color:transparent;border:none;
}}
.stTabs [aria-selected="true"]{{
    background-color:{p['tab_active_bg']}!important;color:{p['text_hi']}!important;
    box-shadow:0 1px 4px rgba(0,0,0,0.4);
}}
.stTabs [data-baseweb="tab-border"],.stTabs [data-baseweb="tab-highlight"]{{display:none;}}
.section-label{{
    font-size:0.68rem;font-weight:700;letter-spacing:0.1em;
    text-transform:uppercase;color:{p['section_label']};
    margin-bottom:0.6rem;display:block;
}}
.metric-row{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:1rem;}}
.metric-card{{
    flex:1;min-width:110px;background:{p['surface']};border-radius:10px;
    padding:1rem 1.2rem;border:1px solid {p['border_sub']};
    border-top:3px solid {p['metric_top']};
}}
.metric-card.green{{border-top-color:#22C55E;}}
.metric-card.amber{{border-top-color:#F59E0B;}}
.metric-card.blue{{border-top-color:#3B82F6;}}
.metric-label{{
    font-size:0.68rem;font-weight:700;letter-spacing:0.08em;
    text-transform:uppercase;color:{p['section_label']};margin-bottom:0.4rem;
}}
.metric-value{{font-size:1.3rem;font-weight:600;color:{p['text_hi']};line-height:1.2;}}
.metric-value.sm{{font-size:0.92rem;font-weight:400;color:{p['text_mid']};}}
.stButton>button[kind="primary"]{{
    background:{p['btn_primary']};border:none;border-radius:8px;
    font-weight:600;color:{p['btn_primary_text']};transition:opacity .15s;
}}
.stButton>button[kind="primary"]:hover{{opacity:0.85;}}
.stButton>button[kind="secondary"]{{
    border-radius:8px;font-weight:500;background-color:{p['surface']};
    border:1px solid {p['btn_secondary_border']};color:{p['btn_secondary_text']};
}}
.stButton>button[kind="secondary"]:hover{{
    border-color:{p['btn_secondary_hover_border']};color:{p['btn_secondary_hover_text']};
}}
.stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox select{{
    background-color:{p['surface']}!important;border:1px solid {p['input_border']}!important;
    border-radius:8px!important;color:{p['text_hi']}!important;
}}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus{{
    border-color:{p['input_focus']}!important;
    box-shadow:0 0 0 2px {p['input_focus_shadow']}!important;
}}
.stTextInput input::placeholder{{color:{p['placeholder']}!important;}}
.helper-text{{color:{p['helper']};font-size:0.78rem;line-height:1.5;margin-bottom:0.75rem;}}
.stAlert{{border-radius:10px;font-size:0.86rem;}}
hr{{border-color:{p['border_sub']}!important;margin:1.2rem 0;}}
.stCaption p{{color:{p['caption']}!important;font-size:0.77rem!important;}}
[data-testid="stDataFrame"]{{border-radius:8px;overflow:hidden;}}
"""


# ── PREFS ─────────────────────────────────────────────────────────────────────

def _load_prefs() -> dict:
    try:
        return json.loads(PREFS_PATH.read_text())
    except Exception:
        return {}


def _save_prefs(data: dict):
    try:
        existing = _load_prefs()
        existing.update(data)
        PREFS_PATH.write_text(json.dumps(existing, indent=2))
    except Exception:
        pass


# ── CSV HELPERS ───────────────────────────────────────────────────────────────

def read_csv() -> list[dict]:
    if not REQUEST_CSV.exists():
        return []
    with open(REQUEST_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict]):
    with open(REQUEST_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def pending_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("Completed", "").strip().upper() != "TRUE"]


# ── UI HELPERS ────────────────────────────────────────────────────────────────

def section_label(text: str):
    st.markdown(f'<span class="section-label">{text}</span>', unsafe_allow_html=True)


def helper_text(text: str):
    st.markdown(f'<p class="helper-text">{text}</p>', unsafe_allow_html=True)


def metric_card(label: str, value, small=False, color="") -> str:
    cls = f"metric-card {color}".strip()
    vcls = "metric-value sm" if small else "metric-value"
    return (
        f'<div class="{cls}">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="{vcls}">{value}</div>'
        f'</div>'
    )


def auto_scroll_log(logs: list[str], height: int = 400):
    p = _PALETTES[st.session_state.theme]
    text = "\n".join(logs).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    components.html(
        f'<div id="log" style="background:{p["log_bg"]};color:{p["log_text"]};'
        f'font-family:\'JetBrains Mono\',\'Fira Code\',ui-monospace,monospace;'
        f'font-size:11px;line-height:1.8;height:{height}px;overflow-y:auto;'
        f'padding:16px 20px;border-radius:4px;white-space:pre-wrap;'
        f'word-break:break-word;border:1px solid {p["log_border"]};">'
        f'{text}</div>'
        f'<script>var e=document.getElementById("log");if(e)e.scrollTop=e.scrollHeight;</script>',
        height=height + 8,
    )


def drain_queue():
    while not st.session_state.log_queue.empty():
        try:
            st.session_state.logs.append(st.session_state.log_queue.get_nowait())
        except queue.Empty:
            break


def render_step_navigator(current_step: int):
    p = _PALETTES[st.session_state.theme]
    steps = [("1", "Configure"), ("2", "Run")]
    items = ""
    for i, (num, label) in enumerate(steps):
        n = int(num)
        done, active = n < current_step, n == current_step
        nc, lc, tc = (p["step_done"] if done else p["step_active"] if active else p["step_idle"])
        dot = (
            f'<div style="width:28px;height:28px;border-radius:50%;'
            f'background:{nc};border:1px solid {lc};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:0.72rem;font-weight:600;color:{tc};">'
            f'{"✓" if done else num}</div>'
        )
        lbl = (
            f'<div style="font-size:0.60rem;font-weight:{"700" if active else "500"};'
            f'color:{tc};white-space:nowrap;margin-top:5px;'
            f'letter-spacing:0.12em;text-transform:uppercase;">{label}</div>'
        )
        line_c = p["step_done_line"] if done else p["step_idle_line"]
        line = (
            f'<div style="flex:1;height:1px;background:{line_c};'
            f'margin:0 16px;margin-top:-20px;"></div>'
            if i < len(steps) - 1 else ""
        )
        items += (
            f'<div style="display:flex;align-items:center;flex:1 1 0;">'
            f'<div style="display:flex;flex-direction:column;align-items:center;">'
            f'{dot}{lbl}</div>{line}</div>'
        )
    components.html(
        f'<div style="display:flex;align-items:flex-start;'
        f'background:{p["step_nav_bg"]};border-radius:10px;'
        f'padding:1.1rem 2.5rem 0.8rem;border:1px solid {p["step_nav_border"]};">'
        f'{items}</div>',
        height=80,
    )


# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Istation Historical Data Pull",
    layout="wide",
)

_prefs = _load_prefs()

_defaults = {
    "theme":       _prefs.get("theme", "blue"),
    "run_step":    1,
    "running":     False,
    "logs":        [],
    "log_queue":   queue.Queue(),
    "proc":        None,
    # Add-row form state
    "add_district":   "",
    "add_state":      "",
    "add_product":    "Reading",
    # Reports tab
    "rpt_step":          1,
    "rpt_running":       False,
    "rpt_logs":          [],
    "rpt_log_queue":     queue.Queue(),
    "rpt_org_oid":       _prefs.get("rpt_org_oid", ""),
    "rpt_dist_key":      0,
    "rpt_year":          _prefs.get("rpt_year", 2024),
    "rpt_years":         _prefs.get("rpt_years", [2024]),
    "rpt_products":      _prefs.get("rpt_products", ["Reading"]),
    "rpt_report_types":  _prefs.get("rpt_report_types", ["assessment"]),
    "rpt_assess_mode":   _prefs.get("rpt_assess_mode", "ytd"),
    "rpt_grade":         _prefs.get("rpt_grade", "All"),
    "rpt_skill":         _prefs.get("rpt_skill", "Overall"),
    "rpt_sel_months":    list(range(12)),
    "rpt_base_dir":      _prefs.get("rpt_base_dir", str(Path.home() / "Documents" / "Istation Reports")),
    "rpt_email":         _prefs.get("rpt_email", ""),
    "add_years":      "",
    "add_requested":  "",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

_P = _PALETTES[st.session_state.theme]
st.markdown(f"<style>{_theme_css(_P)}</style>", unsafe_allow_html=True)
st.markdown("""
<style>
section[data-testid="stMain"] > div:first-child,
.block-container { max-width: 1100px !important; padding-left: 2rem !important; padding-right: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────

_h1, _h2 = st.columns([3, 1])
with _h2:
    _tc1, _tc2, _tc3 = st.columns(3)
    with _tc1:
        if st.button("Blue",  key="th_blue",  use_container_width=True,
                     type="primary" if st.session_state.theme == "blue"  else "secondary"):
            st.session_state.theme = "blue";  _save_prefs({"theme": "blue"});  st.rerun()
    with _tc2:
        if st.button("Dark",  key="th_dark",  use_container_width=True,
                     type="primary" if st.session_state.theme == "dark"  else "secondary"):
            st.session_state.theme = "dark";  _save_prefs({"theme": "dark"});  st.rerun()
    with _tc3:
        if st.button("Light", key="th_light", use_container_width=True,
                     type="primary" if st.session_state.theme == "light" else "secondary"):
            st.session_state.theme = "light"; _save_prefs({"theme": "light"}); st.rerun()

with _h1:
    st.markdown(
        f'<div style="padding:0 0 2.5rem;">'
        f'<div style="font-size:0.65rem;font-weight:700;color:{_P["header_label"]};'
        f'letter-spacing:0.22em;text-transform:uppercase;margin-bottom:0.5rem;">'
        f'Istation</div>'
        f'<div style="font-size:1.9rem;font-weight:600;color:{_P["header_title"]};'
        f'letter-spacing:-0.01em;line-height:1.15;">'
        f'Historical Data Pull</div>'
        f'<div style="width:28px;height:2px;background:{_P["header_rule"]};'
        f'border-radius:2px;margin-top:1.2rem;"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

tab_sheet, tab_run, tab_rpt = st.tabs(["  Request Sheet  ", "  Historical Run  ", "  Reports  "])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — REQUEST SHEET
# ══════════════════════════════════════════════════════════════════════════════

with tab_sheet:
    rows = read_csv()

    # ── Summary metrics ───────────────────────────────────────────────────────
    total     = len(rows)
    completed = sum(1 for r in rows if r.get("Completed", "").strip().upper() == "TRUE")
    pending   = total - completed

    st.markdown(
        '<div class="metric-row">'
        + metric_card("Total Rows",  total,     color="blue")
        + metric_card("Pending",     pending,   color="amber")
        + metric_card("Completed",   completed, color="green")
        + '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Row table ─────────────────────────────────────────────────────────────
    section_label("Request Rows")

    if not rows:
        st.info("No rows yet — add one below.")
    else:
        hdr = st.columns([2.5, 1.2, 1, 1.2, 1.5, 1, 0.7, 0.7])
        for col, label in zip(hdr, ["District", "State", "Product", "Year(s)", "Requested By", "Status", "", ""]):
            col.markdown(
                f'<span style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
                f'text-transform:uppercase;color:{_P["text_lo"]};">{label}</span>',
                unsafe_allow_html=True,
            )

        for i, row in enumerate(rows):
            is_done = row.get("Completed", "").strip().upper() == "TRUE"
            status_color = "#22C55E" if is_done else "#F59E0B"
            status_label = "✓ Done" if is_done else "Pending"

            c = st.columns([2.5, 1.2, 1, 1.2, 1.5, 1, 0.7, 0.7])
            c[0].markdown(
                f'<span style="color:{_P["text_hi"]};font-size:0.85rem;">{row.get("District","")}</span>',
                unsafe_allow_html=True,
            )
            c[1].markdown(
                f'<span style="color:{_P["text_mid"]};font-size:0.85rem;">{row.get("State","")}</span>',
                unsafe_allow_html=True,
            )
            c[2].markdown(
                f'<span style="color:{_P["text_mid"]};font-size:0.85rem;">{row.get("Product","")}</span>',
                unsafe_allow_html=True,
            )
            c[3].markdown(
                f'<span style="color:{_P["text_mid"]};font-size:0.85rem;">{row.get("School Year(s)","")}</span>',
                unsafe_allow_html=True,
            )
            c[4].markdown(
                f'<span style="color:{_P["text_mid"]};font-size:0.85rem;">{row.get("Requested By","")}</span>',
                unsafe_allow_html=True,
            )
            c[5].markdown(
                f'<span style="color:{status_color};font-size:0.82rem;font-weight:600;">{status_label}</span>',
                unsafe_allow_html=True,
            )

            # Reset button (only shown for completed rows)
            if is_done:
                if c[6].button("↺", key=f"reset_{i}", help="Mark as pending"):
                    rows[i]["Completed"] = ""
                    write_csv(rows)
                    st.rerun()
            else:
                c[6].markdown("")

            # Delete button
            if c[7].button("✕", key=f"del_{i}", help="Delete this row"):
                rows.pop(i)
                write_csv(rows)
                st.rerun()

    st.divider()

    # ── Add row form ──────────────────────────────────────────────────────────
    with st.container(border=True):
        section_label("Add Row")
        helper_text("One row per district + product. Use year ranges like 2021-2025.")

        f1, f2, f3 = st.columns([3, 1.5, 1])
        with f1:
            district_val = st.text_input(
                "District", placeholder="e.g. Denver Language School",
                key="add_district_inp",
            )
        with f2:
            state_val = st.text_input(
                "State", placeholder="e.g. Florida",
                key="add_state_inp",
            )
        with f3:
            product_val = st.selectbox(
                "Product", options=PRODUCTS, key="add_product_inp",
            )

        f4, f5 = st.columns([1.5, 3])
        with f4:
            years_val = st.text_input(
                "School Year(s)", placeholder="e.g. 2021-2025 or 2024",
                key="add_years_inp",
            )
        with f5:
            requested_val = st.text_input(
                "Requested By", placeholder="e.g. Julie T",
                key="add_requested_inp",
            )

        can_add = bool(district_val.strip() and state_val.strip() and years_val.strip())
        if st.button("Add Row", type="primary", disabled=not can_add):
            new_row = {
                "District":       district_val.strip(),
                "State":          state_val.strip(),
                "Product":        product_val,
                "School Year(s)": years_val.strip(),
                "Requested By":   requested_val.strip(),
                "Completed":      "",
            }
            rows = read_csv()
            rows.append(new_row)
            write_csv(rows)
            st.success(f"Added: {new_row['District']} — {new_row['Product']} {new_row['School Year(s)']}")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RUN
# ══════════════════════════════════════════════════════════════════════════════

with tab_run:
    rows = read_csv()
    _pending = pending_rows(rows)

    # ── STEP 1: Configure ─────────────────────────────────────────────────────
    if st.session_state.run_step == 1:
        render_step_navigator(1)
        st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)

        # Pending summary
        total     = len(rows)
        completed = total - len(_pending)

        st.markdown(
            '<div class="metric-row">'
            + metric_card("Total Rows",     total,          color="blue")
            + metric_card("Pending",        len(_pending),  color="amber")
            + metric_card("Completed",      completed,      color="green")
            + '</div>',
            unsafe_allow_html=True,
        )

        if _pending:
            with st.container(border=True):
                section_label(f"Pending Rows ({len(_pending)})")
                for r in _pending:
                    st.markdown(
                        f'<span style="color:{_P["text_hi"]};font-size:0.88rem;">'
                        f'<b>{r["District"]}</b></span>'
                        f'<span style="color:{_P["text_mid"]};font-size:0.85rem;"> — '
                        f'{r["Product"]} · {r["School Year(s)"]} · {r["State"]}</span>',
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No pending rows. Add rows in the Request Sheet tab or reset completed rows.")

        st.divider()

        # Python interpreter path
        with st.container(border=True):
            section_label("Python Interpreter")
            helper_text("Must be the interpreter with selenium and requests installed.")
            _py_default = _prefs.get("python_path", sys.executable)
            _py_val = st.text_input(
                "Python path", value=_py_default, key="py_path_inp",
                label_visibility="collapsed",
            )
            if _py_val != _prefs.get("python_path", ""):
                _save_prefs({"python_path": _py_val})

        st.divider()
        _, _, _r = st.columns([2, 6, 2])
        with _r:
            if st.button("Review & Run →", type="primary",
                         disabled=not _pending, use_container_width=True):
                st.session_state.run_step = 2
                st.rerun()

    # ── STEP 2: Run ───────────────────────────────────────────────────────────
    elif st.session_state.run_step == 2:
        render_step_navigator(2)
        st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)

        # Pending summary cards
        st.markdown(
            '<div class="metric-row">'
            + metric_card("Pending Rows", len(_pending), color="amber")
            + metric_card("Script", "istation_extractor.py", small=True)
            + metric_card("Target", "secure.istation.com", small=True)
            + '</div>',
            unsafe_allow_html=True,
        )

        _already_ran = bool(st.session_state.logs)

        # Ready message (pre-run)
        if not st.session_state.running and not _already_ran:
            st.markdown(
                '<div style="padding:2rem 0 1.5rem;text-align:center;">'
                f'<div style="font-size:0.62rem;letter-spacing:0.2em;text-transform:uppercase;'
                f'color:{_P["ready_label"]};margin-bottom:0.8rem;">Ready</div>'
                f'<div style="font-size:0.9rem;font-weight:400;color:{_P["ready_text"]};'
                f'max-width:480px;margin:0 auto;line-height:2;">'
                f'A Chrome window will open. Sign in via Google SSO when prompted, '
                f'then complete your password and 2FA. Downloads begin automatically after login.'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        # Run / Running buttons
        _c1, _c2, _c3 = st.columns([2, 3, 2])
        with _c2:
            if not st.session_state.running:
                _btn_cols = st.columns([4, 1]) if _already_ran else [st.container(), None]
                with _btn_cols[0]:
                    _lbl = "Run Again" if _already_ran else "Start Run"
                    _start = st.button(_lbl, type="primary",
                                       key="start_btn", use_container_width=True)
                if _already_ran and _btn_cols[1]:
                    with _btn_cols[1]:
                        if st.button("✕", key="clear_logs", help="Clear logs"):
                            st.session_state.logs = []
                            st.session_state.log_queue = queue.Queue()
                            st.rerun()
                _start_retry = False
            else:
                _cols = st.columns([4, 1])
                with _cols[0]:
                    st.button("Running…", disabled=True, use_container_width=True)
                with _cols[1]:
                    if st.button("✕", key="stop_btn", help="Force stop"):
                        if st.session_state.proc:
                            try:
                                st.session_state.proc.terminate()
                            except Exception:
                                pass
                        st.session_state.running = False
                        st.rerun()
                _start = False

        # Launch
        if _start and not st.session_state.running:
            st.session_state.logs = []
            st.session_state.log_queue = queue.Queue()
            st.session_state.running = True
            _py = _prefs.get("python_path", sys.executable)
            _q = st.session_state.log_queue

            def _run_extractor(_py=_py, _q=_q):
                try:
                    proc = subprocess.Popen(
                        [_py, str(EXTRACTOR)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        cwd=str(SCRIPT_DIR),
                    )
                    st.session_state.proc = proc
                    for line in proc.stdout:
                        _q.put(line.rstrip())
                    proc.wait()
                    _q.put(f"\n— Process exited with code {proc.returncode} —")
                except Exception as exc:
                    _q.put(f"❌ Failed to launch extractor: {exc}")
                finally:
                    st.session_state.running = False
                    st.session_state.proc = None

            threading.Thread(target=_run_extractor, daemon=True).start()
            st.rerun()

        # Log output
        if st.session_state.running or _already_ran:
            if st.session_state.running:
                st.info(
                    "Chrome is opening — complete the Google SSO prompt when the browser appears. "
                    "Downloads will start automatically after login."
                )
            drain_queue()
            auto_scroll_log(st.session_state.logs, height=420)
            if st.session_state.running:
                time.sleep(1)
                st.rerun()

            # Completion banner
            if not st.session_state.running and _already_ran:
                log_text = "\n".join(st.session_state.logs)
                if "Process exited with code 0" in log_text:
                    st.success("Run complete — all districts processed successfully.")
                elif "Process exited with code" in log_text:
                    st.warning("Run finished with errors — review the log above.")

        # Bottom nav
        st.divider()
        _l, _, _r = st.columns([2, 6, 2])
        with _l:
            if st.button("← Configure", key="back_btn", use_container_width=True,
                         disabled=st.session_state.running):
                st.session_state.run_step = 1
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — REPORTS (single flat form, on-demand)
# ══════════════════════════════════════════════════════════════════════════════

with tab_rpt:
    from istation_live_actions import (
        SKILLS as _SKILLS,
        SCHOOL_YEAR_LABELS as _SY_LABELS,
        run_istation_reports as _run_rpt,
    )

    _IST_REPORT_OPTIONS = [
        ("assessment",            "Executive Summary"),
        ("usage",                 "Usage"),
        ("usage_trend",           "Usage Trend"),
        ("level_movement",        "Level Movement"),
        ("assessment_completion", "Completion"),
    ]
    _GRADE_OPTS = ["All", "PK", "K", "1st", "2nd", "3rd", "4th", "5th",
                   "6th", "7th", "8th", "9th", "10th", "11th", "12th"]
    _SY_OPTIONS = list(range(2018, 2025))
    _SY_DISPLAY = [f"{y}-{str(y+1)[-2:]}" for y in _SY_OPTIONS]
    _SY_LABEL_TO_YR = {f"{y}-{str(y+1)[-2:]}": y for y in _SY_OPTIONS}

    def _rpt_drain():
        while not st.session_state.rpt_log_queue.empty():
            try: st.session_state.rpt_logs.append(st.session_state.rpt_log_queue.get_nowait())
            except queue.Empty: break

    @st.cache_data
    def _load_org_data():
        _org_csv = SCRIPT_DIR / "District name and organization oid.csv"
        _lookup  = {}   # oid -> "Name (ST)"
        _options = []   # ["District Name (ST) — OID", ...]
        try:
            with open(_org_csv, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    oid    = row.get("ORGANIZATION OID", "").strip()
                    name   = row.get("DISTRICT NAME", "").strip()
                    domain = row.get("DISTRICT DOMAIN", "").strip()
                    state  = domain.rsplit(".", 1)[-1].upper() if "." in domain else ""
                    label  = f"{name} ({state})" if state else name
                    if oid and name:
                        _lookup[oid] = label
                        _options.append(f"{label} — {oid}")
        except Exception:
            pass
        return _lookup, sorted(_options)

    _ORG_LOOKUP, _ORG_OPTIONS = _load_org_data()

    # ── Flat form ─────────────────────────────────────────────────────────────
    _rpt_already_ran = bool(st.session_state.rpt_logs)
    _form_disabled   = st.session_state.rpt_running

    # Row 1: Google Account Email (full width)
    with st.container(border=True):
        section_label("Google Account Email")
        helper_text("Required — Google account used to sign in to Istation SSO. Saved once set.")
        _em_val = st.text_input("Email", value=st.session_state.rpt_email,
                                placeholder="you@amiralearning.com",
                                key="rpt_email_inp", label_visibility="collapsed",
                                disabled=_form_disabled)
        if _em_val != st.session_state.rpt_email:
            st.session_state.rpt_email = _em_val
            _save_prefs({"rpt_email": _em_val})

    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

    # Row 2: District (full width)
    with st.container(border=True):
        section_label("District")
        helper_text("Search by name or OID.")
        _saved_oid  = st.session_state.rpt_org_oid
        _saved_name = _ORG_LOOKUP.get(_saved_oid, "")
        _saved_opt  = f"{_saved_name} — {_saved_oid}" if _saved_name else None
        _dist_idx   = (_ORG_OPTIONS.index(_saved_opt) + 1) if _saved_opt and _saved_opt in _ORG_OPTIONS else 0
        _dcol1, _dcol2 = st.columns([10, 1])
        with _dcol1:
            _dist_sel = st.selectbox(
                "District", options=[""] + _ORG_OPTIONS,
                index=_dist_idx, key=f"rpt_dist_sel_{st.session_state.rpt_dist_key}",
                label_visibility="collapsed", disabled=_form_disabled,
            )
        with _dcol2:
            if st.button("✕", key="rpt_dist_clear", help="Clear selection",
                         disabled=_form_disabled or not _saved_oid):
                st.session_state.rpt_org_oid = ""
                st.session_state.rpt_dist_key += 1
                _save_prefs({"rpt_org_oid": ""})
                st.rerun()
        if _dist_sel:
            _sel_oid = _dist_sel.rsplit(" — ", 1)[-1].strip()
            if _sel_oid != st.session_state.rpt_org_oid:
                st.session_state.rpt_org_oid = _sel_oid
                _save_prefs({"rpt_org_oid": _sel_oid})

    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

    # Row 2: School Years (full width)
    with st.container(border=True):
        section_label("School Year(s)")
        _cur_yrs  = st.session_state.get("rpt_years", [st.session_state.rpt_year])
        _cur_lbls = [f"{y}-{str(y+1)[-2:]}" for y in _cur_yrs if y in _SY_OPTIONS]
        _sy_sel   = st.multiselect("School Year(s)", options=_SY_DISPLAY, default=_cur_lbls,
                                   key="rpt_sy_sel", label_visibility="collapsed",
                                   disabled=_form_disabled)
        _yr_vals  = [_SY_LABEL_TO_YR[l] for l in _sy_sel]
        if _yr_vals != st.session_state.get("rpt_years"):
            st.session_state.rpt_years = _yr_vals
            st.session_state.rpt_year  = _yr_vals[0] if _yr_vals else 2024
            _save_prefs({"rpt_years": _yr_vals})

    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

    # Row 2: Products + Report Types
    _fc3, _fc4 = st.columns([1, 2])
    with _fc3:
        with st.container(border=True):
            section_label("Products")
            _prod_vals = list(st.session_state.rpt_products)
            for _p in ["Reading", "Lectura", "Math"]:
                if st.checkbox(_p, value=_p in _prod_vals, key=f"rpt_p_{_p}", disabled=_form_disabled):
                    if _p not in _prod_vals: _prod_vals.append(_p)
                else:
                    if _p in _prod_vals: _prod_vals.remove(_p)
            st.session_state.rpt_products = _prod_vals
            _save_prefs({"rpt_products": _prod_vals})

    with _fc4:
        with st.container(border=True):
            section_label("Report Types")
            _rt_vals = list(st.session_state.rpt_report_types)
            _rt_cols = st.columns(len(_IST_REPORT_OPTIONS))
            for _i, (_key, _label) in enumerate(_IST_REPORT_OPTIONS):
                with _rt_cols[_i]:
                    if st.checkbox(_label, value=_key in _rt_vals, key=f"rpt_rt_{_key}",
                                   disabled=_form_disabled):
                        if _key not in _rt_vals: _rt_vals.append(_key)
                    else:
                        if _key in _rt_vals: _rt_vals.remove(_key)
            st.session_state.rpt_report_types = _rt_vals
            _save_prefs({"rpt_report_types": _rt_vals})

    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

    # Advanced options (collapsed by default)
    with st.expander("Advanced Options"):
        _adv1, _adv2, _adv3 = st.columns(3)
        with _adv1:
            section_label("Grade Filter")
            _gi   = _GRADE_OPTS.index(st.session_state.rpt_grade) if st.session_state.rpt_grade in _GRADE_OPTS else 0
            _gsel = st.selectbox("Grade", options=_GRADE_OPTS, index=_gi,
                                 key="rpt_grade_inp", label_visibility="collapsed")
            if _gsel != st.session_state.rpt_grade:
                st.session_state.rpt_grade = _gsel; _save_prefs({"rpt_grade": _gsel})

        with _adv2:
            section_label("Skill Filter")
            _sel_prods = st.session_state.rpt_products
            if len(_sel_prods) == 1:
                _skill_opts = list(_SKILLS[_sel_prods[0]].keys())
            elif _sel_prods:
                _sets = [set(_SKILLS[p].keys()) for p in _sel_prods if p in _SKILLS]
                _skill_opts = ["Overall"] + sorted(set.intersection(*_sets) - {"Overall"}) if _sets else ["Overall"]
            else:
                _skill_opts = ["Overall"]
            if st.session_state.rpt_skill not in _skill_opts:
                st.session_state.rpt_skill = "Overall"
            _si   = _skill_opts.index(st.session_state.rpt_skill)
            _ssel = st.selectbox("Skill", options=_skill_opts, index=_si,
                                 key="rpt_skill_inp", label_visibility="collapsed")
            if _ssel != st.session_state.rpt_skill:
                st.session_state.rpt_skill = _ssel; _save_prefs({"rpt_skill": _ssel})

        with _adv3:
            section_label("Assessment Mode")
            _am     = st.session_state.rpt_assess_mode
            _am_map = {"ytd": "Year to Date", "current": "Current Month", "per_month": "Pick Periods"}
            _am_sel = st.selectbox("Mode", options=list(_am_map.values()),
                                   index=list(_am_map.keys()).index(_am),
                                   key="rpt_am_sel", label_visibility="collapsed")
            _am_val = {v: k for k, v in _am_map.items()}[_am_sel]
            if _am_val != st.session_state.rpt_assess_mode:
                st.session_state.rpt_assess_mode = _am_val; _save_prefs({"rpt_assess_mode": _am_val})

        if st.session_state.rpt_assess_mode == "per_month":
            _cur_periods = [p for p in st.session_state.rpt_sel_months if 0 <= p < 12]
            _month_names = ["Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun","Jul"]
            _msel = st.multiselect("Periods", options=list(range(12)), default=_cur_periods,
                                   key="rpt_months_inp", format_func=lambda p: _month_names[p])
            st.session_state.rpt_sel_months = _msel

        section_label("Save Location")
        _bd_val = st.text_input("Save Location", value=st.session_state.rpt_base_dir,
                                key="rpt_base_dir_inp", label_visibility="collapsed")
        if _bd_val != st.session_state.rpt_base_dir:
            st.session_state.rpt_base_dir = _bd_val
            _save_prefs({"rpt_base_dir": _bd_val})

    st.divider()

    # ── Start / Running buttons ───────────────────────────────────────────────
    _can_run = (
        bool(st.session_state.rpt_email.strip())
        and bool(st.session_state.rpt_org_oid.strip())
        and bool(st.session_state.get("rpt_years"))
        and bool(st.session_state.rpt_products)
        and bool(st.session_state.rpt_report_types)
    )

    _bc1, _bc2, _bc3 = st.columns([2, 3, 2])
    with _bc2:
        if not st.session_state.rpt_running:
            _rb = st.columns([4, 1]) if _rpt_already_ran else [st.container(), None]
            with _rb[0]:
                _rlbl  = "Run Again" if _rpt_already_ran else "Start Download"
                _rstart = st.button(_rlbl, type="primary", key="rpt_start_btn",
                                    use_container_width=True, disabled=not _can_run)
            if _rpt_already_ran and _rb[1]:
                with _rb[1]:
                    if st.button("✕", key="rpt_clear_btn", help="Clear logs"):
                        st.session_state.rpt_logs = []
                        st.session_state.rpt_log_queue = queue.Queue()
                        st.rerun()
        else:
            _rb2 = st.columns([4, 1])
            with _rb2[0]:
                st.button("Running…", disabled=True, use_container_width=True, key="rpt_running_btn")
            with _rb2[1]:
                if st.button("✕", key="rpt_stop_btn", help="Force stop"):
                    st.session_state.rpt_running = False; st.rerun()
            _rstart = False

    # ── Launch thread ─────────────────────────────────────────────────────────
    if _rstart and not st.session_state.rpt_running:
        st.session_state.rpt_logs      = []
        st.session_state.rpt_log_queue = queue.Queue()
        st.session_state.rpt_running   = True
        _rq = st.session_state.rpt_log_queue

        def _launch_rpt(
            _oid=st.session_state.rpt_org_oid,
            _yrs=list(st.session_state.get("rpt_years", [st.session_state.rpt_year])),
            _prods=list(st.session_state.rpt_products),
            _rts=list(st.session_state.rpt_report_types),
            _am=st.session_state.rpt_assess_mode,
            _grade=st.session_state.rpt_grade,
            _skill=st.session_state.rpt_skill,
            _months=list(st.session_state.rpt_sel_months),
            _bd=st.session_state.rpt_base_dir,
            _email=st.session_state.rpt_email,
            _q=_rq,
        ):
            from selenium import webdriver as _wd
            import tempfile
            try:
                _tmp  = tempfile.mkdtemp(prefix="ist_rpt_")
                _opts = _wd.ChromeOptions()
                _opts.add_argument("--disable-blink-features=AutomationControlled")
                _opts.add_argument("--disable-gpu")
                _opts.add_argument("--no-sandbox")
                _opts.add_argument(f"--user-data-dir={_tmp}")
                _opts.add_experimental_option("excludeSwitches", ["enable-automation"])
                _driver = _wd.Chrome(options=_opts)
                try:
                    for _yr in _yrs:
                        _q.put(f"\n📅 {_yr}-{str(_yr+1)[-2:]}...")
                        _run_rpt(driver=_driver, org_oid=_oid, products=_prods,
                                 year=_yr, report_types=_rts, assessment_mode=_am,
                                 grade=_grade, skill=_skill, selected_months=_months,
                                 base_dir=_bd, email=_email, log_fn=lambda m: _q.put(m))
                finally:
                    try: _driver.quit()
                    except Exception: pass
            except Exception as exc:
                import traceback
                _q.put(f"❌ {exc}\n{traceback.format_exc()}")
            finally:
                st.session_state.rpt_running = False

        threading.Thread(target=_launch_rpt, daemon=True).start()
        st.rerun()

    # ── Log output ────────────────────────────────────────────────────────────
    if st.session_state.rpt_running or _rpt_already_ran:
        if st.session_state.rpt_running:
            st.info("Chrome is opening — complete the Google SSO prompt when the browser appears.")
        _rpt_drain()
        auto_scroll_log(st.session_state.rpt_logs, height=420)
        if st.session_state.rpt_running:
            time.sleep(1); st.rerun()

        if not st.session_state.rpt_running and _rpt_already_ran:
            log_text = "\n".join(st.session_state.rpt_logs)
            if "All reports complete" in log_text:
                st.success("All reports downloaded successfully.")
            elif "❌" in log_text:
                st.warning("Completed with errors — review the log above.")

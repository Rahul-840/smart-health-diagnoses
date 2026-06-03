import json
import os
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from analyzer import DISCLAIMER, build_rule_based_analysis, extract_pdf_text, merge_ai_with_rules, safe_json_loads
from chatbot import get_relevant_context, load_minilm_model, local_answer
from database import HealthDB

load_dotenv()
st.set_page_config(page_title="Smart Health Diagnoses", page_icon="🏥", layout="wide")

MODEL_NAME = "openai/gpt-oss-120b:free"
APP_VERSION = "FINAL-STABLE-v1"


def init_state() -> None:
    defaults = {
        "logged_in": False,
        "user": None,
        "page": "home",
        "show_auth": False,
        "rid": None,
        "rpt_txt": "",
        "analysis": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def get_secret(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)


@st.cache_resource
def get_db() -> HealthDB:
    return HealthDB()


@st.cache_resource
def get_client():
    key = get_secret("OPENROUTER_API_KEY", "")
    if not key:
        return None
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)


@st.cache_resource(show_spinner=False)
def get_embedder():
    return load_minilm_model()


db = get_db()
client = get_client()
embedder = get_embedder()


st.markdown(
    """
<style>
    .stApp {
        background: radial-gradient(circle at top left, rgba(56,189,248,.14), transparent 32%),
                    radial-gradient(circle at top right, rgba(139,92,246,.14), transparent 28%),
                    linear-gradient(180deg, #07111f 0%, #0f172a 60%, #020617 100%);
        color: #e5e7eb;
    }
    /* Keep Streamlit header visible so sidebar collapse/open button works.
       Add top padding so header does not cover dashboard/tabs. */
    .block-container { max-width: 1280px; padding-top: 4.2rem; padding-bottom: 2rem; }
    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] {
        background: rgba(7,17,31,0.85) !important;
        backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(148,163,184,.12);
    }
    section[data-testid="stSidebar"] { padding-top: 3.2rem; }
    .topbar {
        display:flex; align-items:center; justify-content:space-between; gap:1rem;
        padding: .8rem 1rem; margin-bottom: 1rem;
        border-radius: 20px; border:1px solid rgba(148,163,184,.18);
        background: rgba(2,6,23,.62); backdrop-filter: blur(14px);
        box-shadow: 0 18px 50px rgba(0,0,0,.24);
    }
    .brand { display:flex; align-items:center; gap:.75rem; }
    .brand-icon { width:44px; height:44px; display:flex; align-items:center; justify-content:center; border-radius:16px; background:linear-gradient(135deg,#0ea5e9,#7c3aed); font-size:1.35rem; }
    .brand-title { color:white; font-weight:900; font-size:1.05rem; line-height:1; }
    .brand-sub { color:#94a3b8; font-size:.78rem; margin-top:.2rem; }
    .hero {
        border-radius: 30px; padding: 2rem;
        border:1px solid rgba(148,163,184,.18);
        background: linear-gradient(135deg, rgba(14,165,233,.18), rgba(124,58,237,.15)), rgba(15,23,42,.82);
        box-shadow: 0 24px 70px rgba(0,0,0,.28);
        margin-bottom: 1rem;
    }
    .hero h1 { color:white; font-size:2.25rem; font-weight:950; margin:0 0 .45rem 0; letter-spacing:-.04em; }
    .hero p { color:#cbd5e1; margin:0; max-width:780px; line-height:1.55; }
    .pill-row { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1rem; }
    .pill { padding:.42rem .72rem; border-radius:999px; background:rgba(15,23,42,.64); border:1px solid rgba(148,163,184,.2); color:#dbeafe; font-size:.84rem; }
    .panel { border-radius:24px; padding:1.2rem; background:rgba(15,23,42,.78); border:1px solid rgba(148,163,184,.18); box-shadow:0 18px 50px rgba(0,0,0,.22); margin-bottom:1rem; }
    .card { border-radius:22px; padding:1rem; background:rgba(15,23,42,.72); border:1px solid rgba(148,163,184,.18); min-height: 125px; }
    .metric-card { border-radius:22px; padding:1.25rem; color:white; min-height:125px; box-shadow:0 16px 42px rgba(0,0,0,.2); }
    .m-blue { background:linear-gradient(135deg,#2563eb,#0ea5e9); }
    .m-green { background:linear-gradient(135deg,#059669,#22c55e); }
    .m-purple { background:linear-gradient(135deg,#6d28d9,#a855f7); }
    .metric-label { font-size:.9rem; opacity:.9; font-weight:700; }
    .metric-value { font-size:2rem; font-weight:950; margin:.45rem 0 .1rem 0; }
    .metric-caption { opacity:.78; font-size:.82rem; }
    .status-badge { display:inline-flex; align-items:center; gap:.35rem; padding:.28rem .65rem; border-radius:999px; font-weight:800; font-size:.78rem; }
    .normal { color:#bbf7d0; background:rgba(34,197,94,.16); border:1px solid rgba(34,197,94,.3); }
    .low { color:#fed7aa; background:rgba(245,158,11,.16); border:1px solid rgba(245,158,11,.35); }
    .high { color:#fecaca; background:rgba(239,68,68,.16); border:1px solid rgba(239,68,68,.35); }
    .small-muted { color:#94a3b8; font-size:.84rem; line-height:1.4; }
    .summary-box { border-radius:22px; padding:1.15rem; background:linear-gradient(135deg,rgba(14,165,233,.12),rgba(34,197,94,.08)); border:1px solid rgba(56,189,248,.22); margin-bottom:1rem; }
    .warning-box { border-radius:18px; padding:1rem; background:rgba(245,158,11,.12); border:1px solid rgba(245,158,11,.28); color:#fde68a; }
    .stButton>button { border-radius:12px !important; font-weight:800 !important; border:1px solid rgba(148,163,184,.25) !important; }
    div[data-testid="stDataFrame"] { border-radius:18px; overflow:hidden; }
</style>
""",
    unsafe_allow_html=True,
)


def topbar(show_login: bool = False) -> None:
    left, right = st.columns([4, 1])
    with left:
        st.markdown(
            """
            <div class="topbar">
                <div class="brand">
                    <div class="brand-icon">🏥</div>
                    <div><div class="brand-title">Smart Health Diagnoses</div><div class="brand-sub">Medical Report Analyzer</div></div>
                </div>
                <div class="small-muted">Clean report insights • Secure local history • Doctor-first guidance</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if show_login:
            st.write("")
            if st.button("Login / Register", use_container_width=True):
                st.session_state.show_auth = True
                st.rerun()


def hero(title: str, subtitle: str, pills: List[str] | None = None) -> None:
    pill_html = "".join(f'<span class="pill">{p}</span>' for p in (pills or []))
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p><div class="pill-row">{pill_html}</div></div>', unsafe_allow_html=True)


def metric_card(label: str, value: str, caption: str, css: str) -> None:
    st.markdown(
        f'<div class="metric-card {css}"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-caption">{caption}</div></div>',
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    s = (status or "Normal").lower()
    if s == "high":
        return '<span class="status-badge high">🔴 High</span>'
    if s == "low":
        return '<span class="status-badge low">🟠 Low</span>'
    return '<span class="status-badge normal">✅ Normal</span>'


def health_score(values: List[Dict[str, Any]]) -> int:
    if not values:
        return 70
    abnormal = sum(1 for v in values if str(v.get("status", "")).lower() != "normal")
    return max(45, min(100, round(100 - (abnormal / len(values)) * 45)))


def render_value_cards(values: List[Dict[str, Any]]) -> None:
    if not values:
        st.info("No common values were detected from this report.")
        return
    for i in range(0, len(values), 3):
        cols = st.columns(3)
        for col, val in zip(cols, values[i:i + 3]):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{val.get('test', 'Test')}**", unsafe_allow_html=False)
                    st.markdown(status_badge(str(val.get("status", "Normal"))), unsafe_allow_html=True)
                    st.markdown(f"### {val.get('value', 'N/A')}")
                    st.caption(f"Reference Range: {val.get('normal_range', 'N/A')}")
                    st.write(val.get("meaning", ""))
                    if str(val.get("status", "")).lower() != "normal":
                        st.warning(val.get("risk", "Needs attention."))


def clean_dataframe(values: List[Dict[str, Any]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=["Test", "Value", "Reference Range", "Status", "Meaning", "Risk"])
    df = pd.DataFrame(values)
    keep = ["test", "value", "normal_range", "status", "meaning", "risk"]
    df = df[[c for c in keep if c in df.columns]].copy()
    df.columns = ["Test", "Value", "Reference Range", "Status", "Meaning", "Risk"][: len(df.columns)]
    return df


def ai_report_analysis(report_text: str, rule_data: Dict[str, Any]) -> Dict[str, Any]:
    if client is None:
        return rule_data
    prompt = f"""
Analyze this medical report in simple English only. Return ONLY valid JSON. No markdown.
Do not prescribe medicine. Do not claim final diagnosis.

Schema:
{{
  "solution": "safe next steps",
  "diet": "general diet and lifestyle guidance",
  "recommendations": ["recommendation 1", "recommendation 2"]
}}

Extracted values from rule engine:
{json.dumps(rule_data.get('detected_values', []), ensure_ascii=False)}

Report text:
{report_text[:12000]}
"""
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.15,
            max_tokens=800,
        )
        ai_data = safe_json_loads(resp.choices[0].message.content)
        return merge_ai_with_rules(ai_data, rule_data)
    except Exception:
        return rule_data


def ai_chat_answer(question: str, report_text: str, analysis: Dict[str, Any], history: List[Any]) -> str:
    context = get_relevant_context(question, report_text, embedder=embedder, top_k=3)
    if client is None:
        return local_answer(question, analysis, context)
    previous = "\n".join([f"{r}: {c}" for r, c, _ in history[-6:]])
    prompt = f"""
Answer using only the uploaded report context and analysis. Use simple English.
If the answer is not in the report, say it is not available in the uploaded report.
Do not prescribe medicine.

Analysis:
{json.dumps(analysis, ensure_ascii=False)[:5000]}

Relevant report context:
{context[:5000]}

Recent chat:
{previous}

User question: {question}
"""
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=650,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return local_answer(question, analysis, context)


def home_page() -> None:
    topbar(show_login=True)
    if st.session_state.show_auth:
        auth_page()
        return
    hero(
        "Understand medical reports faster",
        "Upload a text-based lab report PDF, detect normal and abnormal values, view diet guidance, recommendations, history, tracking, and report-based chat support.",
        ["Medical PDF upload", "Health score", "Report chat", "History"],
    )
    a, b, c = st.columns(3)
    with a:
        with st.container(border=True):
            st.subheader("🧾 Report Analysis")
            st.write("Extracts common lab values and shows normal, low, and high status.")
    with b:
        with st.container(border=True):
            st.subheader("📊 Clean Dashboard")
            st.write("Shows summary, value cards, table, risks, diet, and recommendations.")
    with c:
        with st.container(border=True):
            st.subheader("💬 Report Chat")
            st.write("Ask questions based on the uploaded report and extracted values.")


def auth_page() -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Access Your Dashboard")
    tab_login, tab_register = st.tabs(["Login", "Register"])
    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            uid = st.text_input("Username or Email", key="login_user")
            pwd = st.text_input("Password", type="password", key="login_pass")
            if st.form_submit_button("Login", use_container_width=True):
                ok, res = db.login_user(uid, pwd)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user = res
                    st.session_state.page = "dashboard"
                    st.session_state.show_auth = False
                    st.rerun()
                st.error(res)
    with tab_register:
        with st.form("register_form", clear_on_submit=True):
            username = st.text_input("Username", key="reg_user")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_pass")
            confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            if st.form_submit_button("Create Account", use_container_width=True):
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = db.register_user(username, email, password)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    st.markdown('</div>', unsafe_allow_html=True)


def dashboard_page() -> None:
    user = st.session_state.user or {}
    uid = user.get("id")
    reports = db.get_user_reports(uid)
    logs = db.get_health_logs(uid)
    hero(f"Welcome, {user.get('username', 'User')}", "Choose an action and continue your health report analysis.", [])
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Total Reports", str(len(reports)), "Uploaded medical reports", "m-blue")
    with c2:
        metric_card("Health Logs", str(len(logs)), "Tracking entries saved", "m-green")
    with c3:
        metric_card("Assistant", "On" if client else "Local", "Report-based support", "m-purple")

    st.markdown("### Quick Actions")
    a, b, c = st.columns(3)
    with a:
        if st.button("Upload Report", use_container_width=True):
            st.session_state.page = "upload"
            st.rerun()
    with b:
        if st.button("Open Report Chat", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
    with c:
        if st.button("Report History", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()


def upload_page() -> None:
    hero("Upload Report", "Choose a text-based medical PDF and run analysis.", [])
    if client is None:
        st.info("Smart assistant is not connected. Local report analysis will still work.")
    with st.container(border=True):
        uploaded = st.file_uploader("Choose PDF", type=["pdf"])
        if uploaded:
            with st.spinner("Reading PDF..."):
                try:
                    text = extract_pdf_text(uploaded)
                except Exception as exc:
                    st.error(str(exc))
                    return
            st.success(f"PDF text extracted successfully. Characters detected: {len(text)}")
            with st.expander("Preview extracted text"):
                st.text_area("Extracted Text", text[:5000], height=220)
            if st.button("Analyze Report", type="primary", use_container_width=True):
                with st.spinner("Analyzing report..."):
                    rule_data = build_rule_based_analysis(text)
                    final = ai_report_analysis(text, rule_data)
                    rid = db.save_report(st.session_state.user["id"], uploaded.name, text, final)
                    st.session_state.rid = rid
                    st.session_state.rpt_txt = text
                    st.session_state.analysis = final
                    st.session_state.page = "result"
                st.rerun()


def result_page() -> None:
    text = st.session_state.rpt_txt or ""
    analysis = st.session_state.analysis
    if text:
        # Always refresh numeric extraction to avoid old saved/wrong values.
        fresh = build_rule_based_analysis(text)
        analysis = merge_ai_with_rules(analysis if isinstance(analysis, dict) else None, fresh)
        st.session_state.analysis = analysis
    if not analysis:
        st.warning("Please upload and analyze a report first.")
        return

    values = analysis.get("detected_values", []) or []
    abnormal = [v for v in values if str(v.get("status", "")).lower() != "normal"]
    score = health_score(values)

    hero("Analysis Result", "Review summary, detected values, risks, diet guidance, and recommendations.", [f"Health Score: {score}/100", f"Detected: {len(values)}", f"Needs Attention: {len(abnormal)}"])

    st.markdown(f'<div class="summary-box"><b>Summary</b><br>{analysis.get("summary", "N/A")}</div>', unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(["Value Cards", "Table", "Risks", "Diet", "Recommendations"])
    with t1:
        render_value_cards(values)
    with t2:
        st.dataframe(clean_dataframe(values), use_container_width=True, hide_index=True)
    with t3:
        if abnormal:
            st.markdown('<div class="warning-box">Some values need attention. Check the details below and consult a doctor.</div>', unsafe_allow_html=True)
        for risk in analysis.get("risk_factors", []):
            st.markdown(f"- {risk}")
    with t4:
        st.write(analysis.get("diet", "Diet guidance is not available."))
    with t5:
        st.write(analysis.get("solution", ""))
        for rec in analysis.get("recommendations", []):
            st.markdown(f"- {rec}")
    st.caption(analysis.get("disclaimer", DISCLAIMER))
    if st.button("Ask questions about this report", use_container_width=True):
        st.session_state.page = "chat"
        st.rerun()


def chat_page() -> None:
    hero("Report Chat", "Ask questions about the currently loaded report.", [])
    if not st.session_state.rid:
        st.warning("Please analyze a report or load one from history first.")
        return
    uid = st.session_state.user["id"]
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Clear Chat", use_container_width=True):
            db.clear_chat(uid, st.session_state.rid)
            st.rerun()
    with c2:
        if st.button("View Result", use_container_width=True):
            st.session_state.page = "result"
            st.rerun()
    chats = db.get_chat(uid, st.session_state.rid)
    for role, content, _ in chats:
        with st.chat_message(role):
            st.markdown(content)
    prompt = st.chat_input("Example: Is my platelet count normal?")
    if prompt:
        db.save_chat(uid, st.session_state.rid, "user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = ai_chat_answer(prompt, st.session_state.rpt_txt, st.session_state.analysis or {}, chats)
                st.markdown(answer)
        db.save_chat(uid, st.session_state.rid, "assistant", answer)
        st.rerun()


def history_page() -> None:
    hero("Report History", "Load or delete previous reports.", [])
    reports = db.get_user_reports(st.session_state.user["id"])
    if not reports:
        st.info("No reports yet.")
        return
    for report_id, filename, uploaded_at in reports:
        c1, c2, c3 = st.columns([4, 1, 1])
        c1.write(f"**{filename}**  \n{uploaded_at}")
        if c2.button("Load", key=f"load_{report_id}", use_container_width=True):
            row = db.get_report_data(report_id, st.session_state.user["id"])
            if row:
                st.session_state.rid = row[0]
                st.session_state.rpt_txt = row[3]
                st.session_state.analysis = json.loads(row[4])
                st.session_state.page = "result"
                st.rerun()
        if c3.button("Delete", key=f"delete_{report_id}", use_container_width=True):
            db.delete_report(report_id, st.session_state.user["id"])
            st.rerun()
        st.divider()


def tracking_page() -> None:
    hero("Health Tracking", "Record simple health readings and view trends.", [])
    uid = st.session_state.user["id"]
    with st.form("health_log_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        date = c1.date_input("Date")
        weight = c2.number_input("Weight (kg)", min_value=0.0, step=0.5)
        c3, c4 = st.columns(2)
        bp_sys = c3.number_input("BP Systolic", min_value=0, step=1)
        bp_dia = c4.number_input("BP Diastolic", min_value=0, step=1)
        c5, c6 = st.columns(2)
        sugar = c5.number_input("Sugar", min_value=0.0, step=1.0)
        hr = c6.number_input("Heart Rate", min_value=0, step=1)
        notes = st.text_area("Notes")
        if st.form_submit_button("Save Log", use_container_width=True):
            db.add_health_log(uid, str(date), weight, bp_sys, bp_dia, sugar, hr, notes)
            st.success("Saved")
            st.rerun()
    logs = db.get_health_logs(uid)
    if logs:
        df = pd.DataFrame(logs, columns=["Date", "Weight", "BP Sys", "BP Dia", "Sugar", "Heart Rate"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        try:
            df["Date"] = pd.to_datetime(df["Date"])
            st.line_chart(df.set_index("Date")[["Weight", "BP Sys", "BP Dia", "Sugar", "Heart Rate"]])
        except Exception:
            pass


def sidebar() -> None:
    # Stable sidebar navigation. Uses buttons instead of radio to avoid disabled/hanging state.
    with st.sidebar:
        st.markdown("### 🏥 Smart Health")
        user = st.session_state.get("user") or {}
        st.markdown(f"**User:** {user.get('username', 'User')}")
        st.caption(f"Version: {APP_VERSION}")
        st.markdown("---")

        if "page" not in st.session_state or not st.session_state.get("page"):
            st.session_state["page"] = "dashboard"

        menu_items = [
            ("🏠 Dashboard", "dashboard"),
            ("📄 Upload Report", "upload"),
            ("🧾 Analysis Result", "result"),
            ("💬 Report Chat", "chat"),
            ("📊 Health Tracking", "tracking"),
            ("📜 Report History", "history"),
        ]

        current_page = st.session_state.get("page", "dashboard")
        for label, page_key in menu_items:
            button_label = f"✅ {label}" if current_page == page_key else label
            if st.button(button_label, use_container_width=True, key=f"nav_{page_key}"):
                st.session_state["page"] = page_key
                st.rerun()

        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True, key="sidebar_logout_btn"):
            st.session_state.clear()
            init_state()
            st.rerun()


def main() -> None:
    init_state()

    if not st.session_state.get("logged_in", False):
        home_page()
        return

    sidebar()

    page = st.session_state.get("page", "dashboard")
    routes = {
        "dashboard": dashboard_page,
        "upload": upload_page,
        "result": result_page,
        "chat": chat_page,
        "tracking": tracking_page,
        "history": history_page,
    }

    page_func = routes.get(page)
    if page_func is None:
        st.session_state["page"] = "dashboard"
        st.rerun()

    page_func()


if __name__ == "__main__":
    main()

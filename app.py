import streamlit as st
import PyPDF2
import os
import json
import re
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from database import HealthDB

load_dotenv()
st.set_page_config(page_title="🏥 Smart Health Suite", layout="wide", page_icon="🏥")

SESSION_FILE = ".health_session.json"

def load_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_session(data):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

st.markdown("""
<style>
    .stApp { background: #0f172a !important; }
    .block-container { background: #1e293b; border-radius: 16px; padding: 2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
    .stButton>button { background: linear-gradient(90deg, #3b82f6, #8b5cf6); color: white !important; border: none; border-radius: 8px; font-weight: 600; padding: 0.6rem 1.5rem; transition: 0.2s; }
    .stButton>button:hover { opacity: 0.9; transform: translateY(-1px); }
    .metric-card { background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 1.5rem; border-radius: 12px; color: white; text-align: center; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea { background: #0f172a !important; color: white !important; border: 1px solid #334155 !important; }
    .stChatInputContainer textarea { background: #0f172a !important; color: white !important; border: 1px solid #334155 !important; border-radius: 12px !important; }
    h1, h2, h3, p, span, div, label { color: #f8fafc !important; }
    #MainMenu, footer { visibility: hidden; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { color: #94a3b8; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p[aria-selected="true"] { color: #38bdf8; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db():
    return HealthDB()

@st.cache_resource
def get_client():
    key = os.getenv("OPENROUTER_API_KEY")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key) if key else None

db = get_db()
client = get_client()

def extract_pdf(file):
    try:
        reader = PyPDF2.PdfReader(file)
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text()).strip()
    except Exception as e:
        st.error(f"❌ PDF Error: {e}")
        return None

def analyze_report(text):
    prompt = f"""Analyze this medical report. Return ONLY valid JSON. No markdown.
Schema:
{{
    "disease": "str",
    "solution": "str",
    "diet": "str",
    "summary": "str",
    "risk_factors": ["str"]
}}
Report:
{text}"""
    try:
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        raw = resp.choices[0].message.content
        clean = re.sub(r'^```json\s*|\s*```$', '', raw, flags=re.MULTILINE).strip()
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        return json.loads(match.group(0)) if match else json.loads(clean)
    except Exception as e:
        st.error(f"❌ AI Error: {e}")
        return None

def chat_ai(question, report_text, history):
    ctx = f"Report:\n{report_text}\n\nHistory:\n" + "\n".join(f"{r}: {c}" for r, c in history[-5:]) + f"\nUser: {question}\nAssistant:"
    try:
        resp = client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[{"role": "user", "content": ctx}],
            temperature=0.5
        )
        return resp.choices[0].message.content
    except:
        return "⚠️ AI Error. Please try again."

def auth_page():
    st.title("🏥 Smart Health Suite")
    t1, t2 = st.tabs(["🔑 Login", "📝 Register"])
    with t1:
        with st.form("login_form", clear_on_submit=False):
            uid = st.text_input("Username/Email", key="l_u")
            pwd = st.text_input("Password", type="password", key="l_p")
            submit_login = st.form_submit_button("Login", use_container_width=True)
            
            if submit_login:
                if uid and pwd:
                    ok, res = db.login_user(uid, pwd)
                    if ok:
                        session_data = {"user": res, "logged_in": True, "page": "dash"}
                        st.session_state.update(session_data)
                        save_session(session_data)
                        st.rerun()
                    else:
                        st.error(res)
                else:
                    st.warning("Please fill both fields!")
    with t2:
        with st.form("register_form", clear_on_submit=True):
            u = st.text_input("Username", key="ru")
            e = st.text_input("Email", key="re")
            p = st.text_input("Password", type="password", key="rp")
            cp = st.text_input("Confirm", type="password", key="rcp")
            submit_register = st.form_submit_button("Register", use_container_width=True)
            
            if submit_register:
                if all([u, e, p, cp]) and p == cp:
                    ok, msg = db.register_user(u, e, p)
                    # ---- IS MEIN BADLAV KIYA HAI ----
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                    # ---------------------------------
                else:
                    st.error("Fields empty or passwords mismatch!")

def dash_page():
    uid = st.session_state["user"]["id"]
    st.title("🏠 Dashboard")
    st.markdown(f"### 👋 Welcome, {st.session_state['user']['username']}!")
    
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="metric-card"><h3>📄 Reports</h3><h1>{len(db.get_user_reports(uid))}</h1></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card" style="background:linear-gradient(135deg,#10b981,#059669)"><h3>📊 Logs</h3><h1>{len(db.get_health_logs(uid))}</h1></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    ac1, ac2, ac3 = st.columns(3)
    if ac1.button("📄 Upload", use_container_width=True): 
        st.session_state["page"] = "up"
        st.rerun()
    if ac2.button("💬 Chat", use_container_width=True): 
        st.session_state["page"] = "chat"
        st.rerun()
    if ac3.button("📊 Track", use_container_width=True): 
        st.session_state["page"] = "trk"
        st.rerun()

def upload_page():
    st.title("📄 Upload & AI Analysis")
    f = st.file_uploader("PDF Report", type="pdf")
    if f:
        txt = extract_pdf(f)
        if txt and st.button("🔍 Analyze", type="primary"):
            with st.spinner("Analyzing..."):
                res = analyze_report(txt)
            if res:
                rid = db.save_report(st.session_state["user"]["id"], f.name, txt, res)
                st.session_state.update({"rid": rid, "rpt_txt": txt, "analysis": res})
                st.success("✅ Done!")
                st.rerun()
    if "analysis" in st.session_state:
        d = st.session_state["analysis"]
        st.info(f"🦠 **Disease:** {d.get('disease','N/A')}")
        st.success(f"💊 **Solution:** {d.get('solution','N/A')}")
        st.warning(f"🥗 **Diet:** {d.get('diet','N/A')}")
        st.info(f"📝 **Summary:** {d.get('summary','N/A')}")

def chat_page():
    st.title("💬 Chat Assistant")
    rid = st.session_state.get("rid")
    if not rid:
        st.warning("⚠️ Analyze a report first!")
        return
    uid = st.session_state["user"]["id"]
    if st.button("🗑️ Clear"): 
        db.clear_chat(uid, rid)
        st.rerun()
    chats = db.get_chat(uid, rid)
    for role, content, _ in chats:
        with st.chat_message(role): 
            st.markdown(content)
    if prompt := st.chat_input("Ask me anything..."):
        db.save_chat(uid, rid, "user", prompt)
        st.rerun()
    if chats and chats[-1][0] == "user":
        with st.spinner("🤖 Thinking..."):
            ans = chat_ai(chats[-1][1], st.session_state.get("rpt_txt",""), [(r,c) for r,c,_ in chats])
            st.markdown(ans)
        db.save_chat(uid, rid, "assistant", ans)
        st.rerun()

def history_page():
    st.title("📜 History")
    for r in db.get_user_reports(st.session_state["user"]["id"]):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.markdown(f"**{r[1]}** ({r[2]})")
        if c2.button("Load", key=f"ld_{r[0]}"):
            d = db.get_report_data(r[0], st.session_state["user"]["id"])
            if d:
                st.session_state.update({"rid": d[0], "rpt_txt": d[3], "analysis": json.loads(d[4]), "page": "chat"})
                st.rerun()
        if c3.button("🗑️", key=f"dl_{r[0]}"):
            db.delete_report(r[0], st.session_state["user"]["id"])
            st.rerun()

def track_page():
    st.title("📊 Tracking")
    uid = st.session_state["user"]["id"]
    with st.form("log", clear_on_submit=True):
        c1, c2 = st.columns(2)
        dt = c1.date_input("Date", key="ld")
        wt = c2.number_input("Weight", key="lwt")
        c3, c4 = st.columns(2)
        s = c3.number_input("BP Sys", key="lbs")
        d = c4.number_input("BP Dia", key="lbd")
        su = st.number_input("Sugar", key="lsu")
        hr = st.number_input("Heart Rate", value=0, key="lhr")
        if st.form_submit_button("💾 Save", use_container_width=True):
            db.add_health_log(uid, str(dt), wt, s, d, su, hr, "")
            st.success("✅ Health log saved!")
            st.rerun()
    logs = db.get_health_logs(uid)
    if logs:
        df = pd.DataFrame(logs, columns=["Date", "Wt", "Sys", "Dia", "Sug", "HR"])
        df["Date"] = pd.to_datetime(df["Date"])
        st.dataframe(df, use_container_width=True)
        st.line_chart(df.set_index("Date")[["Wt", "Sys", "Dia", "Sug", "HR"]])

def main():
    if "logged_in" not in st.session_state:
        saved = load_session()
        if saved.get("logged_in") and saved.get("user"):
            st.session_state.update(saved)
        else:
            auth_page()
            return
    if not client: 
        st.error("❌ API Key missing")
        st.stop()

    st.sidebar.title("🏥 Health Suite")
    st.sidebar.markdown(f"**👤 {st.session_state['user']['username']}**")
    st.sidebar.markdown("---")
    
    pages = {
        "🏠 Dashboard": "dash", 
        "📄 Upload": "up", 
        "💬 Chat": "chat", 
        "📊 Tracking": "trk", 
        "📜 History": "hist"
    }
    
    mapped_pages = {v: k for k, v in pages.items()}
    current_page_key = mapped_pages.get(st.session_state.get("page", "dash"), "🏠 Dashboard")
    
    page_list = list(pages.keys())
    default_index = page_list.index(current_page_key) if current_page_key in page_list else 0
    
    ch = st.sidebar.radio("Menu", page_list, index=default_index)
    if st.session_state.get("page") != pages[ch]:
        st.session_state["page"] = pages[ch]
        st.rerun()
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        clear_session()
        st.session_state.clear()
        st.rerun()

    p = st.session_state["page"]
    if p == "dash": 
        dash_page()
    elif p == "up": 
        upload_page()
    elif p == "chat": 
        chat_page()
    elif p == "trk": 
        track_page()
    elif p == "hist": 
        history_page()

if __name__ == "__main__":
    main()
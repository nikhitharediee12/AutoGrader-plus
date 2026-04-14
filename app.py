"""
AutoGrader+ v2 | Upgraded Streamlit UI
New: QP Upload • Feedback System • Results Page •
     Analytics Upgrade • Validation • Empty States • UX Polish
Existing pipeline untouched.
"""

import json
import time
from pathlib import Path
import streamlit as st
import pandas as pd
import uuid
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io

# ─── Page config ───
st.set_page_config(
    page_title="AutoGrader+",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# GLOBAL STYLES  (all existing + new additions)
# ─────────────────────────────────────────────

st.markdown("""
<style>
  :root {
    --bg-base:    #0d0f14;
    --bg-card:    #151820;
    --bg-hover:   #1c2030;
    --accent:     #4f8ef7;
    --accent-2:   #7c5cfc;
    --accent-3:   #00d4aa;
    --warn:       #f7934f;
    --danger:     #f75f5f;
    --success:    #4fd87e;
    --text-primary:   #e8eaf2;
    --text-secondary: #8b90a4;
    --border:     #252a3a;
    --font-mono:  'JetBrains Mono', 'Fira Code', monospace;
  }
  html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-base) !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', 'Inter', sans-serif;
  }
  [data-testid="stSidebar"] {
    background: #0b0d11 !important;
    border-right: 1px solid var(--border);
  }
  h1, h2, h3 { color: var(--text-primary) !important; letter-spacing: -0.02em; }
  h1 { font-size: 2rem; font-weight: 800; }
  h2 { font-size: 1.4rem; font-weight: 700; }
  h3 { font-size: 1.1rem; font-weight: 600; }
  [data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.25rem;
  }
  [data-testid="stMetricLabel"]  { color: var(--text-secondary) !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
  [data-testid="stMetricValue"]  { color: var(--text-primary)   !important; font-size: 1.8rem !important; font-weight: 800; }
  [data-testid="stMetricDelta"]  { font-size: 0.82rem !important; }
  .stButton > button {
    background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
    color: #fff !important; border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; padding: 0.5rem 1.4rem !important;
    transition: opacity .2s, transform .15s;
  }
  .stButton > button:hover { opacity: .88; transform: translateY(-1px); }
  .stTextInput > div > div > input,
  .stTextArea textarea, .stNumberInput input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important; border-radius: 8px !important;
  }
  .stSelectbox > div { background: var(--bg-card) !important; border-radius: 8px !important; }
  [data-testid="stFileUploadDropzone"] {
    background: var(--bg-card) !important;
    border: 2px dashed var(--accent) !important; border-radius: 12px !important;
  }
  .streamlit-expanderHeader {
    background: var(--bg-card) !important; border-radius: 8px !important;
    color: var(--text-primary) !important;
  }
  .stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--accent), var(--accent-2)) !important;
  }
  hr { border-color: var(--border) !important; }
  [data-testid="stDataFrame"] { background: var(--bg-card) !important; border-radius: 10px; }
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg-base); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

  /* ── Cards ── */
  .ag-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 14px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;
  }
  .ag-card-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-secondary); margin-bottom: .5rem; }
  .ag-card-value { font-size: 2.2rem; font-weight: 800; color: var(--text-primary); }

  /* ── Pipeline badges ── */
  .pipe-step { display: inline-block; padding: .25rem .75rem; border-radius: 20px;
    font-size: .82rem; font-weight: 600; font-family: var(--font-mono); margin: .2rem .25rem; }
  .pipe-pending  { background: #252a3a; color: #8b90a4; }
  .pipe-active   { background: rgba(79,142,247,.18); color: #4f8ef7; border: 1px solid #4f8ef7; }
  .pipe-done     { background: rgba(79,216,126,.14); color: #4fd87e; border: 1px solid #4fd87e; }
  .pipe-error    { background: rgba(247,95,95,.14);  color: #f75f5f; border: 1px solid #f75f5f; }

  /* ── Score classes ── */
  .score-hi { color: #4fd87e; font-weight: 800; }
  .score-md { color: #f7934f; font-weight: 800; }
  .score-lo { color: #f75f5f; font-weight: 800; }

  /* ── Sidebar logo ── */
  .sidebar-logo { text-align: center; padding: 1.5rem 0 1rem 0;
    border-bottom: 1px solid var(--border); margin-bottom: 1rem; }
  .sidebar-logo h2 { font-size: 1.3rem; margin: 0; }
  .sidebar-logo span { font-size: .75rem; color: var(--text-secondary); }

  /* ── Alert boxes ── */
  .ag-info    { background: rgba(79,142,247,.1);  border-left: 3px solid #4f8ef7; padding: .75rem 1rem; border-radius: 0 8px 8px 0; margin: .5rem 0; font-size: .9rem; }
  .ag-success { background: rgba(79,216,126,.1);  border-left: 3px solid #4fd87e; padding: .75rem 1rem; border-radius: 0 8px 8px 0; margin: .5rem 0; font-size: .9rem; }
  .ag-warn    { background: rgba(247,147,79,.1);  border-left: 3px solid #f7934f; padding: .75rem 1rem; border-radius: 0 8px 8px 0; margin: .5rem 0; font-size: .9rem; }
  .ag-danger  { background: rgba(247,95,95,.1);   border-left: 3px solid #f75f5f; padding: .75rem 1rem; border-radius: 0 8px 8px 0; margin: .5rem 0; font-size: .9rem; }

  /* ── NEW: Empty state ── */
  .ag-empty-state {
    text-align: center; padding: 4rem 2rem;
    border: 2px dashed var(--border); border-radius: 16px;
    background: var(--bg-card); margin: 2rem 0;
  }
  .ag-empty-icon { font-size: 3.5rem; display: block; margin-bottom: 1rem; }
  .ag-empty-title { font-size: 1.3rem; font-weight: 700; color: var(--text-primary); margin-bottom: .5rem; }
  .ag-empty-sub { font-size: .9rem; color: var(--text-secondary); }

  /* ── NEW: Performance badge ── */
  .perf-excellent { background: rgba(79,216,126,.15); color: #4fd87e; padding: .2rem .65rem; border-radius: 20px; font-size: .8rem; font-weight: 700; }
  .perf-good      { background: rgba(79,142,247,.15); color: #4f8ef7; padding: .2rem .65rem; border-radius: 20px; font-size: .8rem; font-weight: 700; }
  .perf-partial   { background: rgba(247,147,79,.15); color: #f7934f; padding: .2rem .65rem; border-radius: 20px; font-size: .8rem; font-weight: 700; }
  .perf-poor      { background: rgba(247,95,95,.15);  color: #f75f5f; padding: .2rem .65rem; border-radius: 20px; font-size: .8rem; font-weight: 700; }

  /* ── NEW: grade circle ── */
  .grade-circle {
    display: inline-block; width: 60px; height: 60px; line-height: 60px;
    border-radius: 50%; text-align: center; font-size: 1.4rem; font-weight: 900;
    border: 3px solid currentColor;
  }

  /* ── NEW: keyword chip ── */
  .kw-chip { display: inline-block; padding: .15rem .55rem; border-radius: 12px; font-size: .78rem;
             margin: .1rem; font-family: var(--font-mono); }
  .kw-matched { background: rgba(79,216,126,.12); color: #4fd87e; border: 1px solid rgba(79,216,126,.3); }
  .kw-missing { background: rgba(247,95,95,.12);  color: #f75f5f; border: 1px solid rgba(247,95,95,.3); }

  /* ── NEW: file preview card ── */
  .file-preview-card {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
    padding: .75rem 1rem; margin-bottom: .5rem; display: flex; align-items: center; gap: .75rem;
  }
  .file-icon { font-size: 1.5rem; }
  .file-name { font-weight: 600; font-size: .9rem; color: var(--text-primary); }
  .file-meta { font-size: .78rem; color: var(--text-secondary); }

  /* ── NEW: comparison table row colors ── */
  .val-over  { color: #f7934f; }
  .val-under { color: #4f8ef7; }
  .val-match { color: #4fd87e; }

  /* ── Tab styling ── */
  .stTabs [data-baseweb="tab-list"] { background: var(--bg-card) !important; border-radius: 10px; padding: .25rem; }
  .stTabs [data-baseweb="tab"] { color: var(--text-secondary) !important; border-radius: 8px !important; }
  .stTabs [aria-selected="true"] { background: var(--bg-hover) !important; color: var(--text-primary) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
      <h2>🎓 AutoGrader<span style="color:#4f8ef7">+</span></h2>
      <span>AI-Powered Evaluation Platform</span>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        options=[
            "🏠  Dashboard",
            "📄  Question Paper",
            "📤  Upload & Grade",
            "📋  Results",
            "📊  Analytics",
            "✅  Validation",
            "📁  Past Sessions",
            "⚙️  Settings",
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Session indicator
    sid = st.session_state.get("session_id")
    if sid:
        st.markdown(f"""
        <div style="font-size:.78rem; color:#555; padding: .5rem 0;">
          <b style="color:#4fd87e">● Active Session</b><br>
          <code style="font-size:.72rem">{sid[-20:]}</code>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="font-size:.78rem; color:#555; padding: .5rem 0;">
          <b style="color:#8b90a4">● No active session</b><br>
          Start in Upload &amp; Grade
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:.78rem; color:#444; padding: .5rem 0; margin-top:.5rem;">
      <b style="color:#8b90a4">Pipeline</b><br>
      QP → OCR → VLM → Score → Feedback
      <br><br>
      <b style="color:#8b90a4">Storage</b><br>
      Local files • CSV + JSON<br>
      No database • No cloud
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

def init_state():
    defaults = {
        "session_id":       None,
        "results":          [],
        "student_reports":  {},        # NEW: {student_id: StudentReport}
        "question_paper":   None,      # NEW: QuestionPaper object
        "model_answers":    {},
        "question_texts":   {},        # NEW: {q_id: q_text}
        "marks_map":        {},        # NEW: {q_id: max_marks}
        "grading_config": {
            "max_marks": 10.0,
            "vlm_mode": "auto",
            "force_handwriting": False,
        },
        "pipeline_log":     [],
        "current_step":     0,
        "validation_report": None,     # NEW
        "uploaded_file_previews": [],  # NEW
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─────────────────────────────────────────────
# SHARED HELPERS  (all existing helpers preserved)
# ─────────────────────────────────────────────

def score_color_class(score: float) -> str:
    if score >= 70: return "score-hi"
    if score >= 40: return "score-md"
    return "score-lo"

def perf_badge(tag: str) -> str:
    labels = {"excellent": "Excellent", "good": "Good",
              "partial": "Partial", "poor": "Needs Work"}
    return f'<span class="perf-{tag}">{labels.get(tag, tag)}</span>'

def grade_color(g: str) -> str:
    if g in ("A+", "A"): return "#4fd87e"
    if g == "B":          return "#00d4aa"
    if g == "C":          return "#4f8ef7"
    if g == "D":          return "#f7934f"
    return "#f75f5f"

def _plotly_layout(fig, title=""):
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#151820",
        font=dict(color="#e8eaf2", family="DM Sans, sans-serif"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(gridcolor="#252a3a", zerolinecolor="#252a3a")
    fig.update_yaxes(gridcolor="#252a3a", zerolinecolor="#252a3a")
    return fig

PIPELINE_STEPS = ["Upload", "Parse/QP", "OCR", "VLM", "Evaluate", "Feedback", "Report"]

def render_pipeline(current: int, error_step: int = -1):
    html = "<div style='margin:1rem 0; flex-wrap:wrap; display:flex; align-items:center; gap:.2rem'>"
    for i, step in enumerate(PIPELINE_STEPS):
        if i < current:
            cls = "pipe-done"; icon = "✓"
        elif i == current:
            cls = "pipe-active"; icon = "⟳"
        elif i == error_step:
            cls = "pipe-error"; icon = "✗"
        else:
            cls = "pipe-pending"; icon = str(i + 1)
        html += f'<span class="pipe-step {cls}">{icon} {step}</span>'
        if i < len(PIPELINE_STEPS) - 1:
            html += '<span style="color:#2a2e3f">→</span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def empty_state(icon: str, title: str, subtitle: str, cta: str = ""):
    cta_html = f'<div style="margin-top:1rem; font-size:.85rem; color:var(--accent)">{cta}</div>' if cta else ""
    st.markdown(f"""
    <div class="ag-empty-state">
      <span class="ag-empty-icon">{icon}</span>
      <div class="ag-empty-title">{title}</div>
      <div class="ag-empty-sub">{subtitle}</div>
      {cta_html}
    </div>
    """, unsafe_allow_html=True)

def render_score_gauge(score: float, height: int = 200):
    color = "#4fd87e" if score >= 70 else "#f7934f" if score >= 40 else "#f75f5f"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"color": color, "size": 32}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#555"},
            "bar":  {"color": color},
            "bgcolor": "#151820",
            "steps": [
                {"range": [0, 40],   "color": "#1a1020"},
                {"range": [40, 70],  "color": "#1a1818"},
                {"range": [70, 100], "color": "#0f1a12"},
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e8eaf2"},
        height=height, margin=dict(l=20, r=20, t=20, b=10)
    )
    st.plotly_chart(fig, use_container_width=True, key=str(uuid.uuid4()))


# ─────────────────────────────────────────────
# PAGE: DASHBOARD  (enhanced with empty states)
# ─────────────────────────────────────────────

def page_dashboard():
    st.markdown("## 🏠 Dashboard")

    try:
        from storage import ResultRetriever, AnalyticsEngine, SessionManager
        retriever = ResultRetriever()
        analytics = AnalyticsEngine()
        sessions  = SessionManager()
        all_df    = retriever.load_all_scores()
        stats     = analytics.compute(all_df) if not all_df.empty else {}
        sess_list = sessions.list_sessions()
    except Exception:
        all_df, stats, sess_list = pd.DataFrame(), {}, []

    # ── KPI row ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sessions",  len(sess_list))
    c2.metric("Total Students",  stats.get("total_students", 0))
    c3.metric("Class Average",   f"{stats.get('class_average', 0):.1f}%")
    c4.metric("Pass Rate",       f"{stats.get('pass_rate', 0):.1f}%")

    st.markdown("---")

    if all_df.empty:
        empty_state(
            "🎓", "No grading data yet",
            "Start your first grading session to see insights here.",
            "→ Go to 'Upload & Grade' to begin"
        )
        return

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown("### Score Distribution")
        dist = stats.get("score_distribution", {})
        if dist:
            fig = px.bar(
                x=list(dist.keys()), y=list(dist.values()),
                labels={"x": "Score Range", "y": "Students"},
                color=list(dist.values()),
                color_continuous_scale=["#f75f5f", "#4f8ef7", "#4fd87e"],
            )
            _plotly_layout(fig)
            st.plotly_chart(fig, use_container_width=True, key=str(uuid.uuid4()))

    with col_r:
        st.markdown("### ⚠ Weak Questions")
        weak = stats.get("weak_questions", [])
        if weak:
            for q in weak:
                cls = score_color_class(q["avg_score"])
                st.markdown(
                    f'<div class="ag-card"><div class="ag-card-title">Question {q["question"]}</div>'
                    f'<span class="{cls}">{q["avg_score"]:.1f}%</span> avg</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="ag-success">No weak questions detected ✓</div>', unsafe_allow_html=True)

    tops = stats.get("top_students", [])
    if tops:
        st.markdown("### 🏆 Top Performers")
        fig2 = px.bar(
            x=[t["student"] for t in tops],
            y=[t["avg_score"] for t in tops],
            color=[t["avg_score"] for t in tops],
            color_continuous_scale=["#f75f5f", "#f7934f", "#4fd87e"],
            labels={"x": "Student", "y": "Average Score (%)"},
        )
        _plotly_layout(fig2)
        st.plotly_chart(fig2, use_container_width=True, key=str(uuid.uuid4()))

    # Recent sessions
    if sess_list:
        st.markdown("### 🕐 Recent Sessions")
        for sess in list(reversed(sess_list))[:3]:
            status_color = "#4fd87e" if sess.get("status") == "completed" else "#f7934f"
            st.markdown(
                f'<div class="ag-card">'
                f'<span style="color:{status_color}">●</span> '
                f'<b>{sess.get("name","?")}</b> &nbsp;'
                f'<small style="color:#555">{sess.get("created_at","")[:10]}</small>'
                f'</div>',
                unsafe_allow_html=True
            )


# ─────────────────────────────────────────────
# PAGE: QUESTION PAPER  (NEW — Feature 13)
# ─────────────────────────────────────────────

def page_question_paper():
    st.markdown("## 📄 Question Paper & Answer Key")
    st.markdown('<div class="ag-info">Upload a question paper to auto-extract questions and marks, or enter them manually. Then provide model answers per question.</div>', unsafe_allow_html=True)

    tab_upload, tab_manual = st.tabs(["📁 Upload QP File", "✍️ Manual Entry"])

    # ── Tab 1: Upload ──
    with tab_upload:
        st.markdown("### Upload Question Paper")
        qp_file = st.file_uploader(
            "Question Paper (PDF or image)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="qp_uploader",
            label_visibility="collapsed"
        )
        ak_file = st.file_uploader(
            "Answer Key (optional PDF/TXT)",
            type=["pdf", "txt"],
            key="ak_uploader",
            label_visibility="visible"
        )

        if qp_file:
            st.markdown(f'<div class="file-preview-card"><span class="file-icon">📄</span><div><div class="file-name">{qp_file.name}</div><div class="file-meta">{qp_file.size // 1024} KB • {qp_file.type}</div></div></div>', unsafe_allow_html=True)

            if st.button("🔍 Extract Questions from QP"):
                with st.spinner("Extracting questions and marks..."):
                    try:
                        from qp_parser import QPBuilder, AnswerKeyParser
                        builder = QPBuilder()

                        # Parse answer key if provided
                        manual_answers = {}
                        if ak_file:
                            ak_bytes = ak_file.read()
                            if ak_file.type == "text/plain":
                                ak_text = ak_bytes.decode("utf-8", errors="ignore")
                            else:
                                from qp_parser import QPTextExtractor
                                ak_text = QPTextExtractor().extract(ak_bytes, ak_file.type)
                            manual_answers = AnswerKeyParser().parse(ak_text)
                            st.markdown(f'<div class="ag-success">Answer key parsed: {len(manual_answers)} answers found</div>', unsafe_allow_html=True)

                        qp = builder.build_from_file(
                            file_bytes     =qp_file.read(),
                            mime_type      =qp_file.type,
                            title          =Path(qp_file.name).stem,
                            manual_answers =manual_answers,
                        )

                        st.session_state.question_paper = qp
                        st.session_state.question_texts = {q.q_id: q.text for q in qp.questions}
                        st.session_state.marks_map      = {q.q_id: q.marks for q in qp.questions}
                        st.session_state.model_answers  = {q.q_id: q.model_answer for q in qp.questions}

                        st.markdown(f'<div class="ag-success">✓ Extracted {len(qp.questions)} questions · Total marks: {qp.total_marks}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Extraction error: {e}")

        # Show / edit extracted questions
        qp = st.session_state.get("question_paper")
        if qp:
            _render_qp_editor(qp)

    # ── Tab 2: Manual ──
    with tab_manual:
        st.markdown("### Manual Question Entry")
        col1, col2 = st.columns(2)
        with col1:
            exam_title = st.text_input("Exam Title", "Mid-Term Exam", key="manual_title")
        with col2:
            n_q = st.number_input("Number of Questions", 1, 20, 3, key="manual_nq")

        questions_data = {}
        for i in range(1, int(n_q) + 1):
            q_id = f"Q{i}"
            with st.expander(f"Question {i}", expanded=(i <= 3)):
                c1, c2 = st.columns([3, 1])
                with c1:
                    q_text = st.text_input(f"Question text", key=f"mq_text_{q_id}",
                                           placeholder="Enter the question...")
                with c2:
                    marks = st.number_input("Marks", 1.0, 100.0, 10.0, key=f"mq_marks_{q_id}")

                model_ans = st.text_area("Model Answer", key=f"mq_ans_{q_id}", height=100,
                                         placeholder="Expected answer...")
                kw_raw = st.text_input("Keywords (comma-separated)", key=f"mq_kw_{q_id}",
                                       placeholder="keyword1, keyword2, ...")
                keywords = [k.strip() for k in kw_raw.split(",") if k.strip()]

                questions_data[q_id] = {
                    "text": q_text, "marks": marks,
                    "model_answer": model_ans, "keywords": keywords
                }

        if st.button("💾 Save Question Paper", key="save_manual_qp"):
            try:
                from qp_parser import QPBuilder
                builder = QPBuilder()
                qp = builder.build_from_manual(
                    n_questions=int(n_q),
                    title      =exam_title,
                    answers    ={q: d["model_answer"] for q, d in questions_data.items()},
                    marks      ={q: d["marks"] for q, d in questions_data.items()},
                    keywords   ={q: d["keywords"] for q, d in questions_data.items()},
                )
                # Patch question texts
                for q in qp.questions:
                    d = questions_data.get(q.q_id, {})
                    q.text = d.get("text", q.text)

                st.session_state.question_paper  = qp
                st.session_state.question_texts  = {q.q_id: q.text for q in qp.questions}
                st.session_state.marks_map       = {q.q_id: q.marks for q in qp.questions}
                st.session_state.model_answers   = {q.q_id: q.model_answer for q in qp.questions}

                st.markdown(f'<div class="ag-success">✓ Question paper saved: {len(qp.questions)} questions, {qp.total_marks} total marks</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Save error: {e}")


def _render_qp_editor(qp):
    """Render extracted QP with editable model answers."""
    st.markdown("---")
    st.markdown(f"### 📝 {qp.title} — {len(qp.questions)} Questions · {qp.total_marks} Marks")

    for q in qp.questions:
        with st.expander(f"{q.q_id} · {q.marks} marks", expanded=False):
            st.markdown(f'<div class="ag-info">{q.text}</div>', unsafe_allow_html=True)
            col1, col2 = st.columns([3, 1])
            with col1:
                new_ans = st.text_area(
                    "Model Answer", value=q.model_answer,
                    key=f"qpe_ans_{q.q_id}", height=100
                )
                q.model_answer = new_ans
                st.session_state.model_answers[q.q_id] = new_ans
            with col2:
                new_marks = st.number_input(
                    "Marks", value=float(q.marks), min_value=0.0, max_value=100.0,
                    key=f"qpe_marks_{q.q_id}"
                )
                q.marks = new_marks
                st.session_state.marks_map[q.q_id] = new_marks

                kw_val = ", ".join(q.keywords) if q.keywords else ""
                new_kw = st.text_input("Keywords", value=kw_val, key=f"qpe_kw_{q.q_id}")
                q.keywords = [k.strip() for k in new_kw.split(",") if k.strip()]


# ─────────────────────────────────────────────
# PAGE: UPLOAD & GRADE  (enhanced UX — Features 17, 18)
# ─────────────────────────────────────────────

def page_upload_grade():
    st.markdown("## 📤 Upload & Grade")

    # QP status check
    qp = st.session_state.get("question_paper")
    if qp:
        st.markdown(f'<div class="ag-success">✓ Question paper loaded: <b>{qp.title}</b> — {len(qp.questions)} questions · {qp.total_marks} marks</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ag-warn">⚠ No question paper loaded. You can upload one in <b>Question Paper</b> page, or configure manually below.</div>', unsafe_allow_html=True)

    # ── Session config ──
    with st.expander("⚙ Session Configuration", expanded=not bool(qp)):
        col1, col2 = st.columns(2)
        with col1:
            session_name = st.text_input("Session Name", placeholder="e.g., Physics Mid-Term 2024")
            if not qp:
                n_questions = st.number_input("Number of Questions", 1, 20, 3)
            else:
                n_questions = len(qp.questions)
                st.info(f"Using QP: {n_questions} questions")
        with col2:
            if not qp:
                max_marks = st.number_input("Default Marks Per Question", 1.0, 100.0, 10.0)
            else:
                max_marks = qp.total_marks / len(qp.questions) if qp.questions else 10.0
                st.info(f"Marks per Q from QP")
            vlm_mode   = st.selectbox("VLM Mode", ["auto", "always", "never", "diagrams_only"])
            force_hw   = st.checkbox("Force Handwriting Mode")

        st.session_state.grading_config = {
            "max_marks": max_marks, "vlm_mode": vlm_mode,
            "force_handwriting": force_hw,
        }

    st.markdown("---")

    # ── Model answers (only if no QP loaded) ──
    if not qp:
        st.markdown("### 📝 Model Answers")
        for q in range(1, int(n_questions) + 1):
            key = f"Q{q}"
            with st.expander(f"Question {q} — Model Answer", expanded=(q == 1)):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.session_state.model_answers[key] = st.text_area(
                        f"Model answer for Q{q}", key=f"model_{key}",
                        height=110, placeholder="Paste the expected answer here..."
                    )
                with col_b:
                    st.markdown("**Marks**")
                    marks_val = st.number_input("", 1.0, 100.0, 10.0, key=f"mk_{key}")
                    st.session_state.marks_map[key] = marks_val
                    st.markdown("**Keywords** (optional)")
                    st.text_area("One per line", key=f"kw_{key}", height=70)
        st.markdown("---")

    # ── ENHANCED File Upload (Feature 17) ──
    st.markdown("### 📁 Student Answer Sheets")
    st.markdown('<div class="ag-info">Naming tip: <code>StudentName_Q1.pdf</code> maps automatically. Multiple files accepted.</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Drag & drop answer sheets here",
        type=["pdf", "png", "jpg", "jpeg", "tiff"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="main_uploader"
    )

    # Feature 17: Rich file preview
    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)} file(s) ready**")

        # Upload progress simulation
        prog_placeholder = st.empty()
        for i, uf in enumerate(uploaded_files):
            prog_placeholder.progress(int((i + 1) / len(uploaded_files) * 100),
                                      text=f"Loading {uf.name}...")
            time.sleep(0.05)
        prog_placeholder.empty()
        st.markdown('<div class="ag-success">✓ All files loaded and ready</div>', unsafe_allow_html=True)

        # File preview grid
        st.markdown("#### Uploaded Files")
        for uf in uploaded_files:
            size_kb = uf.size // 1024
            ext     = Path(uf.name).suffix.upper().lstrip(".")
            icon    = "🖼️" if uf.type.startswith("image") else "📄"
            st.markdown(
                f'<div class="file-preview-card">'
                f'<span class="file-icon">{icon}</span>'
                f'<div style="flex:1">'
                f'<div class="file-name">{uf.name}</div>'
                f'<div class="file-meta">{ext} · {size_kb} KB</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

        # Image previews (first 3)
        image_files = [f for f in uploaded_files if f.type.startswith("image")]
        if image_files:
            with st.expander("🖼️ Image Previews", expanded=False):
                cols = st.columns(min(len(image_files[:3]), 3))
                for i, uf in enumerate(image_files[:3]):
                    with cols[i]:
                        uf.seek(0)
                        st.image(uf.read(), caption=uf.name, use_container_width=True)
                        uf.seek(0)

    st.markdown("---")

    # ── Validation marks upload (Feature 20 - optional here) ──
    with st.expander("✅ Optional: Upload Teacher Marks for Validation", expanded=False):
        st.markdown('<div class="ag-info">Upload a CSV with columns: <code>student_id, question_id, marks</code> to compare AI vs teacher scores after grading.</div>', unsafe_allow_html=True)
        teacher_csv = st.file_uploader("Teacher Marks CSV", type=["csv"], key="teacher_marks_uploader")
        if teacher_csv:
            st.session_state["teacher_marks_bytes"] = teacher_csv.read()
            st.markdown('<div class="ag-success">✓ Teacher marks loaded</div>', unsafe_allow_html=True)

    # ── Grade button ──
    col_btn, col_hint = st.columns([1, 3])
    with col_btn:
        start_grade = st.button("🚀 Start Grading", use_container_width=True)
    with col_hint:
        if not uploaded_files:
            st.markdown('<div class="ag-warn" style="margin-top:.5rem">Upload files first</div>', unsafe_allow_html=True)

    if start_grade:
        if not uploaded_files:
            st.error("Please upload at least one student answer sheet.")
            return
        has_answers = qp or any(
            st.session_state.model_answers.get(f"Q{q}", "").strip()
            for q in range(1, int(n_questions) + 1)
        )
        if not has_answers:
            st.error("Please enter at least one model answer or upload a question paper.")
            return

        _run_grading_pipeline(
            uploaded_files=uploaded_files,
            session_name  =session_name or "Unnamed Session",
        )


def _run_grading_pipeline(uploaded_files, session_name):
    """Enhanced pipeline with Features 18 (visual progress) + 14 (feedback)."""

    st.markdown("---")
    st.markdown("### ⚡ Live Grading Pipeline")

    pipeline_ph  = st.empty()
    log_ph       = st.empty()
    progress_bar = st.progress(0)
    status_text  = st.empty()

    logs = []

    def log(msg: str, level="info"):
        icon = {"info": "ℹ", "ok": "✓", "warn": "⚠", "error": "✗"}.get(level, "·")
        ts = time.strftime("%H:%M:%S")
        logs.append(f"[{ts}] {icon} {msg}")
        log_ph.code("\n".join(logs[-18:]), language=None)

    def upd_pipe(step: int):
        with pipeline_ph.container():
            render_pipeline(step)

    # Step 0 – Init
    upd_pipe(0); log("Initializing session..."); progress_bar.progress(5)

    try:
        from storage import SessionManager, FileSaver
        sid = SessionManager().create_session(session_name)
        st.session_state.session_id = sid
        file_saver = FileSaver()
        log(f"Session: {sid}", "ok")
    except Exception as e:
        log(f"Storage init failed: {e}", "error"); st.error(str(e)); return

    # Step 1 – Parse / QP mapping
    upd_pipe(1); log("Mapping files to questions..."); progress_bar.progress(12)

    try:
        from qp_parser import StudentFileMapper
        mapper = StudentFileMapper()
        file_infos = mapper.map([uf.name for uf in uploaded_files])
        log(f"Mapped {len(file_infos)} files", "ok")
    except Exception as e:
        log(f"File mapping warning: {e}", "warn")
        file_infos = [{"filename": uf.name, "student_id": Path(uf.name).stem,
                       "question_id": "Q1", "confidence": "low"}
                      for uf in uploaded_files]

    # Build lookup
    file_lookup = {fi["filename"]: fi for fi in file_infos}
    marks_map   = st.session_state.marks_map
    cfg         = st.session_state.grading_config

    # Save uploads
    for uf, fi in zip(uploaded_files, file_infos):
        uf.seek(0)
        file_saver.save_upload(sid, uf.read(), uf.name,
                               fi["student_id"], fi["question_id"])
        uf.seek(0)

    progress_bar.progress(20)

    # Step 2 – OCR
    upd_pipe(2); log("Starting OCR processing...")

    try:
        from evaluation_engine import BatchGrader
        grader = BatchGrader()
    except Exception as e:
        log(f"Grader init warning: {e}", "warn"); grader = None

    results = []
    total   = len(uploaded_files)

    for idx, (uf, fi) in enumerate(zip(uploaded_files, file_infos)):
        student_id  = fi["student_id"]
        question_id = fi["question_id"]
        model_answer = st.session_state.model_answers.get(question_id, "")
        max_marks    = marks_map.get(question_id, cfg["max_marks"])

        kw_key  = f"kw_{question_id}"
        kw_raw  = st.session_state.get(kw_key, "")
        keywords = ([k.strip() for k in kw_raw.split("\n") if k.strip()]
                    if isinstance(kw_raw, str) and kw_raw else None)

        # Fallback to QP keywords
        qp = st.session_state.get("question_paper")
        if not keywords and qp:
            q_entry = qp.get(question_id)
            if q_entry and q_entry.keywords:
                keywords = q_entry.keywords

        status_text.text(f"[{idx+1}/{total}] OCR: {student_id} — {question_id}")
        upd_pipe(2)

        try:
            uf.seek(0)
            if uf.type.startswith("image"):
                img_source = Image.open(io.BytesIO(uf.read()))
            else:
                img_source = _pdf_to_pil(uf.read())
            uf.seek(0)

            # Step 3 – VLM
            upd_pipe(3)
            if grader:
                if uf.type == "application/pdf":
                    from full_sheet_grader import FullSheetGrader

                    grader_full = FullSheetGrader()

                    uf.seek(0)
                    full_text = grader.ocr.extract_full_text(uf.read())
                    uf.seek(0)

                    full_results = grader_full.grade(
                        full_text=full_text,
                        student_id=student_id,
                        model_answers=st.session_state.model_answers,
                        max_marks_map=st.session_state.marks_map
                    )

                    results.extend(full_results)

                else:
                    if model_answer:
                    # ✅ Old logic (unchanged)
                        result = grader.grade_image(
                            image_source      =img_source,
                            student_id        =student_id,
                            question_id       =question_id,
                            model_answer      =model_answer,
                            max_marks         =float(max_marks),
                            keywords          =keywords,
                            force_handwriting =cfg["force_handwriting"],
                        )
                        results.append(result)
                upd_pipe(4)
                log(f"{student_id} processed", "ok")
            else:
                log(f"Skipped {student_id} {question_id} — no model answer", "warn")

        except Exception as e:
            log(f"Error on {student_id} {question_id}: {e}", "error")

        progress_bar.progress(int(20 + (idx / total) * 50))

    # Step 4 – Evaluate complete; Step 5 – Feedback (Feature 14)
    upd_pipe(5); log("Generating student feedback reports...")
    progress_bar.progress(75)

    question_texts = st.session_state.get("question_texts", {})
    model_answers  = st.session_state.model_answers

    student_reports = {}
    if results:
        try:
            from feedback_engine import BatchFeedbackGenerator
            fbg = BatchFeedbackGenerator()
            student_reports = fbg.generate_all(results, question_texts, model_answers)
            log(f"Feedback generated for {len(student_reports)} students", "ok")
        except Exception as e:
            log(f"Feedback generation warning: {e}", "warn")

    st.session_state.student_reports = student_reports

    # Step 6 – Save
    upd_pipe(6); log("Saving results..."); progress_bar.progress(88)

    if results:
        try:
            from storage import FileSaver as FS
            file_saver.save_results(sid, results)

            # Save feedback JSON
            feedback_path = Path("data/results") / sid / "feedback.json"
            feedback_path.parent.mkdir(parents=True, exist_ok=True)
            feedback_data = {k: v.to_dict() for k, v in student_reports.items()}
            feedback_path.write_text(json.dumps(feedback_data, indent=2))
            log(f"Saved {len(results)} results + feedback", "ok")
        except Exception as e:
            log(f"Save warning: {e}", "warn")

    # Validation (Feature 20) — if teacher marks were uploaded
    teacher_bytes = st.session_state.get("teacher_marks_bytes")
    if teacher_bytes and results:
        try:
            from validation_engine import ValidationEngine
            ve = ValidationEngine()
            t_df = ve.load_teacher_marks_csv(teacher_bytes)
            max_map = {k: float(v) for k, v in st.session_state.marks_map.items()}
            val_report = ve.compare(results, t_df, max_map)
            st.session_state.validation_report = val_report
            log(f"Validation complete — accuracy: {val_report.overall_accuracy:.1f}%", "ok")
        except Exception as e:
            log(f"Validation warning: {e}", "warn")

    st.session_state.results = results
    progress_bar.progress(100)
    status_text.empty()
    log("✅ All done!", "ok")

    if results:
        st.markdown('<div class="ag-success">✓ Grading complete! Go to <b>Results</b> page to view detailed feedback.</div>', unsafe_allow_html=True)
        _render_quick_summary(results)
    else:
        st.markdown('<div class="ag-warn">No results generated. Check model answers and uploads.</div>', unsafe_allow_html=True)


def _pdf_to_pil(pdf_bytes: bytes) -> Image.Image:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return pdf.pages[0].to_image(resolution=200).original
    except Exception:
        return Image.new("RGB", (800, 600), "white")


def _render_quick_summary(results):
    """Quick summary table shown immediately after grading."""
    st.markdown("### 🗒 Quick Summary")
    rows = []
    for r in results:
        rows.append({
            "Student": r.student_id, "Question": r.question_id,
            "Marks": f"{r.scores.marks_awarded}/{r.scores.max_marks}",
            "Score %": f"{r.scores.final_score:.1f}%",
            "OCR Method": r.ocr_method,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ─────────────────────────────────────────────
# PAGE: RESULTS  (NEW — Feature 15)
# ─────────────────────────────────────────────

def page_results():
    st.markdown("## 📋 Results & Student Feedback")

    results  = st.session_state.get("results", [])
    reports  = st.session_state.get("student_reports", {})

    if not results:
        empty_state(
            "📋", "No results yet",
            "Complete a grading session to view per-student results and feedback.",
            "→ Go to 'Upload & Grade'"
        )
        return

    # ── Aggregate summary table ──
    st.markdown("### 📊 Class Overview")

    # Build per-student totals
    from collections import defaultdict
    student_totals = defaultdict(lambda: {"marks": 0, "max_marks": 0, "questions": {}})
    for r in results:
        student_totals[r.student_id]["marks"]     += r.scores.marks_awarded
        student_totals[r.student_id]["max_marks"]  += r.scores.max_marks
        student_totals[r.student_id]["questions"][r.question_id] = {
            "marks": r.scores.marks_awarded, "max": r.scores.max_marks,
            "score": r.scores.final_score
        }

    # Summary table
    summary_rows = []
    q_ids = sorted({r.question_id for r in results})
    for student, data in student_totals.items():
        total  = data["marks"]
        maxm   = data["max_marks"]
        pct    = (total / maxm * 100) if maxm else 0
        report = reports.get(student)
        row = {
            "Student":     student,
            "Total Marks": f"{total:.1f}/{maxm:.1f}",
            "Score %":     round(pct, 1),
            "Grade":       report.grade if report else "—",
        }
        for q in q_ids:
            q_data = data["questions"].get(q)
            row[q] = f"{q_data['marks']:.1f}/{q_data['max']:.1f}" if q_data else "—"
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True, height=200)

    # Download summary
    csv_bytes = summary_df.to_csv(index=False).encode()
    st.download_button("⬇ Download Summary CSV", csv_bytes, "summary.csv", "text/csv")

    st.markdown("---")

    # ── Per-student detail view ──
    st.markdown("### 👤 Student Detail View")

    student_ids = list(student_totals.keys())
    if not student_ids:
        return

    selected = st.selectbox("Select Student", student_ids, key="results_student_sel")

    student_results = [r for r in results if r.student_id == selected]
    report = reports.get(selected)

    if not student_results:
        st.warning("No results for this student.")
        return

    # Student header
    total_m  = student_totals[selected]["marks"]
    max_m    = student_totals[selected]["max_marks"]
    total_pct = (total_m / max_m * 100) if max_m else 0
    grade    = report.grade if report else "—"
    g_color  = grade_color(grade)

    col_hdr, col_grade = st.columns([3, 1])
    with col_hdr:
        st.markdown(f"### {selected}")
        st.markdown(f"**Total: {total_m:.1f} / {max_m:.1f} marks ({total_pct:.1f}%)**")
        if report:
            st.markdown(f'<div class="ag-info">{report.overall_feedback.performance_summary}</div>', unsafe_allow_html=True)
    with col_grade:
        render_score_gauge(total_pct, height=160)
        st.markdown(f'<div style="text-align:center"><span class="grade-circle" style="color:{g_color}">{grade}</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Per-question tabs
    q_tab_labels = [f"{r.question_id}" for r in student_results]
    if len(q_tab_labels) > 1:
        tabs = st.tabs(q_tab_labels)
        for tab, r in zip(tabs, student_results):
            with tab:
                _render_question_detail(r, report)
    else:
        _render_question_detail(student_results[0], report)

    # Overall feedback card
    if report:
        st.markdown("---")
        st.markdown("### 💡 Overall Feedback")
        col_s, col_w, col_sg = st.columns(3)

        with col_s:
            st.markdown("**✅ Strengths**")
            for s in report.overall_feedback.strengths:
                st.markdown(f'<div class="ag-success" style="margin-bottom:.3rem">{s}</div>', unsafe_allow_html=True)

        with col_w:
            st.markdown("**⚠ Weak Areas**")
            for w in report.overall_feedback.weak_areas:
                st.markdown(f'<div class="ag-warn" style="margin-bottom:.3rem">{w}</div>', unsafe_allow_html=True)

        with col_sg:
            st.markdown("**💬 Suggestions**")
            for sg in report.overall_feedback.suggestions:
                st.markdown(f'<div class="ag-info" style="margin-bottom:.3rem">{sg}</div>', unsafe_allow_html=True)

        # Download JSON report
        report_json = report.to_json()
        st.download_button(
            f"⬇ Download {selected}'s Report (JSON)",
            report_json.encode(), f"{selected}_report.json", "application/json",
            key=f"dl_report_{selected}"
        )


def _render_question_detail(r, report):
    """Renders full detail for one question — answer comparison + feedback."""
    s = r.scores

    # Score breakdown
    col1, col2 = st.columns([1, 2])
    with col1:
        render_score_gauge(s.final_score, height=180)
        st.markdown(f'<div style="text-align:center; margin-top:-.5rem"><b>{s.marks_awarded}/{s.max_marks}</b> marks</div>', unsafe_allow_html=True)

    with col2:
        # Sub-scores radar / bar
        sub_data = {
            "Similarity":  s.similarity_score * 100,
            "Keywords":    s.keyword_score * 100,
            "Length":      s.length_score * 100,
            "Diagram":     s.diagram_score * 100,
        }
        fig = px.bar(
            x=list(sub_data.keys()), y=list(sub_data.values()),
            color=list(sub_data.values()),
            color_continuous_scale=["#f75f5f", "#f7934f", "#4fd87e"],
            labels={"y": "Score (%)"}, range_y=[0, 100],
        )
        _plotly_layout(fig)
        fig.update_layout(height=180, showlegend=False,
                          coloraxis_showscale=False,
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True, key=str(uuid.uuid4()))

    # Answer comparison
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**📄 Student Answer (OCR)**")
        st.markdown(f'<div class="ag-card" style="min-height:100px; font-size:.88rem">{r.raw_text[:600] or "<i>No text extracted</i>"}</div>', unsafe_allow_html=True)
    with col_b:
        model_ans = st.session_state.model_answers.get(r.question_id, "")
        st.markdown("**📗 Model Answer**")
        st.markdown(f'<div class="ag-card" style="min-height:100px; font-size:.88rem; border-color:rgba(79,216,126,.3)">{model_ans[:600] or "<i>No model answer</i>"}</div>', unsafe_allow_html=True)

    # Keywords
    st.markdown("**🔑 Keywords**")
    kw_html = ""
    for kw in s.matched_keywords[:8]:
        kw_html += f'<span class="kw-chip kw-matched">✓ {kw}</span>'
    for kw in s.missing_keywords[:8]:
        kw_html += f'<span class="kw-chip kw-missing">✗ {kw}</span>'
    st.markdown(kw_html or "<i>No keyword data</i>", unsafe_allow_html=True)

    # Question feedback from report
    if report:
        qf_list = [qf for qf in report.question_feedback
                   if qf.question == r.question_id]
        if qf_list:
            qf = qf_list[0]
            st.markdown("---")
            st.markdown(f"**🤖 AI Feedback** {perf_badge(qf.performance_tag)}", unsafe_allow_html=True)
            st.markdown(f'<div class="ag-card">{qf.feedback}</div>', unsafe_allow_html=True)

            if qf.concept_gaps:
                st.markdown("**🧠 Concept Gaps Detected:**")
                for gap in qf.concept_gaps:
                    st.markdown(f'<div class="ag-warn">{gap}</div>', unsafe_allow_html=True)

    # OCR detail
    if r.vlm_desc and "[VLM unavailable" not in r.vlm_desc:
        with st.expander("🤖 VLM Interpretation"):
            st.markdown(r.vlm_desc[:600])


# ─────────────────────────────────────────────
# PAGE: ANALYTICS  (upgraded — Feature 16)
# ─────────────────────────────────────────────

def page_analytics():
    st.markdown("## 📊 Analytics Dashboard")

    try:
        from storage import ResultRetriever, AnalyticsEngine
        retriever = ResultRetriever()
        analytics = AnalyticsEngine()
        df    = retriever.load_all_scores()
        stats = analytics.compute(df) if not df.empty else {}
    except Exception as e:
        st.error(f"Analytics error: {e}")
        return

    if df.empty:
        empty_state(
            "📊", "No analytics data yet",
            "Complete your first grading session to see class-wide insights.",
            "→ Go to 'Upload & Grade' to start"
        )
        return

    # ── KPIs ──
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Students",   stats.get("total_students", 0))
    c2.metric("Avg Score",  f"{stats.get('class_average', 0):.1f}%")
    c3.metric("Highest",    f"{stats.get('highest_score', 0):.1f}%")
    c4.metric("Lowest",     f"{stats.get('lowest_score', 0):.1f}%")
    c5.metric("Pass Rate",  f"{stats.get('pass_rate', 0):.1f}%")

    st.markdown("---")

    # ── Row 1: Distribution + Q-wise avg ──
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("### Score Distribution")
        dist = stats.get("score_distribution", {})
        fig = px.bar(
            x=list(dist.keys()), y=list(dist.values()),
            color=list(dist.values()),
            color_continuous_scale=["#f75f5f", "#f7934f", "#4fd87e"],
            labels={"x": "Score Range", "y": "Students"},
        )
        _plotly_layout(fig); st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown("### Question-wise Average Score")
        if "question_id" in df.columns and "final_score" in df.columns:
            q_avg = df.groupby("question_id")["final_score"].mean().reset_index()
            q_avg.columns = ["Question", "Avg Score %"]
            # Highlight weak questions
            fig2 = px.bar(q_avg, x="Question", y="Avg Score %",
                          color="Avg Score %",
                          color_continuous_scale=["#f75f5f", "#f7934f", "#4fd87e"],
                          range_color=[0, 100])
            fig2.add_hline(y=50, line_dash="dash", line_color="#8b90a4",
                           annotation_text="Pass threshold")
            _plotly_layout(fig2); st.plotly_chart(fig, use_container_width=True, key=str(uuid.uuid4()))

    # ── Row 2: Student comparison + keyword gaps ──
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown("### Student Score Comparison")
        if "student_id" in df.columns and "final_score" in df.columns:
            s_avg = df.groupby("student_id")["final_score"].mean().reset_index()
            s_avg = s_avg.sort_values("final_score", ascending=True)
            fig3 = px.bar(s_avg, x="final_score", y="student_id",
                          orientation="h",
                          color="final_score",
                          color_continuous_scale=["#f75f5f", "#f7934f", "#4fd87e"],
                          labels={"final_score": "Score %", "student_id": "Student"})
            _plotly_layout(fig3); st.plotly_chart(fig, use_container_width=True, key=str(uuid.uuid4()))

    with col_r2:
        st.markdown("### ⚠ Weak Questions")
        weak = stats.get("weak_questions", [])
        if weak:
            for wq in weak:
                sc = wq["avg_score"]
                cls = score_color_class(sc)
                st.markdown(
                    f'<div class="ag-card">'
                    f'<div class="ag-card-title">Question {wq["question"]}</div>'
                    f'<span class="{cls}">{sc:.1f}%</span> class average'
                    f'<div style="margin-top:.4rem; font-size:.8rem; color:#8b90a4">'
                    f'Needs instructional focus</div></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="ag-success">No weak questions detected ✓</div>', unsafe_allow_html=True)

    # ── Row 3: Common missing keywords (Feature 16) ──
    st.markdown("### 🔑 Common Missing Keywords / Concepts")
    reports = st.session_state.get("student_reports", {})
    if reports:
        from collections import Counter
        all_missing = []
        for rep in reports.values():
            for qf in rep.question_feedback:
                all_missing.extend(qf.missing_keywords)

        kw_counts = Counter(all_missing)
        if kw_counts:
            kw_df = pd.DataFrame(kw_counts.most_common(12),
                                 columns=["Keyword", "Times Missing"])
            fig4 = px.bar(kw_df, x="Times Missing", y="Keyword",
                          orientation="h",
                          color="Times Missing",
                          color_continuous_scale=["#4f8ef7", "#f75f5f"])
            _plotly_layout(fig4); st.plotly_chart(fig, use_container_width=True, key=str(uuid.uuid4()))
            st.markdown('<div class="ag-info">No keyword data — run grading first.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ag-info">Feedback not yet generated. Run grading to see keyword analysis.</div>', unsafe_allow_html=True)

    # ── Top & Bottom performers ──
    st.markdown("### 🏅 Top & Bottom Performers")
    col_top, col_bot = st.columns(2)

    tops = stats.get("top_students", [])
    with col_top:
        st.markdown("**🏆 Top Performers**")
        for t in tops[:5]:
            st.markdown(
                f'<div class="ag-card" style="padding:.75rem 1rem; margin-bottom:.4rem">'
                f'<span style="color:#4fd87e">▲</span> <b>{t["student"]}</b> '
                f'<span class="score-hi">{t["avg_score"]:.1f}%</span></div>',
                unsafe_allow_html=True
            )

    if "student_id" in df.columns and "final_score" in df.columns:
        bottom = (df.groupby("student_id")["final_score"]
                    .mean().sort_values().head(5).reset_index())
        with col_bot:
            st.markdown("**⚠ Needs Attention**")
            for _, row in bottom.iterrows():
                st.markdown(
                    f'<div class="ag-card" style="padding:.75rem 1rem; margin-bottom:.4rem">'
                    f'<span style="color:#f75f5f">▼</span> <b>{row["student_id"]}</b> '
                    f'<span class="score-lo">{row["final_score"]:.1f}%</span></div>',
                    unsafe_allow_html=True
                )

    # ── Raw data ──
    with st.expander("📋 Raw Data Table"):
        st.dataframe(df, use_container_width=True)
        csv_bytes = df.to_csv(index=False).encode()
        st.download_button("⬇ Download CSV", csv_bytes, "analytics.csv", "text/csv")


# ─────────────────────────────────────────────
# PAGE: VALIDATION  (NEW — Feature 20)
# ─────────────────────────────────────────────

def page_validation():
    st.markdown("## ✅ AI vs Teacher Marks Validation")
    st.markdown('<div class="ag-info">Upload teacher-assigned marks to compare against AI scoring. Identify where the AI over-graded or under-graded.</div>', unsafe_allow_html=True)

    # Load pre-run validation or allow fresh upload
    val_report = st.session_state.get("validation_report")
    results    = st.session_state.get("results", [])

    if not results:
        empty_state(
            "✅", "No grading results found",
            "Run a grading session first, then upload teacher marks here.",
            "→ Go to 'Upload & Grade'"
        )
        return

    st.markdown("### Upload Teacher Marks")
    t_file = st.file_uploader(
        "Teacher marks CSV (columns: student_id, question_id, marks)",
        type=["csv"], key="val_upload"
    )
    if t_file:
        st.markdown(f'<div class="file-preview-card"><span class="file-icon">📊</span><div><div class="file-name">{t_file.name}</div><div class="file-meta">{t_file.size // 1024} KB</div></div></div>', unsafe_allow_html=True)

    if st.button("🔍 Run Validation") and t_file:
        try:
            from validation_engine import ValidationEngine
            ve    = ValidationEngine()
            t_df  = ve.load_teacher_marks_csv(t_file.read())
            max_map = {k: float(v) for k, v in st.session_state.marks_map.items()}
            val_report = ve.compare(results, t_df, max_map)
            st.session_state.validation_report = val_report
            st.markdown('<div class="ag-success">✓ Validation complete</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Validation error: {e}")
            return

    if not val_report:
        empty_state(
            "📐", "No validation data yet",
            "Upload teacher marks above and click Run Validation.",
        )
        return

    # ── Validation KPIs ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Accuracy",   f"{val_report.overall_accuracy:.1f}%")
    c2.metric("Mean Abs Error",     f"{val_report.mean_abs_error:.2f} marks")
    c3.metric("RMSE",               f"{val_report.rmse:.3f}")
    c4.metric("Agreement Rate",     f"{val_report.agreement_rate:.1f}%",
              help="% of cases within ±1 mark of teacher")

    st.markdown("---")

    # ── Comparison chart ──
    from validation_engine import ValidationEngine
    ve  = ValidationEngine()
    cdf = ve.to_dataframe(val_report)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("### AI vs Teacher Marks (Scatter)")
        fig = px.scatter(
            cdf, x="Teacher Marks", y="AI Marks",
            color="Accuracy %", size="Max Marks",
            color_continuous_scale=["#f75f5f", "#4f8ef7", "#4fd87e"],
            hover_data=["Student", "Question"],
            labels={"Teacher Marks": "Teacher", "AI Marks": "AI"},
        )
        # Perfect agreement line
        max_val = max(cdf["Max Marks"].max(), 1)
        fig.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val],
                                 mode="lines", name="Perfect Agreement",
                                 line=dict(dash="dash", color="#8b90a4")))
        _plotly_layout(fig); st.plotly_chart(fig, use_container_width=True, key=str(uuid.uuid4()))

    with col_r:
        st.markdown("### Score Difference Distribution")
        fig2 = px.histogram(
            cdf, x="Difference", nbins=15,
            color_discrete_sequence=["#4f8ef7"],
            labels={"Difference": "AI − Teacher Marks"},
        )
        fig2.add_vline(x=0, line_dash="dash", line_color="#4fd87e")
        _plotly_layout(fig2); st.plotly_chart(fig, use_container_width=True, key=str(uuid.uuid4()))

    # ── Detail table ──
    st.markdown("### 📋 Detailed Comparison")

    def highlight_diff(row):
        d = row.get("Difference", 0)
        if d > 1:   return ['color: #f7934f'] * len(row)
        if d < -1:  return ['color: #4f8ef7'] * len(row)
        return ['color: #4fd87e'] * len(row)

    st.dataframe(cdf.style.apply(highlight_diff, axis=1), use_container_width=True)

    # ── Flagged cases ──
    if val_report.over_graded:
        st.markdown(f"### ⬆ Over-graded Cases ({len(val_report.over_graded)})")
        st.markdown('<div class="ag-warn">AI awarded more than 1 mark above teacher score.</div>', unsafe_allow_html=True)
        over_df = pd.DataFrame([{
            "Student": e.student_id, "Question": e.question_id,
            "AI": e.ai_marks, "Teacher": e.teacher_marks, "Diff": e.diff
        } for e in val_report.over_graded])
        st.dataframe(over_df, use_container_width=True)

    if val_report.under_graded:
        st.markdown(f"### ⬇ Under-graded Cases ({len(val_report.under_graded)})")
        st.markdown('<div class="ag-info">AI awarded more than 1 mark below teacher score.</div>', unsafe_allow_html=True)
        under_df = pd.DataFrame([{
            "Student": e.student_id, "Question": e.question_id,
            "AI": e.ai_marks, "Teacher": e.teacher_marks, "Diff": e.diff
        } for e in val_report.under_graded])
        st.dataframe(under_df, use_container_width=True)

    # Download
    csv_bytes = cdf.to_csv(index=False).encode()
    st.download_button("⬇ Download Validation Report (CSV)", csv_bytes,
                       "validation_report.csv", "text/csv")


# ─────────────────────────────────────────────
# PAGE: PAST SESSIONS  (with empty state)
# ─────────────────────────────────────────────

def page_past_sessions():
    st.markdown("## 📁 Past Sessions")

    try:
        from storage import SessionManager, ResultRetriever
        sessions  = SessionManager()
        retriever = ResultRetriever()
        sess_list = sessions.list_sessions()
    except Exception as e:
        st.error(f"Error: {e}"); return

    if not sess_list:
        empty_state(
            "📁", "No past sessions found",
            "Your completed grading sessions will appear here.",
            "→ Start your first session in 'Upload & Grade'"
        )
        return

    st.markdown(f"**{len(sess_list)} session(s) found**")

    for sess in reversed(sess_list):
        sid    = sess["session_id"]
        name   = sess.get("name", sid)
        status = sess.get("status", "?")
        status_badge = (
            '<span style="color:#4fd87e">● Completed</span>'
            if status == "completed"
            else '<span style="color:#f7934f">● In Progress</span>'
        )
        with st.expander(f"📂 {name}  {status_badge}", expanded=False):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"**ID:** `{sid}`")
                st.markdown(f"**Created:** {sess.get('created_at','?')[:19]}")
            with c2:
                df = retriever.load_scores(sid)
                if df is not None and not df.empty:
                    col_a, col_b = st.columns(2)
                    col_a.metric("Students", df["student_id"].nunique() if "student_id" in df.columns else "?")
                    col_b.metric("Avg %", f"{df['final_score'].mean():.1f}%" if "final_score" in df.columns else "?")

                    c_csv, c_fb = st.columns(2)
                    with c_csv:
                        st.download_button("⬇ CSV", df.to_csv(index=False).encode(),
                                           f"{sid}_scores.csv", "text/csv", key=f"dl_{sid}")
                    with c_fb:
                        fb_path = Path("data/results") / sid / "feedback.json"
                        if fb_path.exists():
                            st.download_button("⬇ Feedback JSON", fb_path.read_bytes(),
                                               f"{sid}_feedback.json", "application/json",
                                               key=f"dl_fb_{sid}")
                else:
                    st.info("No results saved yet.")


# ─────────────────────────────────────────────
# PAGE: SETTINGS  (unchanged from v1)
# ─────────────────────────────────────────────

def page_settings():
    st.markdown("## ⚙️ Settings & System Info")

    st.markdown("### 🤖 VLM Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""<div class="ag-card"><div class="ag-card-title">Option 1 — LLaVA via Ollama (Recommended)</div>
        Best quality. Runs locally. Free.<br><br>
        <code>curl https://ollama.ai/install.sh | sh</code><br>
        <code>ollama pull llava:7b</code></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="ag-card"><div class="ag-card-title">Option 2 — BLIP-2 (HuggingFace)</div>
        Good quality. Downloads ~6 GB on first run.<br><br>
        <code>pip install transformers accelerate</code></div>""", unsafe_allow_html=True)

    st.markdown("### 📦 Dependency Status")
    deps = {
        "pytesseract": "OCR", "easyocr": "Handwriting OCR",
        "cv2": "Image preprocessing", "pdfplumber": "PDF parsing",
        "sklearn": "TF-IDF scoring", "plotly": "Charts",
        "pandas": "Analytics", "PIL": "Image handling",
        "requests": "Ollama API",
    }
    cols = st.columns(3)
    for i, (pkg, desc) in enumerate(deps.items()):
        with cols[i % 3]:
            try:
                __import__(pkg)
                st.markdown(f'<div class="ag-success">✓ <b>{pkg}</b> — {desc}</div>', unsafe_allow_html=True)
            except ImportError:
                st.markdown(f'<div class="ag-warn">✗ <b>{pkg}</b> — {desc}</div>', unsafe_allow_html=True)

    st.markdown("### 📁 Storage Layout")
    st.markdown("""<div class="ag-card"><div class="ag-card-title">File System</div>
    <pre style="font-size:.82rem; color:#8b90a4">
data/
├── uploads/{session_id}/    ← raw student files
├── results/{session_id}/
│   ├── scores.csv           ← marks table
│   ├── details.json         ← full breakdown
│   └── feedback.json        ← student reports
└── sessions.json            ← session index
    </pre></div>""", unsafe_allow_html=True)

    st.markdown("### ⚡ Optimizations Active")
    st.markdown("""<div class="ag-info">
    • VLM cache per image hash — no re-runs<br>
    • EasyOCR singleton — loads once<br>
    • VLM gated by OCR confidence threshold (0.5)<br>
    • Feedback generation batched after grading<br>
    • Validation runs only when teacher marks provided
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────

page_map = {
    "🏠  Dashboard":      page_dashboard,
    "📄  Question Paper": page_question_paper,
    "📤  Upload & Grade": page_upload_grade,
    "📋  Results":        page_results,
    "📊  Analytics":      page_analytics,
    "✅  Validation":     page_validation,
    "📁  Past Sessions":  page_past_sessions,
    "⚙️  Settings":       page_settings,
}

page_map[page]()

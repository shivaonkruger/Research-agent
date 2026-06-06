import uuid  
import streamlit as st
import requests
import json

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Research Workflow",
    page_icon="⟨R⟩",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0d0d0d;
    color: #e8e8e8;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem 1rem; max-width: 100%; }

/* input */
.stTextInput input {
    background: #111 !important;
    border: 1px solid #252525 !important;
    border-radius: 8px !important;
    color: #e0e0e0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.88rem !important;
    padding: 0.6rem 1rem !important;
}
.stTextInput input:focus {
    border-color: #c0392b !important;
    box-shadow: 0 0 0 2px rgba(192,57,43,0.15) !important;
}

/* button */
.stButton > button {
    background: #c0392b !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    padding: 0.5rem 1.5rem !important;
}
.stButton > button:hover { background: #a93226 !important; }

/* pipeline stage indicators */
.pipeline {
    display: flex;
    align-items: center;
    gap: 0;
    margin: 1.5rem 0 2rem;
    font-family: 'JetBrains Mono', monospace;
}
.stage-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 6px 14px;
    border-radius: 4px;
    transition: all 0.2s ease;
}
.stage-waiting  { color: #2a2a2a; background: #111; border: 1px solid #1a1a1a; }
.stage-active   { color: #e8c84a; background: #1a1800; border: 1px solid #3a3000; }
.stage-done     { color: #4caf7d; background: #0e1a10; border: 1px solid #1a3520; }
.stage-arrow    { color: #222; font-size: 0.8rem; padding: 0 4px; }

/* output panels */
.panel {
    background: #111;
    border: 1px solid #1e1e1e;
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    font-size: 0.88rem;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
}
.panel-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.6rem;
}
.panel-search  { border-left: 3px solid #3a5a8a; }
.panel-summary { border-left: 3px solid #7b5ea7; }
.panel-critique{ border-left: 3px solid #c07a2b; }
.panel-final   { border-left: 3px solid #c0392b; }
.label-search  { color: #3a5a8a; }
.label-summary { color: #7b5ea7; }
.label-critique{ color: #c07a2b; }
.label-final   { color: #c0392b; }

/* source links */
.source-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 5px 0;
    border-bottom: 1px solid #1a1a1a;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
}
.source-num { color: #333; min-width: 20px; }
.source-title { color: #888; }
.source-url { color: #3a5a8a; word-break: break-all; }

/* error */
.error-box {
    background: #1a0a0a;
    border: 1px solid #4a1010;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    color: #e74c3c;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
}

.section-divider {
    border: none;
    border-top: 1px solid #1a1a1a;
    margin: 1.5rem 0;
}
</style>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────────
if "history" not in st.session_state:
    # Each entry: {question, search_results, summary, critique, final, error}
    st.session_state.history = []

if "current" not in st.session_state:
    st.session_state.current = None   # the in-progress result dict

if "active_stage" not in st.session_state:
    st.session_state.active_stage = None  # which node is currently running

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# ── helpers ────────────────────────────────────────────────────────────────

STAGES = ["search_node", "summarizer_node", "critic_node"]
STAGE_NAMES = {"search_node": "Search", "summarizer_node": "Summarize", "critic_node": "Critique"}


def render_pipeline(active: str | None, done: list[str]):
    html = '<div class="pipeline">'
    for i, stage in enumerate(STAGES):
        if stage in done:
            cls = "stage-done"
            dot = "✓"
        elif stage == active:
            cls = "stage-active"
            dot = "●"
        else:
            cls = "stage-waiting"
            dot = "○"
        html += f'<div class="stage-item {cls}">{dot} {STAGE_NAMES[stage]}</div>'
        if i < len(STAGES) - 1:
            html += '<span class="stage-arrow">→</span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_result(result: dict):
    if result.get("error"):
        st.markdown(f'<div class="error-box">⚠ {result["error"]}</div>', unsafe_allow_html=True)
        return

    # Search results
    if result.get("search_results"):
        st.markdown("""
        <div class="panel panel-search">
            <div class="panel-label label-search">Search Results</div>
        """, unsafe_allow_html=True)
        for i, r in enumerate(result["search_results"], 1):
            st.markdown(f"""
            <div class="source-item">
                <span class="source-num">{i}.</span>
                <span>
                    <div class="source-title">{r['title']}</div>
                    <div class="source-url">{r['url']}</div>
                </span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Summary
    if result.get("summary"):
        st.markdown(f"""
        <div class="panel panel-summary">
            <div class="panel-label label-summary">Summary</div>
            {result['summary']}
        </div>
        """, unsafe_allow_html=True)

    # Critique
    if result.get("critique"):
        st.markdown(f"""
        <div class="panel panel-critique">
            <div class="panel-label label-critique">Critique</div>
            {result['critique']}
        </div>
        """, unsafe_allow_html=True)

    # Final response
    if result.get("final"):
        st.markdown(f"""
        <div class="panel panel-final">
            <div class="panel-label label-final">Final Response</div>
            {result['final']}
        </div>
        """, unsafe_allow_html=True)


# ── header ─────────────────────────────────────────────────────────────────
st.markdown("### ⟨R⟩ Research Workflow")
st.caption("Cerebras · Tavily · LangGraph — Search → Summarize → Critique → Respond")
st.divider()

# ── input ──────────────────────────────────────────────────────────────────
c1, c2 = st.columns([8, 2])
with c1:
    question = st.text_input(
        "Research question",
        placeholder="What is the current state of nuclear fusion energy?",
        label_visibility="collapsed"
    )
with c2:
    search_btn = st.button("Research →", use_container_width=True)

# ── pipeline status ────────────────────────────────────────────────────────
pipeline_placeholder = st.empty()
result_placeholder = st.empty()

# ── history ────────────────────────────────────────────────────────────────
if st.session_state.history:
    with st.expander(f"Previous results ({len(st.session_state.history)})", expanded=False):
        for i, entry in enumerate(reversed(st.session_state.history)):
            st.markdown(f"**Q: {entry['question']}**")
            render_result(entry)
            if i < len(st.session_state.history) - 1:
                st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ── search handler ─────────────────────────────────────────────────────────
if search_btn and question.strip():
    q = question.strip()

    result = {
        "question": q,
        "search_results": [],
        "summary": "",
        "critique": "",
        "final": "",
        "error": "",
    }

    done_stages = []
    active_stage = None

    # Show empty pipeline immediately
    with pipeline_placeholder:
        render_pipeline(None, [])

    try:
        with requests.post(
            f"{API_URL}/research",
           json={
                "question": q,
                "thread_id": st.session_state.thread_id,               
            },
            stream=True,
            timeout=120
        ) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    event = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                t = event.get("type")

                if t == "stage":
                    stage = event.get("stage")
                    if active_stage and active_stage != stage:
                        done_stages.append(active_stage)
                    active_stage = stage
                    with pipeline_placeholder:
                        render_pipeline(active_stage, done_stages)

                elif t == "results":
                    result["search_results"] = event.get("search_results", [])
                    with result_placeholder:
                        render_result(result)

                elif t == "summary":
                    result["summary"] = event.get("content", "")
                    with result_placeholder:
                        render_result(result)

                elif t == "critique":
                    result["critique"] = event.get("content", "")
                    with result_placeholder:
                        render_result(result)

                elif t == "final":
                    result["final"] = event.get("content", "")
                    if active_stage:
                        done_stages.append(active_stage)
                        active_stage = None
                    with pipeline_placeholder:
                        render_pipeline(None, done_stages)
                    with result_placeholder:
                        render_result(result)

                elif t == "error":
                    result["error"] = event.get("content", "Unknown error")
                    with result_placeholder:
                        render_result(result)

    except requests.exceptions.ConnectionError:
        result["error"] = "Cannot connect to API. Run: uvicorn api:app --reload --port 8000"
        with result_placeholder:
            render_result(result)
    except Exception as e:
        result["error"] = str(e)
        with result_placeholder:
            render_result(result)

    # Save to history
    st.session_state.history.append(result)
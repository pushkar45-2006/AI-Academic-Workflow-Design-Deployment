"""
app.py
------
Academic AI Workflow Assistant — Streamlit Entry Point

Three workflows accessible via sidebar navigation:
  1. 📝 Assignment Corrector  — Upload assignment + rubric, get AI grading.
  2. 🔍 Research Searcher     — Enter a topic, get ranked academic papers.
  3. 📄 Paper Summariser      — Upload a PDF paper, get a structured summary.

Run with:
    streamlit run app.py
"""

import logging
import sys
import os

import streamlit as st

# ---------------------------------------------------------------------------
# Logging setup (visible in terminal, not in the UI)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page configuration — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Academic AI Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Local imports (after st.set_page_config)
# ---------------------------------------------------------------------------
from config import load_config, validate_config
from pdf_utils import extract_text_from_pdf, truncate_text
from llm_utils import get_llm, grade_assignment, summarise_paper
from search_utils import search_academic_papers

# ---------------------------------------------------------------------------
# Custom CSS — refined dark-academic aesthetic
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Source+Serif+4:ital,wght@0,300;0,400;1,300&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Root palette ── */
:root {
    --bg:        #0f0e0c;
    --bg2:       #181714;
    --bg3:       #221f1b;
    --border:    #33302a;
    --gold:      #c9a84c;
    --gold-dim:  #7a6228;
    --text:      #e8e0d0;
    --text-dim:  #8a8070;
    --accent:    #5b8fa8;
    --success:   #5a9e6f;
    --error:     #c05b5b;
}

/* ── Global ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Source Serif 4', Georgia, serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: var(--bg2) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* ── Headings ── */
h1, h2, h3 {
    font-family: 'Playfair Display', serif !important;
    color: var(--gold) !important;
    letter-spacing: 0.02em;
}
h1 { font-size: 2rem !important; font-weight: 700 !important; }

/* ── Code & mono ── */
code, pre, [data-testid="stCode"] {
    font-family: 'JetBrains Mono', monospace !important;
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--gold-dim), var(--gold)) !important;
    color: var(--bg) !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Playfair Display', serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    padding: 0.5rem 1.5rem !important;
    transition: opacity 0.2s, transform 0.1s !important;
}
.stButton > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}

/* ── Inputs & text areas ── */
.stTextInput input, .stTextArea textarea {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 4px !important;
    font-family: 'Source Serif 4', serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--gold-dim) !important;
    box-shadow: 0 0 0 2px rgba(201,168,76,.15) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--bg3) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 6px !important;
}

/* ── Dividers ── */
hr { border-color: var(--border) !important; }

/* ── Info / warning / success / error boxes ── */
.stAlert {
    background: var(--bg3) !important;
    border-radius: 4px !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--gold) !important; }

/* ── Result card ── */
.result-card {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold);
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
    font-family: 'Source Serif 4', serif;
    line-height: 1.65;
}

/* ── Status badge ── */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
}
.badge-gold  { background: var(--gold-dim); color: #f5e9c8; }
.badge-blue  { background: #2a4a5e; color: #9ecde0; }
.badge-green { background: #1e3d28; color: #8fd4a0; }

/* ── Section label ── */
.section-label {
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-dim);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 0.3rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — configuration & navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("# 🎓 Academic AI")
    st.markdown("<div class='section-label'>Workflow</div>", unsafe_allow_html=True)

    page = st.radio(
        label="Select workflow",
        options=["📝 Assignment Corrector", "🔍 Research Searcher", "📄 Paper Summariser"],
        label_visibility="collapsed",
    )

    st.divider()
    
    # --- SECURE API KEY INPUT ---
    st.markdown("<div class='section-label'>Authentication</div>", unsafe_allow_html=True)
    api_key_input = st.text_input(
        "Enter Google API Key", 
        type="password", 
        help="Get your free key at aistudio.google.com"
    )
    
    # If the user hasn't entered a key, stop the app completely
    if not api_key_input:
        st.warning("Please enter your Google API Key to unlock AI features.")
        st.stop()
        
    # Dynamically set the environment variable so LangChain and config.py pick it up
    os.environ["GOOGLE_API_KEY"] = api_key_input
    
    st.success("API Key Loaded securely!")
    st.divider()
    
    # Load config AFTER setting the API key
    st.session_state.config = load_config()
    cfg = st.session_state.config
    errors = validate_config(cfg)

    if errors:
        for err in errors:
            st.error(f"⚠ {err}")
    else:
        provider_badge = "badge-gold" if cfg.llm_provider == "anthropic" else "badge-blue"
        st.markdown(
            f"**LLM:** <span class='badge {provider_badge}'>{cfg.llm_provider.upper()}</span>  \n"
            f"**Search:** <span class='badge badge-green'>{cfg.search_provider.upper()}</span>",
            unsafe_allow_html=True,
        )

        # Force re-initialize LLM with the new key provided by user
        try:
            st.session_state.llm = get_llm(cfg)
            st.success("✓ LLM ready")
        except Exception as exc:
            st.error(f"LLM init failed: {exc}")

    st.divider()
    st.markdown(
        "<small style='color:var(--text-dim)'>Built with LangChain + Streamlit</small>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Guard: no valid config → stop here
# ---------------------------------------------------------------------------
if validate_config(st.session_state.config):
    st.warning("⚠ Please fix the configuration errors shown in the sidebar before using the app.")
    st.stop()

llm = st.session_state.llm
cfg = st.session_state.config


# ===========================================================================
# PAGE 1 — Assignment Corrector
# ===========================================================================
if page == "📝 Assignment Corrector":
    st.title("📝 Assignment Corrector")
    st.markdown(
        "Upload a student's assignment and a grading rubric. "
        "The AI will evaluate the submission against the rubric and return "
        "a score, section-by-section breakdown, and constructive feedback."
    )
    st.divider()

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown("<div class='section-label'>Student Assignment</div>", unsafe_allow_html=True)
        assignment_file = st.file_uploader(
            "Upload assignment PDF",
            type=["pdf"],
            key="assignment_pdf",
            label_visibility="collapsed",
        )

    with col_right:
        st.markdown("<div class='section-label'>Grading Rubric</div>", unsafe_allow_html=True)
        rubric_file = st.file_uploader(
            "Upload rubric PDF (optional)",
            type=["pdf"],
            key="rubric_pdf",
            label_visibility="collapsed",
        )
        st.markdown("<div class='section-label' style='margin-top:0.8rem'>— or paste rubric text —</div>", unsafe_allow_html=True)
        rubric_text_input = st.text_area(
            "Rubric text",
            height=180,
            placeholder="e.g.\n• Introduction (20 pts): Clear thesis, engaging hook.\n• Analysis (40 pts): Evidence-based argument…",
            label_visibility="collapsed",
        )

    st.divider()
    grade_btn = st.button("⚖ Grade Assignment", use_container_width=True)

    if grade_btn:
        # Validate inputs
        if not assignment_file:
            st.error("Please upload the student assignment PDF.")
            st.stop()

        rubric_source = ""
        if rubric_file:
            with st.spinner("Extracting rubric from PDF…"):
                res = extract_text_from_pdf(rubric_file.read())
            if not res.success:
                st.warning(f"Could not extract rubric PDF ({res.error}). Falling back to pasted text.")
            else:
                rubric_source = res.text

        if not rubric_source and rubric_text_input.strip():
            rubric_source = rubric_text_input.strip()

        if not rubric_source:
            st.error("Please provide a rubric — either upload a PDF or paste the rubric text.")
            st.stop()

        # Extract assignment
        with st.spinner("Extracting assignment text…"):
            assign_res = extract_text_from_pdf(assignment_file.read())

        if not assign_res.success:
            st.error(f"Failed to extract assignment PDF: {assign_res.error}")
            st.stop()

        st.info(
            f"📄 Extracted {assign_res.page_count} page(s) via **{assign_res.method_used}** "
            f"({len(assign_res.text):,} chars)"
        )

        # Truncate if very long to avoid context overflow
        assignment_text = truncate_text(assign_res.text, max_chars=14_000)

        # Grade
        with st.spinner("AI is grading the assignment… this may take 15–30 seconds."):
            try:
                report = grade_assignment(llm, assignment_text, rubric_source)
            except Exception as exc:
                st.error(f"Grading failed: {exc}")
                st.stop()

        st.success("✓ Grading complete!")
        st.divider()
        st.markdown("### 📊 Grading Report")
        st.markdown(f"<div class='result-card'>{report}</div>", unsafe_allow_html=True)

        st.download_button(
            label="⬇ Download Report (.md)",
            data=report,
            file_name="grading_report.md",
            mime="text/markdown",
        )


# ===========================================================================
# PAGE 2 — Research Searcher
# ===========================================================================
elif page == "🔍 Research Searcher":
    st.title("🔍 Academic Research Searcher")
    st.markdown(
        "Enter a research topic or question. The assistant will search for "
        "the most relevant academic papers and return the top results with "
        "titles, authors, links, and abstracts."
    )
    st.divider()

    query = st.text_input(
        "Research topic or question",
        placeholder="e.g. transformer architecture for long-context NLP tasks",
    )

    search_btn = st.button("🔎 Search Papers", use_container_width=True)

    if search_btn:
        if not query.strip():
            st.error("Please enter a research query.")
            st.stop()

        with st.spinner(f"Searching {cfg.search_provider.upper()} for academic papers…"):
            try:
                results = search_academic_papers(query.strip(), cfg)
            except RuntimeError as exc:
                st.error(str(exc))
                st.stop()

        if not results:
            st.warning("No results found. Try a different query or check your API key.")
            st.stop()

        st.success(f"✓ Found {len(results)} result(s) for **{query}**")
        st.divider()

        for i, paper in enumerate(results, start=1):
            with st.container():
                st.markdown(
                    f"<div class='result-card'>{paper.to_markdown(i)}</div>",
                    unsafe_allow_html=True,
                )


# ===========================================================================
# PAGE 3 — Paper Summariser
# ===========================================================================
elif page == "📄 Paper Summariser":
    st.title("📄 Research Paper Summariser")
    st.markdown(
        "Upload a research paper PDF. The AI will read the full document "
        "using a **map-reduce** strategy and produce a structured summary: "
        "executive overview, methodologies, and key findings."
    )
    st.divider()

    paper_file = st.file_uploader(
        "Upload research paper PDF",
        type=["pdf"],
        key="paper_pdf",
        label_visibility="visible",
    )

    with st.expander("⚙ Advanced options"):
        chunk_size = st.slider(
            "Chunk size (chars)",
            min_value=500, max_value=4000, value=cfg.chunk_size, step=100,
            help="Smaller chunks = more API calls but finer granularity.",
        )
        chunk_overlap = st.slider(
            "Chunk overlap (chars)",
            min_value=0, max_value=500, value=cfg.chunk_overlap, step=50,
            help="Overlap helps preserve context at chunk boundaries.",
        )

    summarise_btn = st.button("📑 Summarise Paper", use_container_width=True)

    if summarise_btn:
        if not paper_file:
            st.error("Please upload a research paper PDF.")
            st.stop()

        with st.spinner("Extracting text from PDF…"):
            res = extract_text_from_pdf(paper_file.read())

        if not res.success:
            st.error(f"Could not extract PDF: {res.error}")
            st.stop()

        st.info(
            f"📄 {res.page_count} page(s) extracted via **{res.method_used}** "
            f"({len(res.text):,} chars). Running map-reduce summarisation…"
        )

        # Estimate chunk count for the user
        estimated_chunks = max(1, len(res.text) // chunk_size)
        st.warning(
            f"ℹ This will make approximately **{estimated_chunks} LLM call(s)** "
            f"(one per chunk) plus one final reduction call. "
            f"Large papers may take 1–3 minutes."
        )

        with st.spinner("Summarising… (map phase: reading chunks)"):
            try:
                summary = summarise_paper(
                    llm,
                    res.text,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
            except Exception as exc:
                st.error(f"Summarisation failed: {exc}")
                logger.exception("Summarisation error")
                st.stop()

        st.success("✓ Summarisation complete!")
        st.divider()
        st.markdown("### 📋 Paper Summary")
        st.markdown(f"<div class='result-card'>{summary}</div>", unsafe_allow_html=True)

        st.download_button(
            label="⬇ Download Summary (.md)",
            data=summary,
            file_name="paper_summary.md",
            mime="text/markdown",
        )

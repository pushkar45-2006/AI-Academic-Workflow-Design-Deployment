# 🎓 Academic AI Workflow Assistant

A production-ready AI-powered web application for academic tasks, built with **Python**, **LangChain**, and **Streamlit**.

---

## ✨ Features

| Workflow | Description |
|---|---|
| 📝 **Assignment Corrector** | Upload a student PDF + rubric → AI grades and gives structured feedback |
| 🔍 **Research Searcher** | Enter a topic → ranked list of academic papers with abstracts and links |
| 📄 **Paper Summariser** | Upload a research PDF → executive summary, methodologies, findings (map-reduce) |

---

## 🗂 Repository Structure

```
academic-ai-assistant/
│
├── app.py              # Streamlit entry point (all three UI pages)
├── config.py           # Environment variable loader & validator
├── pdf_utils.py        # PDF extraction (PyMuPDF → pdfplumber → PyPDF2) + chunking
├── llm_utils.py        # LLM factory, grading chain, map-reduce summarisation
├── search_utils.py     # Tavily / SerpAPI search + normalised PaperResult type
│
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore          # Excludes .env, __pycache__, etc.
└── README.md           # This file
```

---

## ⚙️ Quick Start

### 1. Clone & install

```bash
git clone https://github.com/your-org/academic-ai-assistant.git
cd academic-ai-assistant

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

**Minimum required keys:**

| Variable | When needed |
|---|---|
| `ANTHROPIC_API_KEY` | `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | `LLM_PROVIDER=openai` |
| `TAVILY_API_KEY` | `SEARCH_PROVIDER=tavily` |
| `SERPAPI_API_KEY` | `SEARCH_PROVIDER=serpapi` |

### 3. Run

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## 🔧 Configuration Reference

All settings live in `.env`:

```ini
# LLM — choose "anthropic" or "openai"
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Search — choose "tavily" or "serpapi"
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=tvly-...

# Tuning (optional)
MAX_TOKENS=4096
CHUNK_SIZE=2000
CHUNK_OVERLAP=200
SEARCH_RESULT_COUNT=5
```

---

## 🏗 Architecture

```
User (Browser)
    │
    ▼
app.py  (Streamlit UI)
    │
    ├── config.py          ← reads .env, validates keys
    │
    ├── pdf_utils.py       ← PyMuPDF / pdfplumber / PyPDF2
    │       └── chunk_text()  ← RecursiveCharacterTextSplitter
    │
    ├── llm_utils.py       ← get_llm() → ChatAnthropic | ChatOpenAI
    │       ├── grade_assignment()    (single-shot)
    │       └── summarise_paper()    (map-reduce over chunks)
    │
    └── search_utils.py    ← Tavily | SerpAPI → [PaperResult]
```

### PDF Extraction Strategy

Extractors are tried in order; the first successful result is used:

1. **PyMuPDF** — fast, handles complex layouts and most scanned text
2. **pdfplumber** — excellent for tables and columnar layouts
3. **PyPDF2** — lightweight fallback for simple text PDFs

### Summarisation (Map-Reduce)

```
PDF text → chunk_text() → [chunk₁, chunk₂, …, chunkₙ]
                                │
                           MAP phase
                    (one LLM call per chunk)
                                │
                        [summary₁, …, summaryₙ]
                                │
                         REDUCE phase
                    (one final LLM call merges all)
                                │
                        Structured final report
```

---

## 🔑 Obtaining API Keys

| Service | URL |
|---|---|
| Anthropic | https://console.anthropic.com |
| OpenAI | https://platform.openai.com/api-keys |
| Tavily | https://tavily.com |
| SerpAPI | https://serpapi.com |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI |
| `langchain`, `langchain-anthropic`, `langchain-openai` | LLM orchestration |
| `anthropic`, `openai` | Provider SDKs |
| `pymupdf` | Primary PDF extractor |
| `pdfplumber` | Secondary PDF extractor |
| `pypdf2` | Tertiary PDF extractor |
| `tavily-python` | Academic search |
| `google-search-results` | SerpAPI client |
| `python-dotenv` | `.env` file loading |

---

## 📄 License

MIT

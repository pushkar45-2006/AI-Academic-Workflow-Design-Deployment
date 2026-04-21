"""
llm_utils.py
------------
Academic AI Workflow logic supporting Google Gemini (Free Tier), 
Anthropic, and OpenAI.

Workflows:
  1. get_llm()           — Factory for AI model initialization (Secure Version)
  2. grade_assignment()  — Assignment Correction System
  3. summarise_paper()   — Research Paper Summariser (map-reduce)
"""

from __future__ import annotations
import os
import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import AppConfig
from pdf_utils import chunk_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM Factory
# ---------------------------------------------------------------------------

def get_llm(config: AppConfig) -> Optional[BaseChatModel]:
    """
    Return a configured LangChain chat model based on the provider in config.
    Prioritizes user-provided keys from the UI to prevent leakage.
    """
    if config.llm_provider == "gemini":
        # Pull key from the config object (set by the sidebar in app.py)
        # Fallback to the environment only if absolutely necessary
        api_key = getattr(config, 'google_api_key', None) or os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            logger.warning("No Google API key provided. LLM initialization aborted.")
            return None
            
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        try:
            return ChatGoogleGenerativeAI(
                model="gemini-pro", # Changed to universal alias to prevent 404 NOT_FOUND
                google_api_key=api_key,
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"Error initializing Gemini: {e}")
            return None

    if config.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.anthropic_model,
            anthropic_api_key=config.anthropic_api_key,
            max_tokens=config.max_tokens,
            temperature=0.3,
        )

    if config.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.openai_model,
            openai_api_key=config.openai_api_key,
            max_tokens=config.max_tokens,
            temperature=0.3,
        )

    raise ValueError(f"Unsupported LLM provider: '{config.llm_provider}'")


# ---------------------------------------------------------------------------
# Helper: run a single prompt
# ---------------------------------------------------------------------------

def _invoke_llm(llm: Optional[BaseChatModel], system: str, human: str) -> str:
    """Simple wrapper: system + human → string response."""
    if not llm:
        return "Error: AI model not initialized. Please provide a valid API key in the sidebar."
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "{input}"),
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"input": human})


# ---------------------------------------------------------------------------
# Workflow 1: Assignment Correction
# ---------------------------------------------------------------------------

GRADING_SYSTEM_PROMPT = """You are an experienced academic grader with expertise across multiple disciplines.
Your task is to evaluate a student's assignment against a provided rubric.

Be constructive, precise, and fair. Support every score with specific evidence from the student's work.
Format your response with these exact sections:
---
## Overall Score
[Score] / [Max Score]  (e.g., 78 / 100)

## Section-by-Section Breakdown
[For each rubric criterion: criterion name, score awarded, brief justification]

## Strengths
[2–4 bullet points of what the student did well]

## Areas for Improvement
[2–4 bullet points of specific, actionable feedback]

## Summary Comment
[2–3 sentence holistic comment suitable for the student to read]
---"""

def grade_assignment(
    llm: BaseChatModel,
    assignment_text: str,
    rubric_text: str,
) -> str:
    """
    Evaluate a student assignment against a rubric using the LLM.
    """
    human_prompt = f"""## GRADING RUBRIC
{rubric_text}

---

## STUDENT ASSIGNMENT
{assignment_text}

---

Please evaluate this student assignment against the rubric above and provide a detailed grading report."""

    logger.info("Sending assignment to LLM for grading...")
    return _invoke_llm(llm, GRADING_SYSTEM_PROMPT, human_prompt)


# ---------------------------------------------------------------------------
# Workflow 2: Paper Summarisation (Map-Reduce)
# ---------------------------------------------------------------------------

MAP_SYSTEM_PROMPT = """You are an expert academic research analyst.
You are reading a CHUNK of a research paper. Extract the following from this chunk only:
- Key concepts or arguments introduced
- Any methodologies described
- Any findings or results mentioned
- Important quotes or definitions

Be concise. Use bullet points. Only report what is explicitly in this chunk."""

REDUCE_SYSTEM_PROMPT = """You are a senior academic editor who synthesises research analysis.
You will receive multiple partial analyses of different sections of the same research paper.
Synthesise them into a single, coherent report with the following structure:

---
## Executive Summary
[3–5 sentence high-level overview of the paper's purpose, approach, and significance]

## Key Methodologies
[Bullet list of the research methods, tools, datasets, or frameworks used]

## Primary Findings & Conclusions
[Bullet list of the most important results, insights, and conclusions]

## Limitations & Future Work
[Brief note on limitations acknowledged or future directions suggested, if mentioned]
---

Write for an expert audience. Be precise and informative."""


def summarise_paper(
    llm: BaseChatModel,
    paper_text: str,
    chunk_size: int = 2000,
    chunk_overlap: int = 200,
) -> str:
    """
    Summarise a research paper using a map-reduce strategy.

    Map phase:  Each chunk is independently summarised.
    Reduce phase: All partial summaries are merged into a final structured report.
    """
    if not llm:
         return "Summarisation failed: AI model is not ready. Have you provided an API key?"

    chunks = chunk_text(paper_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    logger.info("Summarising paper in %d chunks (map phase)...", len(chunks))

    # --- MAP phase: summarise each chunk independently ---
    partial_summaries: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        logger.debug("Processing chunk %d / %d", i, len(chunks))
        summary = _invoke_llm(
            llm,
            MAP_SYSTEM_PROMPT,
            f"[CHUNK {i} of {len(chunks)}]\n\n{chunk}",
        )
        partial_summaries.append(f"### Chunk {i} Analysis\n{summary}")

    # --- REDUCE phase: merge all partial summaries ---
    combined = "\n\n".join(partial_summaries)
    logger.info("Merging partial summaries (reduce phase)...")
    final_summary = _invoke_llm(
        llm,
        REDUCE_SYSTEM_PROMPT,
        f"Here are the partial analyses from all sections of the paper:\n\n{combined}",
    )

    return final_summary

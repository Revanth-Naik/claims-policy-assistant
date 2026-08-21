"""
Provider-switchable chat model. Reads LLM_PROVIDER (+ the matching API key)
from the environment / .env file and returns a LangChain chat model, so the
rest of the app (app/streamlit_app.py) doesn't care whether it's talking to
Anthropic, OpenAI, xAI (Grok), or Groq.
"""
import os

from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a claims and benefits assistant for Meridian Health \
Plan (a fictional health plan used for this demo). Answer the member's or \
provider's question using ONLY the context provided below -- a mix of plan \
policy documents and, when relevant, the specific claim or member record \
pulled from the claims warehouse.

Rules:
- If the context includes a specific claim record, ground your answer in its \
  actual fields (status, denial reason, amounts) rather than speaking generally.
- If the context does not contain enough information to answer confidently, \
  say so plainly rather than guessing.
- Keep answers concise and reference which plan or policy the answer applies \
  to when it's plan-specific (benefits differ by Bronze/Silver/Gold/Platinum).
"""


def get_llm(temperature: float = 0.1):
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set in .env")
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        return ChatAnthropic(model=model, api_key=api_key, temperature=temperature)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set in .env")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, api_key=api_key, temperature=temperature)

    if provider == "xai":
        # xAI's Grok API is OpenAI-compatible, so the same ChatOpenAI client
        # works -- it just points at xAI's base URL instead of OpenAI's.
        # Docs: https://docs.x.ai/developers/quickstart
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=xai but XAI_API_KEY is not set in .env")
        model = os.getenv("XAI_MODEL", "grok-4.6")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://api.x.ai/v1",
            temperature=temperature,
        )

    if provider == "groq":
        # Groq (api.groq.com) is a different company from xAI's Grok -- easy
        # mix-up given the names. Also OpenAI-compatible, so same ChatOpenAI
        # client, different base URL. Docs: https://console.groq.com/docs/models
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=groq but GROQ_API_KEY is not set in .env")
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temperature,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}' -- expected 'anthropic', 'openai', 'xai', or 'groq'"
    )


def build_prompt(question: str, structured_context: str | None, policy_context: str) -> str:
    parts = []
    if structured_context:
        parts.append(f"CLAIM / MEMBER RECORD(S) FROM THE WAREHOUSE:\n{structured_context}")
    parts.append(f"RELEVANT POLICY DOCUMENT EXCERPTS:\n{policy_context}")
    parts.append(f"QUESTION:\n{question}")
    return "\n\n---\n\n".join(parts)

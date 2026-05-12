import os
import time
from typing import Any, Callable, Optional
from src.config.logging_config import setup_logging

logger = setup_logging()


class LLMConfigurationError(RuntimeError):
    """Raised when an LLM client is missing required configuration."""


class LLMResponseError(RuntimeError):
    """Raised when an LLM provider returns an unusable response."""


class LLMRateLimitError(RuntimeError):
    """Raised when an LLM provider reports a quota or rate-limit failure."""

class LLMClient:
    """LLM client wrapper with retry logic."""

    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.temperature = 0.1
        self.max_retries = 3
        if provider == "openai":
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.client = OpenAI(api_key=api_key)
            self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response from LLM."""
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response.choices[0].message.content
            except Exception as e:
                wait = 2 ** attempt
                logger.warning(f"LLM attempt {attempt + 1} failed: {e}. Retry in {wait}s")
                if attempt < self.max_retries - 1:
                    time.sleep(wait)
                else:
                    raise
        return ""


class GeminiClient:
    """Google Gemini client with lazy imports, retries, and clear errors."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        max_retries: int = 3,
        timeout_seconds: int = 60,
        model: Optional[Any] = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self._model = model
        self._sleep = sleep

    def generate(self, prompt: str) -> str:
        model = self._model or self._build_model()
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = model.generate_content(
                    prompt,
                    request_options={"timeout": self.timeout_seconds},
                )
                text = getattr(response, "text", None)
                if not text or not text.strip():
                    raise LLMResponseError("Gemini returned an empty response")
                return text.strip()
            except LLMResponseError:
                raise
            except Exception as exc:
                last_error = exc
                if self._is_rate_limit(exc):
                    raise LLMRateLimitError(f"Gemini quota or rate limit error: {exc}") from exc
                if attempt < self.max_retries - 1:
                    self._sleep(2 ** attempt)
                else:
                    raise LLMResponseError(f"Gemini generation failed: {exc}") from exc
        raise LLMResponseError(f"Gemini generation failed: {last_error}")

    def _build_model(self):
        if not self.api_key:
            raise LLMConfigurationError(
                "GEMINI_API_KEY is not set. Add it to .env or pass api_key explicitly."
            )
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise LLMConfigurationError(
                "google-genai is required for Gemini. Install dependencies from requirements.txt."
            ) from exc

        try:
            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                temperature=self.temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
            )
            self._model = _GoogleGenAIModel(
                client=client,
                model_name=self.model_name,
                config=config,
            )
            return self._model
        except Exception as exc:
            raise LLMConfigurationError(
                f"Failed to initialize Gemini client. Check API key validity: {exc}"
            ) from exc

    @staticmethod
    def _is_rate_limit(exc: Exception) -> bool:
        code = getattr(exc, "code", None)
        if code == 429:
            return True
        message = str(exc).lower()
        return any(token in message for token in ["quota", "rate limit", "429", "resource exhausted"])


class _GoogleGenAIModel:
    """Small adapter so tests can still inject simple generate_content fakes."""

    def __init__(self, client: Any, model_name: str, config: Any):
        self.client = client
        self.model_name = model_name
        self.config = config

    def generate_content(self, prompt: str, request_options: Optional[dict] = None):
        return self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=self.config,
        )


AAOIFI_ADHERENCE_SYSTEM_PROMPT = """You are a Sharia compliance analyzer specializing in AAOIFI Financial Accounting Standards (FAS).

STRICT INSTRUCTIONS:
- Base ALL rulings ONLY on the provided AAOIFI FAS standards context.
- Every ruling MUST include citations with standard number and section.
- Format citations as: [AAOIFI FAS X, Section Y].
- If context is insufficient, state: "INSUFFICIENT_STANDARDS: [what is missing]".
- Do NOT use external knowledge not in the provided context.
- Do NOT provide generic Islamic finance advice without citing specific standards.

RESPONSE STRUCTURE:
1. COMPLIANCE STATUS: [COMPLIANT / NON_COMPLIANT / PARTIALLY_COMPLIANT]
2. REASONING: [detailed explanation with citations]
3. CITATIONS: [list all AAOIFI standards used]
4. RECOMMENDATIONS: [actionable recommendations]
5. WARNINGS: [any caveats or limitations]

PROHIBITED BEHAVIORS:
- Do not answer without citing AAOIFI standards.
- Do not make up standard numbers or sections.
- Do not provide legal advice beyond AAOIFI FAS scope.
"""

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

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate response from LLM."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=messages,
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


class OpenRouterClient:
    """OpenRouter client using OpenAI-compatible API with retries and clear errors."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        max_retries: int = 3,
        timeout_seconds: int = 60,
        max_tokens: Optional[int] = None,
        client: Optional[Any] = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model_name = model_name or os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens if max_tokens is not None else int(os.getenv("OPENROUTER_MAX_TOKENS", "1024"))
        self._client = client
        self._sleep = sleep

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response.

        Args:
            prompt: The user message content (must be text only).
            system_prompt: Optional system-role instructions sent as a separate
                message before the user turn for better instruction following.
        """
        client = self._client or self._build_client()
        last_error = None
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": str(system_prompt)})
        messages.append({"role": "user", "content": str(prompt)})
        for attempt in range(self.max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout_seconds,
                )
                text = response.choices[0].message.content
                if not text or not text.strip():
                    raise LLMResponseError("OpenRouter returned an empty response")
                return text.strip()
            except LLMResponseError:
                raise
            except Exception as exc:
                last_error = exc
                error_str = str(exc).lower()
                if self._is_rate_limit(exc):
                    raise LLMRateLimitError(f"OpenRouter quota or rate limit error: {exc}") from exc
                if "image" in error_str and "does not support" in error_str:
                    raise LLMResponseError(
                        f"OpenRouter rejected request with image-related error. "
                        f"This usually means the prompt contains non-text content. "
                        f"Verify the query is plain text. Original error: {exc}"
                    ) from exc
                if attempt < self.max_retries - 1:
                    self._sleep(2 ** attempt)
                else:
                    raise LLMResponseError(f"OpenRouter generation failed: {exc}") from exc
        raise LLMResponseError(f"OpenRouter generation failed: {last_error}")

    def _build_client(self):
        if not self.api_key:
            raise LLMConfigurationError(
                "OPENROUTER_API_KEY is not set. Add it to .env or pass api_key explicitly."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMConfigurationError(
                "openai is required for OpenRouter. Install dependencies from requirements.txt."
            ) from exc

        try:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            return self._client
        except Exception as exc:
            raise LLMConfigurationError(
                f"Failed to initialize OpenRouter client. Check API key validity: {exc}"
            ) from exc

    @staticmethod
    def _is_rate_limit(exc: Exception) -> bool:
        code = getattr(exc, "code", None)
        if code == 429:
            return True
        if code == 402:
            return True
        message = str(exc).lower()
        return any(
            token in message
            for token in [
                "quota",
                "rate limit",
                "429",
                "402",
                "payment required",
                "insufficient credits",
                "resource exhausted",
            ]
        )


# Backward compatibility alias
GeminiClient = OpenRouterClient


class MockLLM:
    """Deterministic LLM stub for testing.

    Accepts a pre-defined list of responses and an optional list of per-call
    delays (seconds). Responses can be strings (returned as-is) or Exception
    instances (raised on call) to simulate failure modes such as HTTPError(429),
    HTTPError(502), or TimeoutError.

    Implements the same ``generate(prompt, system_prompt)`` interface as
    ``OpenRouterClient`` so it can be injected via ``app.dependency_overrides``
    or passed directly to ``ApplicationService(llm_client=...)``.
    """

    def __init__(
        self,
        responses: list[str | Exception],
        delays: list[float] | None = None,
    ):
        self._responses = list(responses)
        self._delays = delays if delays is not None else [0.0] * len(responses)
        self.call_count = 0
        self.last_prompt: str | None = None
        self.last_system_prompt: str | None = None

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return the next pre-configured response or raise the next exception.

        Mirrors ``OpenRouterClient.generate()`` signature so the same caller
        code path is exercised.
        """
        import time

        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        idx = self.call_count
        self.call_count += 1

        # Apply delay if configured for this call index
        if idx < len(self._delays) and self._delays[idx] > 0:
            time.sleep(self._delays[idx])

        if idx >= len(self._responses):
            from src.chatbot.llm_client import LLMResponseError

            raise LLMResponseError(
                f"MockLLM: no more responses configured (call #{idx}, "
                f"{len(self._responses)} configured)"
            )

        response = self._responses[idx]
        if isinstance(response, Exception):
            raise response

        return str(response)

    @property
    def model_name(self) -> str:
        """Return a stable identifier so ``ApplicationService`` metadata works."""
        return "mock-llm"

    def reset(self) -> None:
        """Reset call tracking for test isolation."""
        self.call_count = 0
        self.last_prompt = None
        self.last_system_prompt = None


"""Generates answers using LLM with prompt building."""
from typing import Any, Dict, List, Optional
from inspect import Parameter, signature


class AnswerGenerator:
    """Coordinates LLM generation with prompt building."""

    def __init__(self, llm_client, prompt_builder):
        """Initialize answer generator.
        
        Args:
            llm_client: LLM client for generation
            prompt_builder: Prompt builder for constructing prompts
        """
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder

    def generate(
        self,
        query: str,
        chunks: List[Any],
        history: Optional[List[Dict[str, str]]] = None,
        response_language: str = "en",
    ) -> str:
        """Generate answer from query and retrieved chunks.
        
        Args:
            query: User query
            chunks: Retrieved chunks
            history: Conversation history
            response_language: Language for response (en or ar)
            
        Returns:
            Generated answer text
        """
        # Build prompt using appropriate method
        if hasattr(self.prompt_builder, 'build_messages'):
            system_prompt, user_prompt = self.prompt_builder.build_messages(
                query,
                chunks,
                history=history,
                response_language=response_language,
            )
            return self.llm_client.generate(user_prompt, system_prompt=system_prompt)
        else:
            prompt = self._build_prompt(query, chunks, history, response_language)
            return self.llm_client.generate(prompt)

    def _build_prompt(
        self,
        query: str,
        chunks: List[Any],
        history: Optional[List[Dict[str, str]]],
        response_language: str,
    ) -> str:
        """Build a single-string prompt for legacy prompt builders."""
        build_signature = signature(self.prompt_builder.build)
        params = build_signature.parameters
        accepts_kwargs = any(param.kind == Parameter.VAR_KEYWORD for param in params.values())
        
        kwargs = {"history": history, "response_language": response_language}
        supported_kwargs = {
            key: value
            for key, value in kwargs.items()
            if accepts_kwargs or key in params
        }
        
        return self.prompt_builder.build(query, chunks, **supported_kwargs)

"""Built-in LLM providers.

Each provider lazily imports its LangChain integration so only the packages
for the provider you actually use need to be installed.  Adding a new
back-end (say, a local Ollama server) is just another class with the
``@register_provider`` decorator — no other file changes.
"""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from deep_agent.llm.base import LLMParams, LLMProviderSpec
from deep_agent.llm.registry import register_provider


@register_provider
class OpenAIProvider(LLMProviderSpec):
    name = "openai"
    settings_key = "openai_api_key"
    env_key = "OPENAI_API_KEY"
    package = "langchain-openai"
    default_model = "gpt-4o"

    def build(self, settings, params: LLMParams) -> BaseChatModel:
        from langchain_openai import ChatOpenAI

        kwargs: dict = dict(
            model=params.model,
            temperature=params.temperature,
            api_key=self.get_api_key(settings),
            timeout=params.timeout,
            max_retries=params.max_retries,
        )
        if params.max_tokens is not None:
            kwargs["max_tokens"] = params.max_tokens
        if params.seed is not None:
            kwargs["seed"] = params.seed
        return ChatOpenAI(**kwargs)


@register_provider
class AnthropicProvider(LLMProviderSpec):
    name = "anthropic"
    settings_key = "anthropic_api_key"
    env_key = "ANTHROPIC_API_KEY"
    package = "langchain-anthropic"
    default_model = "claude-3-5-sonnet-latest"

    def build(self, settings, params: LLMParams) -> BaseChatModel:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=params.model,
            temperature=params.temperature,
            api_key=self.get_api_key(settings),
            timeout=params.timeout,
            max_retries=params.max_retries,
            # Anthropic requires an explicit max_tokens; default when unset.
            max_tokens=params.max_tokens or 4096,
        )


@register_provider
class GoogleProvider(LLMProviderSpec):
    name = "google"
    settings_key = "google_api_key"
    env_key = "GOOGLE_API_KEY"
    package = "langchain-google-genai"
    default_model = "gemini-1.5-pro"

    def build(self, settings, params: LLMParams) -> BaseChatModel:
        from langchain_google_genai import ChatGoogleGenerativeAI

        kwargs: dict = dict(
            model=params.model,
            temperature=params.temperature,
            google_api_key=self.get_api_key(settings),
            timeout=params.timeout,
            max_retries=params.max_retries,
        )
        if params.max_tokens is not None:
            kwargs["max_output_tokens"] = params.max_tokens
        return ChatGoogleGenerativeAI(**kwargs)

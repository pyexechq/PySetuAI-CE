from app.modules.uag.translators.azure_openai import AzureOpenAITranslator
from app.modules.uag.translators.claude import ClaudeTranslator
from app.modules.uag.translators.gemini import GeminiTranslator
from app.modules.uag.translators.openai import OpenAITranslator

TRANSLATORS = {
    "openai": OpenAITranslator(),
    "azure_openai": AzureOpenAITranslator(),
    "gemini": GeminiTranslator(),
    "anthropic": ClaudeTranslator(),
    "claude": ClaudeTranslator(),
    "openai-compatible": OpenAITranslator(),
}


def get_translator(protocol: str):
    return TRANSLATORS.get(protocol.strip().lower(), OpenAITranslator())

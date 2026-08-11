from app.modules.uag.translators.base import OpenAICompatibleTranslator


class OpenAITranslator(OpenAICompatibleTranslator):
    protocol = "openai"

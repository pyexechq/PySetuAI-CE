from app.modules.uag.translators.base import OpenAICompatibleTranslator


class AzureOpenAITranslator(OpenAICompatibleTranslator):
    protocol = "azure_openai"

    def translate_to_upstream(self, canonical):
        payload = super().translate_to_upstream(canonical)
        payload["azure_deployment"] = canonical.model
        return payload

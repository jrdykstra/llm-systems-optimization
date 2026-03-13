import time
from openai import OpenAI
from src.models.base import Model, ModelResult
from dotenv import load_dotenv


load_dotenv()

class OpenAIModel(Model):

    def __init__(self, model_name: str):
        self.name = model_name
        self.client = OpenAI()

    def generate(self, prompt: str) -> ModelResult:

        start = time.time()

        response = self.client.chat.completions.create(
            model=self.name,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        latency_ms = (time.time() - start) * 1000

        output_text = response.choices[0].message.content

        usage = response.usage

        return ModelResult(
            output_text=output_text,
            latency_ms=latency_ms,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            cost_usd=None,
        )
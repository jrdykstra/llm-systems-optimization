import time
from huggingface_hub import InferenceClient
from src.models.base import Model, ModelResult
from dotenv import load_dotenv
import os

load_dotenv()


class HFModel(Model):

    def __init__(self, model_name: str):
        self.name = model_name
        self.client = InferenceClient(
            model=model_name,
            token=os.getenv("HUGGINGFACE_API_KEY"),
        )

    def generate(self, prompt: str) -> ModelResult:
        start = time.time()

        response = self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )

        latency_ms = (time.time() - start) * 1000

        output_text = response.choices[0].message.content
        usage = response.usage

        return ModelResult(
            output_text=output_text,
            latency_ms=latency_ms,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            cost_usd=0.0,  # Free tier
        )

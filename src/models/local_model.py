import time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from src.models.base import Model, ModelResult


class LocalModel(Model):

    def __init__(self, model_name: str):
        self.name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
        )

    def generate(self, prompt: str) -> ModelResult:
        start = time.time()

        input_ids = self.tokenizer.encode(prompt, return_tensors="pt")
        input_tokens = input_ids.shape[1]

        messages = [{"role": "user", "content": prompt}]
        result = self.pipe(
            messages,
            max_new_tokens=512,
            do_sample=False,
        )

        output_text = result[0]["generated_text"][-1]["content"]
        output_tokens = len(self.tokenizer.encode(output_text))

        latency_ms = (time.time() - start) * 1000

        return ModelResult(
            output_text=output_text,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
        )

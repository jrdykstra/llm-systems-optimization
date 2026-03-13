from dataclasses import dataclass


@dataclass
class ModelResult:
    output_text: str
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None


class Model:
    name: str

    def generate(self, prompt: str) -> ModelResult:
        raise NotImplementedError
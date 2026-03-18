import json
import argparse
from pathlib import Path

from src.models.openai_model import OpenAIModel
from src.models.local_model import LocalModel


DATASET_PATH = Path("datasets/router_v1/tasks.jsonl")
RUNS_DIR = Path("runs")

PROMPT_VERSION = "v2"
PROMPT_PATH = Path(f"prompts/extraction_{PROMPT_VERSION}.txt")


def load_tasks(path: Path):
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            tasks.append(json.loads(line))
    return tasks


def build_prompt(task) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{input}", task["input"].strip())


def select_model(provider: str, model_name: str):

    if provider == "openai":
        return OpenAIModel(model_name)

    if provider == "local":
        return LocalModel(model_name)

    raise ValueError(f"Unsupported provider: {provider}")


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)

    args = parser.parse_args()

    tasks = load_tasks(DATASET_PATH)

    model = select_model(args.provider, args.model)

    output_path = RUNS_DIR / f"{model.name}_predictions.jsonl"

    with open(output_path, "w", encoding="utf-8") as out:

        for i, task in enumerate(tasks, start=1):
            print(f"[{i}/{len(tasks)}] running {task['id']}")
            prompt = build_prompt(task)
            result = model.generate(prompt)

            row = {
                "id": task["id"],
                "model": model.name,
                "prompt_version": PROMPT_VERSION,
                "output_text": result.output_text,
                "latency_ms": result.latency_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
            }

            out.write(json.dumps(row) + "\n")

    print(f"Predictions written to {output_path}")


if __name__ == "__main__":
    main()
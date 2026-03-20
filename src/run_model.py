import json
import argparse
from pathlib import Path

from src.models.openai_model import OpenAIModel
from src.models.local_model import LocalModel
from src.models.hf_model import HFModel


RUNS_DIR = Path("runs")


def load_tasks(path):
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tasks.append(json.loads(line))
    return tasks


def build_prompt(task, prompt_path):
    template = prompt_path.read_text(encoding="utf-8")
    return template.replace("{input}", task["input"].strip())


def select_model(provider, model_name):
    if provider == "openai":
        return OpenAIModel(model_name)
    if provider == "local":
        return LocalModel(model_name)
    if provider == "huggingface":
        return HFModel(model_name)
    raise ValueError(f"Unsupported provider: {provider}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--task-type", default="extraction_v1",
                        choices=["extraction_v1", "antitrust_v1"])
    args = parser.parse_args()

    dataset_path = Path(f"datasets/{args.task_type}/tasks.jsonl")
    prompt_path = Path(f"prompts/{args.task_type.split('_')[0]}.txt")

    tasks = load_tasks(dataset_path)
    model = select_model(args.provider, args.model)

    safe_name = model.name.replace("/", "_")
    output_path = RUNS_DIR / f"{safe_name}_{args.task_type}_predictions.jsonl"

    with open(output_path, "w", encoding="utf-8") as out:
        for i, task in enumerate(tasks, start=1):
            print(f"[{i}/{len(tasks)}] running {task['id']}")
            prompt = build_prompt(task, prompt_path)
            result = model.generate(prompt)

            row = {
                "id": task["id"],
                "model": model.name,
                "task_type": args.task_type,
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

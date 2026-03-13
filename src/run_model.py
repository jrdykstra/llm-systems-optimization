import json
import argparse
from pathlib import Path

from src.models.openai_model import OpenAIModel
from src.models.local_model import LocalModel


DATASET_PATH = Path("datasets/router_v1/tasks.jsonl")
RUNS_DIR = Path("runs")


def load_tasks(path: Path):
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            tasks.append(json.loads(line))
    return tasks


def build_prompt(task: dict) -> str:
    input_text = task["input"].strip()

    return f"""Extract structured data from the input text and return a single JSON object. No markdown, no explanation — raw JSON only.

    Field rules:
    - primary_entity: string — the main subject (see role rules below)
    - primary_entity_type: one of exactly: company | agency | individual
    - secondary_entity: string or null
    - action_type: one of exactly: acquisition | fine | lawsuit | partnership | investigation
    - amount_usd: number (integer) or null — convert "$1.2 billion" -> 1200000000, "$520 million" -> 520000000
    - date: string in YYYY-MM-DD format or null — "December 2022" -> "2022-12-01", "in 2023" -> "2023-01-01"
    - jurisdiction: one of exactly: US | EU | UK | Other | null

    Role rules (which entity is primary vs secondary):
    - acquisition: primary = acquirer, secondary = target
    - fine: primary = entity fined, secondary = entity imposing fine
    - lawsuit: primary = plaintiff/filer, secondary = defendant
    - partnership: primary = first-named entity, secondary = second-named entity
    - investigation: primary = entity under investigation, secondary = investigating body

    Input: {input_text}"""

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
                "prompt_version": "v1",
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
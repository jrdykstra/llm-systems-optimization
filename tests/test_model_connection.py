import os
import pytest
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _get_api_key():
    return os.getenv("OPENAI_API_KEY")


@pytest.mark.skipif(_get_api_key() is None, reason="OPENAI_API_KEY not set")
def test_openai_connection():

    client = OpenAI()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Reply with the word ok"}],
        max_tokens=5,
    )

    text = resp.choices[0].message.content

    assert isinstance(text, str)
    assert len(text) > 0
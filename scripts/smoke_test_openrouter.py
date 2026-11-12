"""Optional live smoke check for the shared OpenRouter client.

Run with `uv run python -m scripts.smoke_test_openrouter`. This makes two
model calls: a plain-text generation and a structured TableData generation.
"""

import os

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit("Set OPENROUTER_API_KEY in the environment or .env file first.")

    from graphs.llm import llm
    from graphs.models import TableData

    plain_response = llm.invoke("Reply with exactly: OpenRouter smoke test passed.")
    print("Plain-text response:")
    print(plain_response.content)

    table = llm.with_structured_output(TableData).invoke(
        "Create a tiny Spanish noun table showing singular and plural forms of 'gato'."
    )
    print("Structured TableData response:")
    print(table.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

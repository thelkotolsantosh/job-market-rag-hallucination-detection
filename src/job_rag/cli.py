"""Ask the RAG system from the terminal without running the API."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .rag import answer
from .store import connect, search_jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask questions about supplied job CSV files")
    parser.add_argument("--question", required=True)
    parser.add_argument("--mode", choices=["guarded", "baseline", "ollama"], default="guarded")
    parser.add_argument("--db", type=Path, default=Path("data/processed/jobs.sqlite"))
    args = parser.parse_args()
    with connect(args.db) as con:
        print(json.dumps(answer(con, args.question, mode=args.mode), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

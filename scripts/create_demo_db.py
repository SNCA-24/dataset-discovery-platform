from __future__ import annotations

import argparse
from pathlib import Path

from scripts.demo_data import build_demo_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a small local demo DB for V2.")
    parser.add_argument(
        "--db-path",
        default="data/demo_discovery.duckdb",
        help="Output DuckDB path for the seeded local demo catalog.",
    )
    parser.add_argument(
        "--fixture-path",
        default="tests/fixtures/demo_catalog.json",
        help="JSON fixture describing demo datasets and artifacts.",
    )
    args = parser.parse_args()

    db_path = build_demo_db(args.db_path, args.fixture_path)
    print(f"Created demo DB at {Path(db_path)}")


if __name__ == "__main__":
    main()

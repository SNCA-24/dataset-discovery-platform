from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the V2 API against the configured DuckDB path.")
    parser.add_argument("--host", default=os.getenv("API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "8000")))
    args = parser.parse_args()
    uvicorn.run("V2.api.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()

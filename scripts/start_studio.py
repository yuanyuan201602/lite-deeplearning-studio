from __future__ import annotations

import argparse
import os

import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start Lite DeepLearning Studio locally.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host, default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="Bind port, default: 8000")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload on code changes. Useful for development installs.",
    )
    parser.add_argument(
        "--edition",
        choices=["all", "smart_museum", "future_creator"],
        default=os.environ.get("LDS_EDITION", "all"),
        help="App edition to show: all, smart_museum, or future_creator.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["LDS_EDITION"] = args.edition
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import os
import threading
import webbrowser

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
        "--open",
        action="store_true",
        help="Open the browser automatically after the server starts.",
    )
    parser.add_argument(
        "--edition",
        choices=["all", "smart_museum", "future_creator"],
        default=os.environ.get("LDS_EDITION", "all"),
        help="App edition to show: all, smart_museum, or future_creator.",
    )
    return parser.parse_args()


def open_browser_later(url: str, delay_seconds: float = 1.5) -> None:
    timer = threading.Timer(delay_seconds, webbrowser.open, args=(url,))
    timer.daemon = True
    timer.start()


def main() -> None:
    args = parse_args()
    os.environ["LDS_EDITION"] = args.edition
    if args.open and not args.reload:
        browse_host = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
        open_browser_later(f"http://{browse_host}:{args.port}")
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

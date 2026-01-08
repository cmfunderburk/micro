"""Entry point for running the server.

Usage:
    python -m server
    python -m server --port 8000
"""

import argparse

import uvicorn

from server.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Microecon simulation backend")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    app = create_app()
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

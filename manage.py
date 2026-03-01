#!/usr/bin/env python3
"""Script de administración para la webapp."""

from __future__ import annotations

import argparse

from app import app


def runserver(host: str, port: int, debug: bool) -> None:
    app.run(host=host, port=port, debug=debug)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Herramienta de administración")
    subparsers = parser.add_subparsers(dest="command", required=True)

    runserver_parser = subparsers.add_parser(
        "runserver", help="Levanta el servidor Flask"
    )
    runserver_parser.add_argument("--host", default="127.0.0.1")
    runserver_parser.add_argument("--port", type=int, default=5000)
    runserver_parser.add_argument("--debug", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "runserver":
        runserver(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()

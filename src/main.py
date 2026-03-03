from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from yalex_parser import parse_yalex


def run() -> None:
    parser = argparse.ArgumentParser(description="Parser básico para archivos YALex")
    parser.add_argument("input", type=Path, help="Ruta al archivo .yal")
    args = parser.parse_args()

    source = args.input.read_text(encoding="utf-8")
    spec = parse_yalex(source)

    print(json.dumps(asdict(spec), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()

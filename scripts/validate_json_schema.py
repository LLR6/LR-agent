import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a JSON artifact against a Draft 2020-12 schema")
    parser.add_argument("schema", type=Path)
    parser.add_argument("document", type=Path)
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    document = json.loads(args.document.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        for error in errors:
            path = ".".join(str(x) for x in error.absolute_path) or "$"
            print(f"{path}: {error.message}")
        return 2
    print(f"schema validation passed: {args.document} -> {args.schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

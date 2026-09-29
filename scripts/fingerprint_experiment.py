import argparse
import json
from pathlib import Path

from lr_agent.research_artifacts import build_artifact_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Fingerprint an LR-Agent research manifest and its retained artifacts")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--artifact", action="append", default=[], type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        bundle = build_artifact_bundle(manifest, args.artifact)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    text = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

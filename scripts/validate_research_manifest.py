import argparse
import json
from pathlib import Path

from lr_agent.research_manifest import ResearchManifestError, validate_research_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an LR-Agent research-run manifest")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate_research_manifest(data)
    except (OSError, json.JSONDecodeError, ResearchManifestError) as exc:
        parser.error(str(exc))
    print(f"valid research manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import re
from pathlib import Path


def project_version() -> str:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    in_project = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_project = line == "[project]"
            continue
        if in_project:
            match = re.match(r'version\s*=\s*"([^"]+)"', line)
            if match:
                return match.group(1)
    raise SystemExit("could not find [project].version in pyproject.toml")


def citation_version() -> str:
    text = Path("CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version:\s*["\']?([^"\'\n]+)["\']?\s*$', text)
    if not match:
        raise SystemExit("could not find version in CITATION.cff")
    return match.group(1).strip()


def changelog_contains(version: str) -> bool:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")
    return bool(re.search(rf"(?m)^##\s+{re.escape(version)}(?:\s+-|\s*$)", text))


def main() -> int:
    package = project_version()
    citation = citation_version()
    errors = []
    if citation != package:
        errors.append(f"CITATION.cff version {citation!r} != package version {package!r}")
    if not changelog_contains(package):
        errors.append(f"CHANGELOG.md has no release heading for {package}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 2
    print(f"release metadata consistent: {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


LINK_RE = re.compile(
    r'!?\[[^\]]*\]\(([^)]+)\)|(?:href|src)=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "android"}


def markdown_files(root: Path):
    for path in root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def clean_destination(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()
    if " " in value and not value.startswith(("http://", "https://")):
        value = value.split(" ", 1)[0]
    return value


def local_target(root: Path, source: Path, destination: str) -> Path | None:
    if not destination or destination.startswith("#"):
        return None
    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc:
        return None
    path_text = unquote(parsed.path)
    if not path_text:
        return None
    if path_text.startswith("/"):
        return root / path_text.lstrip("/")
    return source.parent / path_text


def main() -> int:
    root = Path(".").resolve()
    failures: list[str] = []
    checked = 0

    for source in markdown_files(root):
        text = source.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            raw = match.group(1) or match.group(2) or ""
            destination = clean_destination(raw)
            target = local_target(root, source, destination)
            if target is None:
                continue
            checked += 1
            if not target.exists():
                failures.append(
                    f"{source.relative_to(root)}: {destination} -> missing {target.relative_to(root) if target.is_relative_to(root) else target}"
                )

    if failures:
        print(f"broken local links: {len(failures)}")
        for failure in failures:
            print(f"- {failure}")
        return 2

    print(f"local Markdown links OK: {checked} checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

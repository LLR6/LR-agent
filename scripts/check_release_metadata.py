import re
from pathlib import Path


def first(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, re.M)
    if not match:
        raise SystemExit(f"missing {label}")
    return match.group(1)


pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
citation = Path("CITATION.cff").read_text(encoding="utf-8")
changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

package_version = first(r'^version\s*=\s*"([^"]+)"', pyproject, "pyproject version")
citation_version = first(r'^version:\s*"?([^"\n]+)"?\s*$', citation, "CITATION version").strip()
released_versions = re.findall(r"^##\s+(\d+\.\d+\.\d+)\b", changelog, re.M)
if not released_versions:
    raise SystemExit("CHANGELOG has no released semantic version")
changelog_version = released_versions[0]

if package_version != citation_version:
    raise SystemExit(f"version mismatch: pyproject={package_version} citation={citation_version}")
if package_version != changelog_version:
    raise SystemExit(f"version mismatch: pyproject={package_version} changelog={changelog_version}")

print(f"release metadata consistent: {package_version}")

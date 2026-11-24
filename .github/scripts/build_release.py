"""Build the add-on zip and release notes for a GitHub release.

The version comes from bl_info in __init__.py, and the tag name and release
notes come from the matching "## YYYYMMDD-<version>" section in CHANGELOG.md.
"""

import argparse
import ast
import os
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "livelinkface_arkit_receiver"

# Only the files Blender needs, plus the license required by GPL-3.0.
ADDON_FILES = ("__init__.py", "LICENSE")


def read_bl_info():
    tree = ast.parse((REPO_ROOT / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "bl_info" for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError("bl_info not found in __init__.py")


def read_changelog_section(version):
    lines = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.startswith("## ") and line[3:].strip().endswith(f"-{version}"):
            tag = line[3:].strip()
            body = []
            for next_line in lines[i + 1:]:
                if next_line.startswith("## "):
                    break
                body.append(next_line)
            return tag, "\n".join(body).strip() + "\n"
    raise RuntimeError(f'No "## YYYYMMDD-{version}" section found in CHANGELOG.md')


def build_zip(zip_path):
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ADDON_FILES:
            archive.write(REPO_ROOT / name, f"{ADDON_NAME}/{name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="dist", help="Output directory for the zip and notes")
    args = parser.parse_args()

    bl_info = read_bl_info()
    version = ".".join(str(part) for part in bl_info["version"])
    tag, notes = read_changelog_section(version)

    out_dir = Path(args.out_dir)
    zip_path = out_dir / f"{ADDON_NAME}-{version}.zip"
    notes_path = out_dir / "release_notes.md"

    build_zip(zip_path)
    notes_path.write_text(notes, encoding="utf-8")

    outputs = {
        "version": version,
        "tag": tag,
        "title": f"{bl_info['name']} {version}",
        "zip": zip_path.as_posix(),
        "notes": notes_path.as_posix(),
    }
    for key, value in outputs.items():
        print(f"{key}={value}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"::error::{e}", file=sys.stderr)
        sys.exit(1)

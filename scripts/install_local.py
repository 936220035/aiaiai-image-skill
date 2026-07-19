#!/usr/bin/env python3
"""Install the AIAIAI image skill for Codex and/or Claude Code."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path


SKILL_NAME = "aiaiai-image"
REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "skills" / SKILL_NAME
TARGET_ROOTS = {
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
}


def backup_existing(target: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = target.with_name(f"{target.name}.backup-{stamp}")
    target.rename(backup)
    return backup


def install_one(target_root: Path, mode: str, force: bool) -> dict[str, str]:
    target = target_root / SKILL_NAME
    result = {"path": str(target)}
    if target.exists() or target.is_symlink():
        if not force:
            result["status"] = "already-exists"
            return result
        result["backup"] = str(backup_existing(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    selected_mode = mode
    if mode == "auto":
        selected_mode = "copy" if os.name == "nt" else "symlink"
    if selected_mode == "symlink":
        target.symlink_to(SOURCE.resolve(), target_is_directory=True)
    else:
        shutil.copytree(SOURCE, target)
    result["status"] = selected_mode
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("codex", "claude", "both"), default="codex")
    parser.add_argument("--mode", choices=("auto", "copy", "symlink"), default="auto")
    parser.add_argument("--force", action="store_true", help="Back up and replace an existing installation.")
    parser.add_argument("--codex-skill-root", type=Path, default=TARGET_ROOTS["codex"])
    parser.add_argument("--claude-skill-root", type=Path, default=TARGET_ROOTS["claude"])
    args = parser.parse_args()
    if not (SOURCE / "SKILL.md").is_file():
        raise SystemExit(f"Skill source is missing: {SOURCE}")
    names = ["codex", "claude"] if args.target == "both" else [args.target]
    roots = {"codex": args.codex_skill_root, "claude": args.claude_skill_root}
    results = {name: install_one(roots[name], args.mode, args.force) for name in names}
    print(json.dumps({"installed": results, "restart_clients": names}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

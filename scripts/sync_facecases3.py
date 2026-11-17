#!/usr/bin/env python3
"""Stage shared facecases3 source clips used by comparison pages."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


DEFAULT_MANIFEST = Path("/keyan/Video_group/fq/workspace/facecases3/case_manifest.json")
DEFAULT_ORIGINAL_DIR = Path("/keyan/Video_group/fq/workspace/AgnesProdution/outputs/facecases3")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--original-dir", type=Path, default=DEFAULT_ORIGINAL_DIR)
    parser.add_argument("--site-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    cases = json.loads(args.manifest.read_text(encoding="utf-8"))["cases"]
    numbers = [int(case["case_number"]) for case in cases]
    if numbers != list(range(1, len(cases) + 1)):
        raise SystemExit("Expected case numbers in ascending order starting from 1")

    sources = []
    missing = []
    for case in cases:
        case_id = f"case_{int(case['case_number']):02d}"
        source = args.original_dir / f"{case['case_dir']}.mp4"
        if not source.is_file():
            missing.append(str(source))
        sources.append((case_id, source))
    if missing:
        raise SystemExit("Missing source videos:\n" + "\n".join(missing))

    output_dir = args.site_dir / "videos" / "facecases3" / "original"
    output_dir.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    for case_id, source in sources:
        destination = output_dir / f"{case_id}.mp4"
        shutil.copy2(source, destination)
        total_bytes += destination.stat().st_size

    print(f"Staged {len(sources)} shared original clips ({total_bytes / 1024 / 1024:.1f} MiB).")
    print(f"Assets: {output_dir}")


if __name__ == "__main__":
    main()

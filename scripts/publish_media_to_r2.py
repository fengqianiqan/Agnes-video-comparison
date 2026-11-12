#!/usr/bin/env python3
"""Upload staged site videos to Cloudflare R2 and publish their public URLs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from urllib.request import Request, urlopen
from pathlib import Path


DEFAULT_PUBLIC_BASE = "https://pub-88d378d7d6e94a07a7fc30386f6d9a71.r2.dev"
DEFAULT_REMOTE = "videos:videos/agnes-video-comparison"
SITE_DIR = Path(__file__).resolve().parents[1]


def iter_media_fields(data: dict):
    for case in data.get("cases", []):
        for field in ("original", "refined"):
            if case.get(field):
                yield case, field

    for material in data.get("sourceMaterials", []):
        if material.get("sourceVideo"):
            yield material, "sourceVideo"
        for reference in material.get("references", []):
            if reference.get("src"):
                yield reference, "src"
        for audio in material.get("audios", []):
            if audio.get("src"):
                yield audio, "src"


def find_rclone() -> str:
    configured = os.environ.get("RCLONE_BIN")
    candidates = [configured, shutil.which("rclone"), "/keyan/Video_group/fq/bin/rclone"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit("rclone not found; set RCLONE_BIN or install it on PATH")


def media_key(value: str, public_base: str) -> str:
    """Return the object key relative to the R2 site prefix."""
    prefix = public_base.rstrip("/") + "/agnes-video-comparison/"
    if value.startswith(prefix):
        return value[len(prefix):]
    if value.startswith("videos/"):
        return value.removeprefix("videos/")
    raise ValueError(f"Unsupported media path in manifest: {value}")


def verify_public_url(value: str) -> None:
    request = Request(
        value,
        headers={"Range": "bytes=0-0", "User-Agent": "Mozilla/5.0"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            if response.status not in (200, 206):
                raise SystemExit(f"Public media URL returned HTTP {response.status}: {value}")
            response.read(1)
    except Exception as error:
        raise SystemExit(f"Could not verify existing public media URL {value}: {error}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=SITE_DIR)
    parser.add_argument("--remote", default=DEFAULT_REMOTE, help="rclone destination")
    parser.add_argument("--public-base", default=DEFAULT_PUBLIC_BASE)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="publish only this manifest (relative to site root or an absolute path)",
    )
    args = parser.parse_args()

    site_dir = args.site_dir.resolve()
    video_dir = site_dir / "videos"
    manifest_dir = site_dir / "data"
    if args.manifest:
        selected_manifest = args.manifest
        if not selected_manifest.is_absolute():
            selected_manifest = site_dir / selected_manifest
        selected_manifest = selected_manifest.resolve()
        if selected_manifest.parent != manifest_dir.resolve() or not selected_manifest.is_file():
            raise SystemExit(f"Manifest must be an existing file under {manifest_dir}")
        manifests = [selected_manifest]
    else:
        manifests = sorted(manifest_dir.glob("*.json"))
    if not video_dir.is_dir() or not manifests:
        raise SystemExit("Expected videos/ and at least one data/*.json manifest")

    # Validate all manifest references before uploading or editing anything.
    references: set[str] = set()
    for manifest_path in manifests:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for owner, field in iter_media_fields(data):
            value = owner[field]
            key = media_key(value, args.public_base)
            if not (video_dir / key).is_file():
                public_prefix = args.public_base.rstrip("/") + "/agnes-video-comparison/"
                if not value.startswith(public_prefix):
                    raise SystemExit(f"Missing local media for {manifest_path.name}: videos/{key}")
                verify_public_url(value)
            else:
                references.add(key)

    rclone = find_rclone()
    subprocess.run(
        [rclone, "copy", str(video_dir), args.remote, "--transfers", "4", "--checkers", "8"],
        check=True,
    )
    subprocess.run(
        [rclone, "check", str(video_dir), args.remote, "--size-only", "--one-way"],
        check=True,
    )

    # Rewrite manifests only after the remote copy has been verified.
    public_base = args.public_base.rstrip("/")
    updated = 0
    for manifest_path in manifests:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        changed = False
        for owner, field in iter_media_fields(data):
            value = owner[field]
            key = media_key(value, public_base)
            public_url = f"{public_base}/agnes-video-comparison/{key}"
            if value != public_url:
                owner[field] = public_url
                changed = True
        if changed:
            manifest_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            updated += 1

    print(f"Verified R2 media for {len(references)} unique manifest assets.")
    print(f"Published public URLs in {updated} manifest(s).")


if __name__ == "__main__":
    main()

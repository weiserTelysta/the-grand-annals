"""Validate the Markdown-first authoring contract before MkDocs runs.

The public tree is intentionally simple: authors edit Markdown and front matter
in Obsidian, while presentation and generated navigation stay outside the notes.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


DOCS_DIR = Path("docs/zh")
FRONT_MATTER = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", re.DOTALL)
HEADING = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
MARKDOWN_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target><[^>]+>|[^\s)]+)(?:\s+['\"].*?['\"])?\)")
WIKILINK_IMAGE = re.compile(r"!\[\[[^\]]+\]\]")
WIKILINK = re.compile(r"(?<!!)\[\[[^\]]+\]\]")
ATTRIBUTE_ONLY = re.compile(r"(?m)^\s*\{\s*:?\s*\.[^}]+\}\s*$")
PRESENTATION_HTML = re.compile(r"(?mi)^\s*</?(?:div|span|section|article|nav|button)(?:\s|>)")
PUBLISHED_IMAGE_SUFFIXES = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
RESERVED_KEYS = {"status"}


def read_note(path: Path) -> tuple[dict[str, Any], str, str]:
    source = path.read_text(encoding="utf-8-sig")
    match = FRONT_MATTER.match(source)
    if not match:
        return {}, source, source
    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        return {"__yaml_error__": str(exc)}, source[match.end() :], source
    if not isinstance(metadata, dict):
        return {"__yaml_error__": "front matter must be a mapping"}, source[match.end() :], source
    return metadata, source[match.end() :], source


def normalize_lookup(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]" ):
        text = text[2:-2]
    return text.split("|", 1)[0].split("#", 1)[0].removesuffix(".md").strip("/").casefold()


def note_title(metadata: dict[str, Any], body: str, path: Path) -> str:
    if metadata.get("title"):
        return str(metadata["title"]).strip()
    match = HEADING.search(body)
    return match.group(1).strip() if match else path.stem


def resolve_related(value: Any, titles: dict[str, list[Path]], paths: dict[str, Path]) -> list[Path]:
    key = normalize_lookup(value)
    if key in titles:
        return titles[key]
    if key in paths:
        return [paths[key]]
    basename = PurePosixPath(key).name
    return [path for path_key, path in paths.items() if PurePosixPath(path_key).name == basename]


def resolve_image(note: Path, raw_target: str) -> Path | None:
    target = raw_target.strip("<>").split("#", 1)[0].replace("%20", " ")
    if not target or "://" in target or target.startswith(("data:", "mailto:")):
        return None
    return (note.parent / target).resolve()


def validate(docs_dir: Path) -> list[str]:
    errors: list[str] = []
    notes: dict[Path, tuple[dict[str, Any], str, str]] = {}
    titles: dict[str, list[Path]] = defaultdict(list)
    paths: dict[str, Path] = {}

    for path in sorted(docs_dir.rglob("*.md")):
        relative = path.relative_to(docs_dir).as_posix()
        metadata, body, source = read_note(path)
        notes[path] = (metadata, body, source)
        if "__yaml_error__" in metadata:
            errors.append(f"{relative}: invalid front matter ({metadata['__yaml_error__']})")
            continue
        title = note_title(metadata, body, path)
        titles[title.casefold()].append(path)
        paths[relative.removesuffix(".md").casefold()] = path

    for title, matched in titles.items():
        if len(matched) > 1:
            locations = ", ".join(path.relative_to(docs_dir).as_posix() for path in matched)
            errors.append(f"duplicate public title {title!r}: {locations}")

    for path, (metadata, body, source) in notes.items():
        relative = path.relative_to(docs_dir).as_posix()
        if "__yaml_error__" in metadata:
            continue
        if not metadata.get("title"):
            errors.append(f"{relative}: missing required front matter 'title'")
        if not str(metadata.get("description", "")).strip():
            errors.append(f"{relative}: missing required front matter 'description'")
        for key in RESERVED_KEYS & metadata.keys():
            errors.append(f"{relative}: reserved front matter key {key!r} is not allowed")
        if ATTRIBUTE_ONLY.search(source):
            errors.append(f"{relative}: presentation-only attribute syntax is not allowed")
        if PRESENTATION_HTML.search(source):
            errors.append(f"{relative}: presentation HTML is not allowed")
        if WIKILINK_IMAGE.search(source):
            errors.append(f"{relative}: embedded images must use Markdown links, not Obsidian embeds")
        if WIKILINK.search(body):
            errors.append(f"{relative}: body links must use portable Markdown links, not Obsidian wikilinks")

        related = metadata.get("related") or []
        if isinstance(related, str):
            related = [related]
        if not isinstance(related, list):
            errors.append(f"{relative}: 'related' must be a list")
            related = []
        seen_related: set[Path] = set()
        for value in related:
            matches = resolve_related(value, titles, paths)
            if not matches:
                errors.append(f"{relative}: unknown related entry {value!r}")
            elif len(matches) > 1:
                errors.append(f"{relative}: ambiguous related entry {value!r}")
            elif matches[0] == path:
                errors.append(f"{relative}: related entry cannot point to itself")
            elif matches[0] in seen_related:
                errors.append(f"{relative}: duplicate related entry {value!r}")
            else:
                seen_related.add(matches[0])

        aliases = metadata.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        if not isinstance(aliases, list):
            errors.append(f"{relative}: 'aliases' must be a list")
        elif any(not isinstance(alias, str) or not alias.strip() for alias in aliases):
            errors.append(f"{relative}: aliases must contain non-empty text values")

        for match in MARKDOWN_IMAGE.finditer(body):
            if not match.group("alt").strip():
                errors.append(f"{relative}: image is missing alternative text")
            image = resolve_image(path, match.group("target"))
            if image is not None:
                try:
                    image.relative_to(docs_dir)
                except ValueError:
                    errors.append(f"{relative}: image escapes the public docs directory: {match.group('target')!r}")
                    continue
                if not image.is_file():
                    errors.append(f"{relative}: missing image {match.group('target')!r}")
                elif image.suffix.casefold() == ".png" and image.stat().st_size > 1_500_000:
                    errors.append(f"{relative}: large PNG should be converted to a web display format: {image.name}")

    referenced_images: set[Path] = set()
    for path, (_, body, _) in notes.items():
        for match in MARKDOWN_IMAGE.finditer(body):
            image = resolve_image(path, match.group("target"))
            if image is not None and image.is_file():
                referenced_images.add(image)
    uploads = (docs_dir / "assets" / "uploads").resolve()
    if uploads.is_dir():
        for asset in uploads.rglob("*"):
            if asset.is_file() and asset.name != ".gitkeep" and asset.suffix.casefold() in PUBLISHED_IMAGE_SUFFIXES:
                if asset.resolve() not in referenced_images:
                    errors.append(f"{asset.relative_to(docs_dir.resolve()).as_posix()}: unreferenced public upload")
    return errors


def main() -> int:
    errors = validate(DOCS_DIR.resolve())
    if errors:
        print("Content validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Content validation passed: {DOCS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

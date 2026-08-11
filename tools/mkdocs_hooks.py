"""Small content-pipeline hooks for The Grand Annals.

The authoring contract stays Markdown-first: navigation is derived from folders,
the public index is generated at build time, and related-entry cards are rendered
from front matter instead of handwritten HTML.
"""

from __future__ import annotations

import logging
import posixpath
import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


log = logging.getLogger("mkdocs.hooks.annals")

_FRONT_MATTER = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", re.DOTALL)
_HEADING = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_INDEX_MARKER = "<!-- annals:index -->"

_CATEGORY_ORDER = (
    "世界与法则",
    "山河与诸邦",
    "历史与纪元",
    "众生与人物",
)

_CATEGORY_BY_ROOT = {
    "世界总览": "世界与法则",
    "法则设定": "世界与法则",
    "山河地理": "山河与诸邦",
    "文明诸邦": "山河与诸邦",
    "历史纪元": "历史与纪元",
    "众生谱系": "众生与人物",
    "星辰微光": "众生与人物",
}

_TYPE_BY_ROOT = {
    "世界总览": "世界设定",
    "法则设定": "世界法则",
    "山河地理": "山河地理",
    "文明诸邦": "文明诸邦",
    "历史纪元": "历史纪元",
    "众生谱系": "众生谱系",
    "星辰微光": "人物档案",
}

_entries: list[dict[str, Any]] = []
_entries_by_title: dict[str, dict[str, Any]] = {}
_entries_by_path: dict[str, dict[str, Any]] = {}


def _read_page(path: Path) -> tuple[dict[str, Any], str]:
    source = path.read_text(encoding="utf-8-sig")
    match = _FRONT_MATTER.match(source)
    if not match:
        return {}, source

    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        log.warning("Front matter must be a mapping: %s", path)
        return {}, source[match.end() :]
    return metadata, source[match.end() :]


def _plain_title(value: str) -> str:
    return re.sub(r"\s+#+\s*$", "", value).strip()


def _lookup_key(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("[[") and text.endswith("]]" ):
        text = text[2:-2]
    text = text.split("|", 1)[0].split("#", 1)[0].strip()
    return text.casefold()


def _path_key(value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip()
    if text.startswith("[[") and text.endswith("]]" ):
        text = text[2:-2]
    text = text.split("|", 1)[0].split("#", 1)[0].strip()
    if text.endswith(".md"):
        text = text[:-3]
    return text.strip("/").casefold()


def _infer_title(metadata: dict[str, Any], body: str, src_uri: str) -> str:
    if metadata.get("title"):
        return _plain_title(str(metadata["title"]))
    heading = _HEADING.search(body)
    if heading:
        return _plain_title(heading.group(1))
    return PurePosixPath(src_uri).stem


def _relative_url(current_url: str, target_url: str) -> str:
    current = current_url.replace("\\", "/")
    target = target_url.replace("\\", "/")
    current_dir = current.rstrip("/") if current.endswith("/") else posixpath.dirname(current)
    target_path = target.rstrip("/") or "."
    result = posixpath.relpath(target_path, current_dir or ".")
    if target.endswith("/") and result != ".":
        result += "/"
    return result


def _relative_source(current_src_uri: str, target_src_uri: str) -> str:
    current_dir = posixpath.dirname(current_src_uri.replace("\\", "/"))
    target = target_src_uri.replace("\\", "/")
    return posixpath.relpath(target, current_dir or ".")


def _escape_markdown(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def on_files(files, config):
    """Collect a stable registry before pages are rendered."""
    global _entries, _entries_by_title, _entries_by_path

    docs_dir = Path(config.docs_dir)
    entries: list[dict[str, Any]] = []

    for file in files:
        if not file.is_documentation_page():
            continue

        src_uri = file.src_uri.replace("\\", "/")
        if src_uri in {"index.md", "404.md", "索引/index.md", "开始阅读/index.md"}:
            continue

        metadata, body = _read_page(docs_dir / file.src_uri)
        title = _infer_title(metadata, body, src_uri)
        root = PurePosixPath(src_uri).parts[0]
        status = str(metadata.get("status", "公开"))
        entry_type = str(metadata.get("type") or _TYPE_BY_ROOT.get(root, "世界条目"))
        if entry_type == "人物":
            entry_type = "人物档案"

        entry = {
            "title": title,
            "description": str(metadata.get("description", "")).strip(),
            "type": entry_type,
            "status": status,
            "category": _CATEGORY_BY_ROOT.get(root, "其他条目"),
            "src_uri": src_uri,
            "src_path": src_uri[:-3] if src_uri.endswith(".md") else src_uri,
            "url": file.url,
            "is_index": PurePosixPath(src_uri).name == "index.md",
        }
        entries.append(entry)

    _entries = entries
    _entries_by_title = {_lookup_key(entry["title"]): entry for entry in entries}
    _entries_by_path = {_path_key(entry["src_path"]): entry for entry in entries}
    return files


def _resolve_related(value: Any) -> dict[str, Any] | None:
    title_match = _entries_by_title.get(_lookup_key(value))
    if title_match:
        return title_match

    path_key = _path_key(value)
    path_match = _entries_by_path.get(path_key)
    if path_match:
        return path_match

    basename = PurePosixPath(path_key).name
    candidates = [entry for key, entry in _entries_by_path.items() if PurePosixPath(key).name == basename]
    return candidates[0] if len(candidates) == 1 else None


def on_page_context(context, page, config, nav):
    """Resolve ``related`` metadata into cards with correct relative URLs."""
    if not str(page.meta.get("description", "")).strip():
        log.warning("Missing description metadata in %s", page.file.src_uri)

    related = page.meta.get("related") or []
    if isinstance(related, str):
        related = [related]

    resolved: list[dict[str, str]] = []
    for value in related:
        entry = _resolve_related(value)
        if entry is None:
            log.warning("Unknown related entry %r in %s", value, page.file.src_uri)
            continue
        resolved.append(
            {
                "title": entry["title"],
                "type": entry["type"],
                "url": _relative_url(page.url, entry["url"]),
            }
        )

    context["annals_related"] = resolved
    return context


def on_page_markdown(markdown, page, config, files):
    """Replace the index marker with all public content, grouped for readers."""
    if page.file.src_uri.replace("\\", "/") != "索引/index.md":
        return markdown
    if _INDEX_MARKER not in markdown:
        log.warning("Missing automatic index marker in %s", page.file.src_uri)
        return markdown

    public_entries = [
        entry
        for entry in _entries
        if entry["status"].casefold() in {"公开", "published", "public"}
    ]
    lines: list[str] = []

    categories = list(_CATEGORY_ORDER)
    if any(entry["category"] == "其他条目" for entry in public_entries):
        categories.append("其他条目")

    for category in categories:
        grouped = [entry for entry in public_entries if entry["category"] == category]
        if not grouped:
            continue
        grouped.sort(key=lambda item: (not item["is_index"], item["title"]))
        lines.extend((f"## {category} {{ .index-heading }}", ""))
        for entry in grouped:
            title = _escape_markdown(entry["title"])
            url = _relative_source(page.file.src_uri, entry["src_uri"])
            description = _escape_markdown(entry["description"])
            lines.append(f"- **[{title}]({url})**")
            if description:
                lines.append(f"  {description}")
        lines.append("")

    return markdown.replace(_INDEX_MARKER, "\n".join(lines).rstrip())

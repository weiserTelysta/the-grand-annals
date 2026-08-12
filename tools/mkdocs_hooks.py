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
_HEADING_LINE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_ATTRIBUTE_ONLY = re.compile(r"^\{\s*:?\s*\.[^}]+\}\s*$")
_MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(")
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

_LEAD_PAGES = {
    "开始阅读/index.md",
    "索引/index.md",
    "历史纪元/index.md",
    "山河地理/index.md",
    "文明诸邦/index.md",
    "星辰微光/index.md",
    "法则设定/index.md",
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


def _enhance_markdown(markdown: str, page) -> str:
    """Add presentation hooks without leaking CSS syntax into authored notes."""
    src_uri = page.file.src_uri.replace("\\", "/")
    lines = [line for line in markdown.splitlines() if not _ATTRIBUTE_ONLY.match(line.strip())]

    heading_classes: dict[str, str] = {}
    if src_uri == "开始阅读/index.md":
        heading_classes = {
            "建议阅读顺序": "reading-heading",
            "按兴趣探索": "topic-heading",
        }
    elif src_uri == "索引/index.md":
        heading_classes = {}
    elif PurePosixPath(src_uri).name == "index.md":
        heading_classes = {
            "当前公开": "catalog-heading",
            "当前公开的人物": "catalog-heading",
            "地理名词": "catalog-heading",
        }

    for index, line in enumerate(lines):
        match = _HEADING_LINE.match(line)
        if not match:
            continue
        heading_text = re.sub(r"\s+\{[^}]+\}\s*$", "", match.group(2)).strip()
        css_class = heading_classes.get(heading_text)
        if css_class:
            lines[index] = f"{match.group(1)} {heading_text} {{ .{css_class} }}"

    # The first block quote after H1 is a page epigraph. Classify it from its
    # content at build time so authors can keep plain, Obsidian-friendly Markdown.
    h1_index = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if h1_index is not None:
        quote_start = next(
            (i for i in range(h1_index + 1, len(lines)) if lines[i].lstrip().startswith(">")),
            None,
        )
        if quote_start is not None:
            quote_end = quote_start
            quote_lines: list[str] = []
            while quote_end < len(lines) and (
                lines[quote_end].lstrip().startswith(">") or not lines[quote_end].strip()
            ):
                quote_lines.append(lines[quote_end])
                quote_end += 1
            if quote_end < len(lines) and lines[quote_end].startswith("## "):
                epigraph_class = "epigraph" if any("——" in item for item in quote_lines) else "character-epigraph"
                # Python-Markdown's block-level attr_list form follows the
                # block directly and uses ``{ .class }`` rather than ``{:``.
                lines.insert(quote_end, f"{{ .{epigraph_class} }}")

    return "\n".join(lines)


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
        entry_type = str(metadata.get("type") or _TYPE_BY_ROOT.get(root, "世界条目"))
        if entry_type == "人物":
            entry_type = "人物档案"

        entry = {
            "title": title,
            "description": str(metadata.get("description", "")).strip(),
            "type": entry_type,
            "category": _CATEGORY_BY_ROOT.get(root, "其他条目"),
            "src_uri": src_uri,
            "src_path": src_uri[:-3] if src_uri.endswith(".md") else src_uri,
            "url": file.url,
            "is_index": PurePosixPath(src_uri).name == "index.md",
        }
        entries.append(entry)

    _entries = entries
    title_groups: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        title_groups.setdefault(_lookup_key(entry["title"]), []).append(entry)
    for key, group in title_groups.items():
        if len(group) > 1:
            log.warning(
                "Duplicate public title %r: %s",
                group[0]["title"],
                ", ".join(item["src_uri"] for item in group),
            )
    _entries_by_title = {key: group[0] for key, group in title_groups.items() if len(group) == 1}
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
    resolved_sources: set[str] = set()
    for value in related:
        entry = _resolve_related(value)
        if entry is None:
            log.warning("Unknown related entry %r in %s", value, page.file.src_uri)
            continue
        if entry["src_uri"] == page.file.src_uri.replace("\\", "/"):
            log.warning("Self-related entry %r in %s", value, page.file.src_uri)
            continue
        if entry["src_uri"] in resolved_sources:
            log.warning("Duplicate related entry %r in %s", value, page.file.src_uri)
            continue
        resolved_sources.add(entry["src_uri"])
        resolved.append(
            {
                "title": entry["title"],
                "type": entry["type"],
                "url": _relative_url(page.url, entry["url"]),
            }
        )

    context["annals_related"] = resolved
    context["annals_lead_page"] = page.file.src_uri.replace("\\", "/") in _LEAD_PAGES
    return context


def on_page_markdown(markdown, page, config, files):
    """Enhance authored Markdown and generate the public index."""
    aliases = page.meta.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    if isinstance(aliases, list) and aliases:
        tags = page.meta.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        page.meta["tags"] = list(dict.fromkeys([*tags, *aliases]))

    # The lightbox plugin otherwise injects its CSS and JavaScript into every
    # page. Derive the opt-in from authored Markdown so writers need no UI meta.
    page.meta["glightbox"] = bool(_MARKDOWN_IMAGE.search(markdown))
    markdown = _enhance_markdown(markdown, page)
    if page.file.src_uri.replace("\\", "/") != "索引/index.md":
        return markdown
    if _INDEX_MARKER not in markdown:
        log.warning("Missing automatic index marker in %s", page.file.src_uri)
        return markdown

    # The source directory is the publication boundary: everything in
    # ``docs/zh`` is public, while drafts live outside it in ``docs/weiser``.
    # This avoids overloading Material's reserved ``status`` navigation field.
    public_entries = list(_entries)
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


def on_post_build(config):
    """Remove development source maps from the production artifact."""
    site_dir = Path(config.site_dir)
    for source_map in site_dir.rglob("*.map"):
        source_map.unlink()
    for asset in (
        site_dir / "assets/stylesheets/glightbox.min.css",
        site_dir / "assets/javascripts/glightbox.min.js",
    ):
        if not asset.is_file():
            continue
        relative_url = asset.relative_to(site_dir).as_posix()
        if not any(relative_url in page.read_text(encoding="utf-8") for page in site_dir.rglob("*.html")):
            asset.unlink()

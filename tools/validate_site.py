"""Validate generated HTML and local links without a browser dependency."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


SITE_ORIGIN = "https://annals.telysta.com"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: list[str] = []
        self.lang = ""
        self.description = ""
        self.robots = ""
        self.canonical = ""
        self.og: dict[str, str] = {}
        self.links: list[str] = []
        self.images: list[tuple[str, str]] = []
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []
        self.anchors: list[str] = []
        self.headings: list[int] = []
        self.h1_count = 0
        self.has_content_image = False
        self.has_glightbox_asset = False
        self.breadcrumb_links: list[tuple[str, str]] = []
        self.breadcrumb_current_count = 0
        self._in_breadcrumb = False
        self._current_breadcrumb_href: str | None = None
        self._current_breadcrumb_text: list[str] = []
        self.json_ld: list[str] = []
        self._in_json_ld = False
        self._json_parts: list[str] = []

    @property
    def title(self) -> str:
        return "".join(self.title_parts).strip()

    def handle_starttag(self, tag: str, attrs) -> None:
        data = dict(attrs)
        if tag == "html":
            self.lang = data.get("lang", "")
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            if data.get("name") == "description":
                self.description = data.get("content", "").strip()
            if data.get("name") == "robots":
                self.robots = data.get("content", "").strip()
            if data.get("property", "").startswith("og:"):
                self.og[data["property"]] = data.get("content", "").strip()
        elif tag == "link" and data.get("rel") == "canonical":
            self.canonical = data.get("href", "").strip()
        elif tag == "link" and data.get("rel") == "stylesheet" and data.get("href"):
            self.stylesheets.append(data["href"])
            if "glightbox" in data["href"]:
                self.has_glightbox_asset = True
        elif tag == "a" and data.get("href"):
            self.links.append(data["href"])
            if self._in_breadcrumb:
                self._current_breadcrumb_href = data["href"]
                self._current_breadcrumb_text = []
        elif tag == "img" and data.get("src"):
            self.images.append((data["src"], data.get("alt", "")))
            if not set(data.get("class", "").split()) & {"twemoji", "emojione", "gemoji"}:
                self.has_content_image = True
        elif tag == "script" and data.get("src"):
            self.scripts.append(data["src"])
            if "glightbox" in data["src"]:
                self.has_glightbox_asset = True
        elif tag == "nav" and "md-path" in data.get("class", "").split():
            self._in_breadcrumb = True
        elif tag == "li" and self._in_breadcrumb and data.get("aria-current") == "page":
            self.breadcrumb_current_count += 1
        if data.get("id"):
            self.anchors.append(data["id"])
        if re.fullmatch(r"h[1-6]", tag):
            level = int(tag[1])
            self.headings.append(level)
            if level == 1:
                self.h1_count += 1
        elif tag == "script" and data.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            self.json_ld.append("".join(self._json_parts).strip())
        elif tag == "a" and self._in_breadcrumb and self._current_breadcrumb_href is not None:
            self.breadcrumb_links.append(
                ("".join(self._current_breadcrumb_text).strip(), self._current_breadcrumb_href)
            )
            self._current_breadcrumb_href = None
            self._current_breadcrumb_text = []
        elif tag == "nav" and self._in_breadcrumb:
            self._in_breadcrumb = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self._in_json_ld:
            self._json_parts.append(data)
        if self._in_breadcrumb and self._current_breadcrumb_href is not None:
            self._current_breadcrumb_text.append(data)


def route_for(path: Path, site_dir: Path) -> str:
    relative = path.relative_to(site_dir).as_posix()
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return "/" + relative[: -len("index.html")]
    return "/" + relative


def local_target_exists(site_dir: Path, route: str, href: str) -> bool:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or href.startswith(("mailto:", "tel:")):
        return True
    if not parsed.path:
        return True

    target_route = unquote(urljoin(route, parsed.path))
    target_path = target_route.lstrip("/")
    candidates = [site_dir / target_path]
    if target_route.endswith("/"):
        candidates.append(site_dir / target_path / "index.html")
    elif not Path(target_path).suffix:
        candidates.extend((site_dir / f"{target_path}.html", site_dir / target_path / "index.html"))
    return any(candidate.is_file() for candidate in candidates)


def validate(site_dir: Path) -> list[str]:
    errors: list[str] = []
    pages = sorted(site_dir.rglob("*.html"))
    if not pages:
        return [f"No HTML files found in {site_dir}"]

    for path in pages:
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        route = route_for(path, site_dir)
        label = path.relative_to(site_dir).as_posix()

        if not parser.title:
            errors.append(f"{label}: missing <title>")
        is_not_found = label == "404.html"
        is_homepage = label == "index.html"
        if not is_not_found and not parser.description:
            errors.append(f"{label}: missing meta description")
        if not parser.lang.startswith("zh"):
            errors.append(f"{label}: unexpected html lang {parser.lang!r}")
        if not is_not_found and not parser.canonical.startswith(f"{SITE_ORIGIN}/"):
            errors.append(f"{label}: invalid canonical {parser.canonical!r}")
        if not is_homepage and not is_not_found and parser.h1_count != 1:
            errors.append(f"{label}: expected exactly one h1, found {parser.h1_count}")
        if is_homepage and parser.h1_count != 1:
            errors.append(f"{label}: homepage must contain exactly one h1, found {parser.h1_count}")

        for previous, current in zip(parser.headings, parser.headings[1:]):
            if current > previous + 1:
                errors.append(f"{label}: heading level jumps from h{previous} to h{current}")

        duplicate_anchors = [anchor for anchor, count in Counter(parser.anchors).items() if count > 1]
        for anchor in duplicate_anchors:
            errors.append(f"{label}: duplicate anchor id {anchor!r}")

        if is_not_found:
            if "noindex" not in parser.robots:
                errors.append(f"{label}: 404 page must be noindex")
        else:
            for key in ("og:title", "og:description", "og:url", "og:image"):
                if not parser.og.get(key):
                    errors.append(f"{label}: missing {key}")

        for raw in parser.json_ld:
            try:
                data = json.loads(raw)
                graph = data.get("@graph", []) if isinstance(data, dict) else []
                for node in graph:
                    if not isinstance(node, dict) or node.get("@type") != "BreadcrumbList":
                        continue
                    positions = [item.get("position") for item in node.get("itemListElement", [])]
                    if positions != list(range(1, len(positions) + 1)):
                        errors.append(f"{label}: JSON-LD breadcrumb positions are not contiguous")
            except json.JSONDecodeError as exc:
                errors.append(f"{label}: invalid JSON-LD ({exc})")

        for href in parser.links:
            if not local_target_exists(site_dir, route, href):
                errors.append(f"{label}: broken local link {href!r}")
        for src, alt in parser.images:
            if not alt.strip():
                errors.append(f"{label}: image {src!r} is missing alt text")
            if not local_target_exists(site_dir, route, src):
                errors.append(f"{label}: broken local image {src!r}")
        for src in parser.scripts:
            if not local_target_exists(site_dir, route, src):
                errors.append(f"{label}: broken local script {src!r}")
        for href in parser.stylesheets:
            if not local_target_exists(site_dir, route, href):
                errors.append(f"{label}: broken local stylesheet {href!r}")
        for text, href in parser.breadcrumb_links:
            target = unquote(urljoin(route, urlsplit(href).path))
            if target == route:
                errors.append(f"{label}: breadcrumb {text!r} links to the current page")
        if not is_homepage and not is_not_found and parser.breadcrumb_current_count != 1:
            errors.append(
                f"{label}: expected one current breadcrumb, found {parser.breadcrumb_current_count}"
            )
        if parser.has_glightbox_asset and not parser.has_content_image:
            errors.append(f"{label}: lightbox assets loaded without a content image")

    for required in ("robots.txt", "sitemap.xml", "CNAME"):
        if not (site_dir / required).is_file():
            errors.append(f"Missing generated {required}")
    source_maps = sorted(site_dir.rglob("*.map"))
    for source_map in source_maps:
        errors.append(f"Development source map published: {source_map.relative_to(site_dir).as_posix()}")
    return errors


def validate_source(docs_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(docs_dir.rglob("*.md")):
        relative = path.relative_to(docs_dir).as_posix()
        source = path.read_text(encoding="utf-8-sig")
        if re.search(r"(?m)^\s*\{\s*:?\s*\.[^}]+\}\s*$", source):
            errors.append(f"{relative}: presentation-only attribute syntax is not allowed")
        if re.search(r"(?mi)^\s*</?(?:div|span|section|article|nav|button)(?:\s|>)", source):
            errors.append(f"{relative}: presentation HTML is not allowed in authored content")
        if re.search(r"(?m)^status\s*:", source):
            errors.append(f"{relative}: reserved front matter key 'status' is not allowed")
        if "\u200b" in source or "\ufeff" in source:
            errors.append(f"{relative}: contains an invisible Unicode formatting character")
    return errors


def collect_document_routes(site_dir: Path) -> set[str]:
    routes: set[str] = set()
    for path in site_dir.rglob("*.html"):
        if path.name == "404.html":
            continue
        routes.add(route_for(path, site_dir))
    return routes


def validate_discoverability(site_dir: Path) -> list[str]:
    errors: list[str] = []
    routes = collect_document_routes(site_dir)
    inbound = Counter({route: 0 for route in routes})
    for path in site_dir.rglob("*.html"):
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        source_route = route_for(path, site_dir)
        for href in parser.links:
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or href.startswith(("mailto:", "tel:")):
                continue
            target_route = unquote(urljoin(source_route, parsed.path))
            if target_route in inbound and target_route != source_route:
                inbound[target_route] += 1
    for route, count in inbound.items():
        if route != "/" and count == 0:
            errors.append(f"{route}: orphan page with no inbound internal link")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site_dir", nargs="?", default="site", type=Path)
    parser.add_argument("--docs-dir", default="docs/zh", type=Path)
    args = parser.parse_args()
    site_dir = args.site_dir.resolve()
    errors = (
        validate_source(args.docs_dir.resolve())
        + validate(site_dir)
        + validate_discoverability(site_dir)
    )
    if errors:
        print("Site validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Site validation passed: {args.site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

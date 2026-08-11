"""Validate generated HTML and local links without a browser dependency."""

from __future__ import annotations

import argparse
import json
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
        elif tag == "a" and data.get("href"):
            self.links.append(data["href"])
        elif tag == "script" and data.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            self.json_ld.append("".join(self._json_parts).strip())

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self._in_json_ld:
            self._json_parts.append(data)


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
        if not is_not_found and not parser.description:
            errors.append(f"{label}: missing meta description")
        if not parser.lang.startswith("zh"):
            errors.append(f"{label}: unexpected html lang {parser.lang!r}")
        if not is_not_found and not parser.canonical.startswith(f"{SITE_ORIGIN}/"):
            errors.append(f"{label}: invalid canonical {parser.canonical!r}")

        if is_not_found:
            if "noindex" not in parser.robots:
                errors.append(f"{label}: 404 page must be noindex")
        else:
            for key in ("og:title", "og:description", "og:url", "og:image"):
                if not parser.og.get(key):
                    errors.append(f"{label}: missing {key}")

        for raw in parser.json_ld:
            try:
                json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"{label}: invalid JSON-LD ({exc})")

        for href in parser.links:
            if not local_target_exists(site_dir, route, href):
                errors.append(f"{label}: broken local link {href!r}")

    for required in ("robots.txt", "sitemap.xml", "CNAME"):
        if not (site_dir / required).is_file():
            errors.append(f"Missing generated {required}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site_dir", nargs="?", default="site", type=Path)
    args = parser.parse_args()
    errors = validate(args.site_dir.resolve())
    if errors:
        print("Site validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Site validation passed: {args.site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Exercise representative pages in a real browser and catch layout regressions."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


CASES = (
    ("", 360, 800, "default"),
    ("", 1440, 900, "slate"),
    ("法则设定/", 360, 800, "default"),
    ("法则设定/", 1024, 768, "default"),
    ("法则设定/", 1440, 900, "slate"),
    ("法则设定/魔法体系/魔法体系/", 360, 800, "slate"),
    ("法则设定/魔法体系/魔法体系/", 1024, 768, "default"),
    ("法则设定/魔法体系/魔法体系/", 1440, 900, "slate"),
    ("文明诸邦/", 1024, 768, "slate"),
    ("星辰微光/塔莫拉广域/埃瑟穆大区/塞勒林大公爵领地/塞勒林家族/特莉丝塔·塞勒林/", 768, 1024, "default"),
    ("星辰微光/塔莫拉广域/埃瑟穆大区/塞勒林大公爵领地/塞勒林家族/特莉丝塔·塞勒林/", 1280, 800, "slate"),
)


def wait_for_server(base_url: str, timeout: float = 12.0) -> None:
    """Wait for the preview server so CI does not race its background process."""
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(base_url, timeout=1) as response:
                if response.status < 500:
                    return
        except (OSError, URLError) as error:
            last_error = error
        time.sleep(0.2)
    raise RuntimeError(f"preview server did not become ready at {base_url}: {last_error}")

def browser() -> webdriver.Chrome:
    options = Options()
    chrome = next(
        (
            candidate
            for candidate in (
                shutil.which("google-chrome"),
                shutil.which("google-chrome-stable"),
                shutil.which("chrome"),
                shutil.which("chromium"),
                shutil.which("chromium-browser"),
            )
            if candidate
        ),
        None,
    )
    windows_chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if chrome:
        options.binary_location = chrome
    elif windows_chrome.is_file():
        options.binary_location = str(windows_chrome)
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--no-first-run")
    options.add_argument("--force-device-scale-factor=1")
    options.page_load_strategy = "none"
    return webdriver.Chrome(options=options)


def inspect(driver: webdriver.Chrome) -> dict[str, object]:
    return driver.execute_script(
        """
        const article = document.querySelector('.md-content__inner');
        const isHome = document.documentElement.dataset.annalsPage === 'home';
        const h1 = article?.querySelector('h1');
        const content = document.querySelector('.md-content');
        const toc = document.querySelector('.md-sidebar--secondary .md-nav--secondary');
        const quote = article?.querySelector('blockquote');
        const quoteBefore = quote ? getComputedStyle(quote, '::before') : null;
        const noticeTitle = article?.querySelector('.admonition-title');
        const noticeBody = noticeTitle?.parentElement?.querySelector(':scope > p:not(.admonition-title)');
        const noticeIcon = noticeTitle ? getComputedStyle(noticeTitle, '::before') : null;
        const paletteButtons = [...document.querySelectorAll('label.md-header__button[for^="__palette_"]')]
          .filter((node) => getComputedStyle(node).display !== 'none' && node.offsetWidth);
        const rect = article?.getBoundingClientRect();
        const h1rect = h1?.getBoundingClientRect();
        return {
          viewport: window.innerWidth,
          viewportHeight: window.innerHeight,
          scrollWidth: document.documentElement.scrollWidth,
          scrollHeight: document.documentElement.scrollHeight,
          isHome,
          heroActions: article ? article.querySelectorAll('.hero-actions a').length : 0,
          articleLeft: rect?.left ?? -1,
          articleRightGap: rect ? window.innerWidth - rect.right : -1,
          contentLeft: content?.getBoundingClientRect().left ?? -1,
          h1Left: h1rect?.left ?? -1,
          h1Right: h1rect?.right ?? -1,
          tocVisible: Boolean(toc && getComputedStyle(toc).display !== 'none' && toc.offsetWidth),
          headings: article ? article.querySelectorAll('h2').length : 0,
          statusIcons: [...document.querySelectorAll('.md-nav .md-status')]
            .filter((node) => getComputedStyle(node).display !== 'none').length,
          paletteButtons: paletteButtons.length,
          quoteBorder: quote ? parseFloat(getComputedStyle(quote).borderInlineStartWidth) : null,
          quotePseudo: Boolean(quoteBefore && quoteBefore.content !== 'none' && quoteBefore.display !== 'none'),
          noticeIcon: Boolean(noticeIcon && noticeIcon.content !== 'none' && noticeIcon.display !== 'none'),
          noticeTitleLeft: noticeTitle
            ? noticeTitle.getBoundingClientRect().left + parseFloat(getComputedStyle(noticeTitle).paddingInlineStart)
            : null,
          noticeBodyLeft: noticeBody ? noticeBody.getBoundingClientRect().left : null,
        };
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765/")
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    wait_for_server(args.base_url)
    driver = browser()
    driver.set_page_load_timeout(8)
    try:
        for route, width, height, scheme in CASES:
            driver.set_window_size(width, height)
            url = args.base_url.rstrip("/") + "/" + quote(route, safe="/")
            driver.get(url)
            WebDriverWait(driver, 4).until(
                lambda current: current.execute_script("return Boolean(document.querySelector('.md-content__inner h1'))")
            )
            WebDriverWait(driver, 4).until(
                lambda current: current.execute_script(
                    "if (document.documentElement.dataset.annalsPage === 'home') return true;"
                    "return [...document.querySelectorAll('label.md-header__button[for^=\"__palette_\"]')]"
                    ".filter((node) => getComputedStyle(node).display !== 'none' && node.offsetWidth).length === 1"
                )
            )
            driver.execute_script(
                "document.body.dataset.mdColorScheme = arguments[0];"
                "document.documentElement.dataset.annalsScheme = arguments[0];",
                scheme,
            )
            driver.execute_script("window.stop()")
            result = inspect(driver)
            label = f"{route} ({scheme}) at {width}x{height}"
            minimum_gutter = 15 if width <= 480 else 20
            if result["scrollWidth"] > result["viewport"] + 1:
                errors.append(f"{label}: horizontal overflow {result}")
            if not result["isHome"] and result["articleLeft"] < minimum_gutter:
                errors.append(f"{label}: left gutter too small {result}")
            if not result["isHome"] and result["articleRightGap"] < minimum_gutter:
                errors.append(f"{label}: right gutter too small {result}")
            if result["h1Left"] < result["articleLeft"] - 1:
                errors.append(f"{label}: h1 escapes article {result}")
            if result["h1Right"] > result["viewport"] + 1:
                errors.append(f"{label}: h1 is clipped {result}")
            if result["headings"] <= 1 and result["tocVisible"]:
                errors.append(f"{label}: low-value TOC is visible {result}")
            if result["statusIcons"]:
                errors.append(f"{label}: reserved status icons leaked into navigation {result}")
            expected_palette_buttons = 0 if result["isHome"] else 1
            if result["paletteButtons"] != expected_palette_buttons:
                errors.append(f"{label}: expected one visible theme control {result}")
            if result["isHome"] and result["heroActions"] != 1:
                errors.append(f"{label}: homepage must expose one primary entry {result}")
            if result["isHome"] and result["scrollHeight"] > result["viewportHeight"] + 1:
                errors.append(f"{label}: homepage unexpectedly scrolls {result}")
            if result["quoteBorder"] is not None and result["quoteBorder"] < 2:
                errors.append(f"{label}: quotation rail is missing {result}")
            if result["quotePseudo"]:
                errors.append(f"{label}: quotation has a duplicate pseudo-element rail {result}")
            if result["noticeIcon"]:
                errors.append(f"{label}: redundant notice icon is visible {result}")
            if (
                result["noticeTitleLeft"] is not None
                and result["noticeBodyLeft"] is not None
                and abs(result["noticeTitleLeft"] - result["noticeBodyLeft"]) > 2
            ):
                errors.append(f"{label}: notice title and body are not aligned {result}")

            if args.artifacts:
                args.artifacts.mkdir(parents=True, exist_ok=True)
                name = route.strip("/").replace("/", "-") or "home"
                driver.save_screenshot(str((args.artifacts / f"{name}-{scheme}-{width}.png").resolve()))
    finally:
        driver.quit()

    if errors:
        print("Layout validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Layout validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

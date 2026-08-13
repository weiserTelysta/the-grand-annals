"""Exercise representative pages in a real browser and catch layout regressions."""

from __future__ import annotations

import argparse
import shutil
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
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
    ("星辰微光/塔莫拉广域/埃瑟穆大区/塞勒林大公爵领地/塞勒林家族/蕾莉萨·塞勒林/", 1280, 800, "slate"),
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


def close_browser(driver: webdriver.Chrome, timeout: float = 5.0) -> None:
    """Do not let a stalled Chrome shutdown hide completed regression results."""
    service_process = getattr(getattr(driver, "service", None), "process", None)
    shutdown = threading.Thread(target=driver.quit, daemon=True)
    shutdown.start()
    shutdown.join(timeout)
    if shutdown.is_alive() and service_process and service_process.poll() is None:
        service_process.kill()


def inspect(driver: webdriver.Chrome) -> dict[str, object]:
    return driver.execute_script(
        """
        const article = document.querySelector('.md-content__inner');
        const isHome = document.documentElement.dataset.annalsPage === 'home';
        const header = document.querySelector('.md-header');
        const h1 = article?.querySelector('h1');
        const content = document.querySelector('.md-content');
        const toc = document.querySelector('.md-sidebar--secondary .md-nav--secondary');
        const tocWrap = document.querySelector('.md-sidebar--secondary .md-sidebar__scrollwrap');
        const quote = article?.querySelector('blockquote');
        const quoteBefore = quote ? getComputedStyle(quote, '::before') : null;
        const noticeTitle = article?.querySelector('.admonition-title');
        const noticeBody = noticeTitle?.parentElement?.querySelector(':scope > p:not(.admonition-title)');
        const noticeIcon = noticeTitle ? getComputedStyle(noticeTitle, '::before') : null;
        const disclosureTitle = article?.querySelector('details > summary');
        const disclosureBody = disclosureTitle?.parentElement?.querySelector(':scope > p');
        const disclosureIcon = disclosureTitle ? getComputedStyle(disclosureTitle, '::before') : null;
        const disclosureStyles = disclosureTitle ? getComputedStyle(disclosureTitle) : null;
        const searchIcon = document.querySelector('.md-search__input + .md-search__icon');
        const footerAuthor = document.querySelector('.md-copyright__author');
        const searchTokenProbe = document.createElement('span');
        searchTokenProbe.style.color = 'var(--annals-search-icon)';
        document.body.append(searchTokenProbe);
        const searchIconUsesToken = searchIcon
          ? getComputedStyle(searchIcon).color === getComputedStyle(searchTokenProbe).color
          : null;
        searchTokenProbe.remove();
        const h2 = article?.querySelector('h2');
        const h3 = article?.querySelector('h3');
        const h4 = article?.querySelector('h4');
        const articleStyles = article ? getComputedStyle(article) : null;
        const canvasStyles = getComputedStyle(document.body);
        const parseRgb = (color) => (color.match(/[0-9.]+/g) || []).slice(0, 3).map(Number);
        const luminance = (color) => {
          const channels = parseRgb(color).map((value) => {
            const normalized = value / 255;
            return normalized <= 0.04045
              ? normalized / 12.92
              : ((normalized + 0.055) / 1.055) ** 2.4;
          });
          return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
        };
        const contrast = (foreground, background) => {
          const lighter = Math.max(luminance(foreground), luminance(background));
          const darker = Math.min(luminance(foreground), luminance(background));
          return (lighter + 0.05) / (darker + 0.05);
        };
        const tocRootItems = toc
          ? [...toc.querySelectorAll(':scope > .md-nav__list > .md-nav__item')]
          : [];
        const tocParent = tocRootItems.find((item) => item.querySelector(':scope > .md-nav'));
        const tocParentLink = tocParent?.querySelector(':scope > .md-nav__link');
        const tocChildLink = tocParent?.querySelector(':scope > .md-nav .md-nav__link');
        const domainHeading = article
          ? [...article.querySelectorAll('h2')].find((node) => node.textContent.includes('第四章、干涉域'))
          : null;
        let domainList = domainHeading?.nextElementSibling ?? null;
        while (domainList && !domainList.matches('h2, ul')) domainList = domainList.nextElementSibling;
        const alignedBlocks = article
          ? [...article.children].filter((node) =>
              node.matches('h1, h2, h3, h4, p, blockquote, .admonition, details') &&
              getComputedStyle(node).display !== 'none'
            )
          : [];
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
          headerHeight: header?.getBoundingClientRect().height ?? 0,
          heroActions: article ? article.querySelectorAll('.hero-actions a').length : 0,
          articleLeft: rect?.left ?? -1,
          articleRightGap: rect ? window.innerWidth - rect.right : -1,
          contentLeft: content?.getBoundingClientRect().left ?? -1,
          h1Left: h1rect?.left ?? -1,
          h1Right: h1rect?.right ?? -1,
          bodyContrast: articleStyles ? contrast(articleStyles.color, canvasStyles.backgroundColor) : null,
          h1Contrast: h1 ? contrast(getComputedStyle(h1).color, canvasStyles.backgroundColor) : null,
          bodySize: articleStyles ? parseFloat(articleStyles.fontSize) : null,
          h1Size: h1 ? parseFloat(getComputedStyle(h1).fontSize) : null,
          h2Size: h2 ? parseFloat(getComputedStyle(h2).fontSize) : null,
          h3Size: h3 ? parseFloat(getComputedStyle(h3).fontSize) : null,
          h4Size: h4 ? parseFloat(getComputedStyle(h4).fontSize) : null,
          h1Color: h1 ? getComputedStyle(h1).color : null,
          h2Color: h2 ? getComputedStyle(h2).color : null,
          tocVisible: Boolean(toc && getComputedStyle(toc).display !== 'none' && toc.offsetWidth),
          tocFirstIndent: tocParentLink && tocChildLink
            ? tocChildLink.getBoundingClientRect().left - tocParentLink.getBoundingClientRect().left
            : null,
          tocScrollable: Boolean(tocWrap && tocWrap.scrollHeight > tocWrap.clientHeight + 1),
          headings: article ? article.querySelectorAll('h2').length : 0,
          statusIcons: [...document.querySelectorAll('.md-nav .md-status')]
            .filter((node) => getComputedStyle(node).display !== 'none').length,
          paletteButtons: paletteButtons.length,
          searchIconUsesToken,
          footerAuthorDecoration: footerAuthor ? getComputedStyle(footerAuthor).textDecorationLine : null,
          quoteBorder: quote ? parseFloat(getComputedStyle(quote).borderInlineStartWidth) : null,
          quotePseudo: Boolean(quoteBefore && quoteBefore.content !== 'none' && quoteBefore.display !== 'none'),
          noticeIcon: Boolean(noticeIcon && noticeIcon.content !== 'none' && noticeIcon.display !== 'none'),
          noticeTitleLeft: noticeTitle
            ? noticeTitle.getBoundingClientRect().left + parseFloat(getComputedStyle(noticeTitle).paddingInlineStart)
            : null,
          noticeBodyLeft: noticeBody ? noticeBody.getBoundingClientRect().left : null,
          disclosureIcon: Boolean(
            disclosureIcon && disclosureIcon.content !== 'none' && disclosureIcon.display !== 'none'
          ),
          disclosureTitleLeft: disclosureTitle
            ? disclosureTitle.getBoundingClientRect().left
              + parseFloat(getComputedStyle(disclosureTitle).paddingInlineStart)
            : null,
          disclosureBodyLeft: disclosureBody ? disclosureBody.getBoundingClientRect().left : null,
          disclosureMouseOutline: disclosureStyles?.outlineStyle ?? null,
          disclosureMouseShadow: disclosureStyles?.boxShadow ?? null,
          disclosureUserSelect: disclosureStyles?.userSelect ?? null,
          alignedBlockOffsets: alignedBlocks.map((node) => node.getBoundingClientRect().left - rect.left),
          interferenceItems: domainList?.matches('ul') ? domainList.querySelectorAll(':scope > li').length : null,
        };
        """
    )


def inspect_toc_follow(driver: webdriver.Chrome) -> dict[str, object]:
    """Scroll a long article and verify that Material follows inside the TOC scroller."""
    driver.execute_script(
        "document.documentElement.style.scrollBehavior = 'auto';"
        "window.scrollTo(0, (document.documentElement.scrollHeight - window.innerHeight) * 0.75)"
    )
    try:
        WebDriverWait(driver, 4).until(
            lambda current: current.execute_script(
                "return (document.querySelector('.md-sidebar--secondary .md-sidebar__scrollwrap')?.scrollTop || 0) > 0"
            )
        )
    except TimeoutException:
        pass
    result = driver.execute_script(
        """
        const wrap = document.querySelector('.md-sidebar--secondary .md-sidebar__scrollwrap');
        const active = document.querySelector('.md-sidebar--secondary .md-nav__link--active');
        const cursor = [...document.querySelectorAll('.annals-toc-cursor')]
          .find((node) => node.dataset.ready === 'true' && node.offsetHeight);
        const wrapRect = wrap?.getBoundingClientRect();
        const activeRect = active?.getBoundingClientRect();
        return {
          scrollTop: wrap?.scrollTop ?? 0,
          activeText: active?.textContent.trim() ?? '',
          activeWithinToc: Boolean(
            wrapRect && activeRect &&
            activeRect.top >= wrapRect.top - 1 && activeRect.bottom <= wrapRect.bottom + 1
          ),
          activeOverflowsParent: Boolean(
            active?.parentElement && active.scrollWidth > active.parentElement.scrollWidth
          ),
          visibleCursors: [...document.querySelectorAll('.annals-toc-cursor')]
            .filter((node) => node.offsetHeight && parseFloat(getComputedStyle(node).opacity) > 0).length,
          cursorReady: Boolean(cursor),
          cursorTransition: cursor ? getComputedStyle(cursor).transitionDuration : '',
        };
        """
    )
    driver.execute_script(
        "window.scrollTo(0, 0);"
        "document.documentElement.style.removeProperty('scroll-behavior')"
    )
    return result


def inspect_disclosure_motion(driver: webdriver.Chrome) -> dict[str, object] | None:
    """Verify enhanced disclosure motion and rapid reversal without replacing native semantics."""
    summary = driver.find_elements("css selector", ".md-typeset details[class] > summary")
    if not summary:
        return None

    summary = summary[0]
    driver.execute_script("arguments[0].scrollIntoView({ block: 'center' })", summary)
    initial = driver.execute_script(
        "const details = arguments[0].parentElement;"
        "return { open: details.open, height: details.getBoundingClientRect().height }",
        summary,
    )
    driver.execute_script("arguments[0].click()", summary)
    time.sleep(0.08)
    opening = driver.execute_script(
        "const details = arguments[0].parentElement;"
        "return { open: details.open, animating: details.dataset.annalsAnimating === 'true',"
        "height: details.getBoundingClientRect().height }",
        summary,
    )
    time.sleep(0.4)
    opened = driver.execute_script(
        "const details = arguments[0].parentElement;"
        "return { open: details.open, animating: details.dataset.annalsAnimating === 'true',"
        "inlineHeight: details.style.height }",
        summary,
    )
    driver.execute_script("arguments[0].click()", summary)
    time.sleep(0.06)
    driver.execute_script("arguments[0].click()", summary)
    time.sleep(0.45)
    reversed_state = driver.execute_script(
        "const details = arguments[0].parentElement;"
        "return { open: details.open, animating: details.dataset.annalsAnimating === 'true',"
        "inlineHeight: details.style.height }",
        summary,
    )
    return {
        "initial": initial,
        "opening": opening,
        "opened": opened,
        "reversed": reversed_state,
    }


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
                lambda current: current.execute_script(
                    "return Boolean(document.querySelector('.md-content__inner h1'))"
                )
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
            WebDriverWait(driver, 2).until(
                lambda current: current.execute_script(
                    "const icon = document.querySelector('.md-search__input + .md-search__icon');"
                    "if (!icon) return true;"
                    "const probe = document.createElement('span');"
                    "probe.style.color = 'var(--annals-search-icon)';"
                    "document.body.append(probe);"
                    "const matches = getComputedStyle(icon).color === getComputedStyle(probe).color;"
                    "probe.remove();"
                    "return matches;"
                )
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
            if not result["isHome"]:
                maximum_header_height = 90 if width >= 1220 else 50
                if result["headerHeight"] > maximum_header_height:
                    errors.append(f"{label}: header consumes too much vertical space {result}")
            if result["h1Left"] < result["articleLeft"] - 1:
                errors.append(f"{label}: h1 escapes article {result}")
            if result["h1Right"] > result["viewport"] + 1:
                errors.append(f"{label}: h1 is clipped {result}")
            if not result["isHome"] and result["bodyContrast"] is not None and result["bodyContrast"] < 7:
                errors.append(f"{label}: long-form text contrast is below the enhanced reading target {result}")
            if not result["isHome"] and result["h1Contrast"] is not None and result["h1Contrast"] < 4.5:
                errors.append(f"{label}: h1 contrast is too low {result}")
            if not result["isHome"] and result["bodySize"] and result["h1Size"]:
                h1_ratio = result["h1Size"] / result["bodySize"]
                if not 1.75 <= h1_ratio <= 2.4:
                    errors.append(f"{label}: h1/body type ratio is outside the reading scale {result}")
            for heading, minimum, maximum in (("h2Size", 1.35, 1.75), ("h3Size", 1.15, 1.4), ("h4Size", 1.04, 1.2)):
                if result["bodySize"] and result[heading] is not None:
                    ratio = result[heading] / result["bodySize"]
                    if not minimum <= ratio <= maximum:
                        errors.append(f"{label}: {heading}/body type ratio is outside the reading scale {result}")
            if result["h2Color"] is not None and result["h1Color"] == result["h2Color"]:
                errors.append(f"{label}: h1 and h2 collapsed to the same color role {result}")
            if result["tocFirstIndent"] is not None and result["tocFirstIndent"] > 26:
                errors.append(f"{label}: first TOC nesting step is too deep {result}")
            if "魔法体系" in route and result["interferenceItems"] != 4:
                errors.append(f"{label}: interference domains are not a semantic four-item list {result}")
            if result["headings"] <= 1 and result["tocVisible"]:
                errors.append(f"{label}: low-value TOC is visible {result}")
            if result["statusIcons"]:
                errors.append(f"{label}: reserved status icons leaked into navigation {result}")
            if not result["isHome"] and result["searchIconUsesToken"] is not True:
                errors.append(f"{label}: search icon does not use the scheme-aware color token {result}")
            if not result["isHome"] and result["footerAuthorDecoration"] != "none":
                errors.append(f"{label}: footer author link must not be underlined {result}")
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
            if result["disclosureIcon"]:
                errors.append(f"{label}: redundant disclosure icon is visible {result}")
            if result["disclosureMouseOutline"] not in (None, "none"):
                errors.append(f"{label}: disclosure keeps a mouse-click outline {result}")
            if result["disclosureMouseShadow"] not in (None, "none"):
                errors.append(f"{label}: disclosure keeps a selected-card shadow {result}")
            if result["disclosureUserSelect"] not in (None, "none"):
                errors.append(f"{label}: disclosure label remains text-selectable {result}")
            if (
                result["disclosureTitleLeft"] is not None
                and result["disclosureBodyLeft"] is not None
                and abs(result["disclosureTitleLeft"] - result["disclosureBodyLeft"]) > 2
            ):
                errors.append(f"{label}: disclosure title and body are not aligned {result}")
            if any(abs(offset) > 1 for offset in result["alignedBlockOffsets"]):
                errors.append(f"{label}: top-level content blocks do not share one baseline {result}")

            if result["tocScrollable"]:
                toc_follow = inspect_toc_follow(driver)
                if toc_follow["scrollTop"] <= 0:
                    errors.append(f"{label}: long TOC did not follow the article {toc_follow}")
                if not toc_follow["activeWithinToc"]:
                    errors.append(f"{label}: active TOC entry left the visible scroller {toc_follow}")
                if toc_follow["activeOverflowsParent"]:
                    errors.append(f"{label}: active TOC style overflows its container {toc_follow}")
                if toc_follow["visibleCursors"] != 1 or not toc_follow["cursorReady"]:
                    errors.append(f"{label}: expected one visible TOC cursor {toc_follow}")
                if "0.18s" not in toc_follow["cursorTransition"]:
                    errors.append(f"{label}: TOC cursor motion is missing {toc_follow}")

            if result["disclosureTitleLeft"] is not None:
                disclosure_motion = inspect_disclosure_motion(driver)
                if disclosure_motion:
                    initial = disclosure_motion["initial"]
                    opening = disclosure_motion["opening"]
                    opened = disclosure_motion["opened"]
                    reversed_state = disclosure_motion["reversed"]
                    if not opening["open"] or not opening["animating"]:
                        errors.append(f"{label}: disclosure has no opening intermediate state {disclosure_motion}")
                    if not (initial["height"] < opening["height"]):
                        errors.append(f"{label}: disclosure height does not interpolate {disclosure_motion}")
                    if not opened["open"] or opened["animating"] or opened["inlineHeight"]:
                        errors.append(f"{label}: disclosure opening did not clean up {disclosure_motion}")
                    if not reversed_state["open"] or reversed_state["animating"] or reversed_state["inlineHeight"]:
                        errors.append(f"{label}: interrupted disclosure ended incorrectly {disclosure_motion}")

            if args.artifacts:
                args.artifacts.mkdir(parents=True, exist_ok=True)
                name = route.strip("/").replace("/", "-") or "home"
                driver.save_screenshot(str((args.artifacts / f"{name}-{scheme}-{width}.png").resolve()))
    finally:
        close_browser(driver)

    if errors:
        print("Layout validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Layout validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

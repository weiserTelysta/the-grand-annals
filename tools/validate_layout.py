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
    ("开始阅读/", 2048, 1200, "default"),
    ("开始阅读/", 2048, 1200, "slate"),
    ("法则设定/", 360, 800, "default"),
    ("法则设定/", 1024, 768, "default"),
    ("法则设定/", 1440, 900, "slate"),
    ("法则设定/", 2048, 1152, "default"),
    ("法则设定/魔法体系/魔法体系/", 360, 800, "slate"),
    ("法则设定/魔法体系/魔法体系/", 1024, 768, "default"),
    ("法则设定/魔法体系/魔法体系/", 1440, 900, "slate"),
    ("文明诸邦/", 1024, 768, "slate"),
    ("星辰微光/塔莫拉广域/埃瑟穆大区/塞勒林大公爵领地/塞勒林家族/特莉丝塔·塞勒林/", 768, 1024, "default"),
    ("星辰微光/塔莫拉广域/埃瑟穆大区/塞勒林大公爵领地/塞勒林家族/特莉丝塔·塞勒林/", 768, 1024, "slate"),
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
        const headerInner = header?.querySelector('.md-header__inner');
        const headerTitle = header?.querySelector('.md-header__title');
        const headerLogo = header?.querySelector('.md-header__button.md-logo');
        const headerTitleText = headerTitle?.querySelector('.md-header__topic:first-child .md-ellipsis');
        const headerLogoIcon = headerLogo?.querySelector('svg');
        const tabs = document.querySelector('.md-tabs');
        const tabsGrid = tabs?.querySelector(':scope > .md-grid');
        const tabsList = tabs?.querySelector('.md-tabs__list');
        const headerStyles = header ? getComputedStyle(header) : null;
        const tabsStyles = tabs ? getComputedStyle(tabs) : null;
        const tabsListStyles = tabsList ? getComputedStyle(tabsList) : null;
        const h1 = article?.querySelector('h1');
        const paragraph = article?.querySelector(':scope > p');
        const path = document.querySelector('.md-path');
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
        const hero = document.querySelector('.hero-section');
        const searchForm = document.querySelector('.md-search__form');
        const searchIconElement = searchForm?.querySelector('.md-search__icon[for="__search"]');
        const ornamentLayer = document.querySelector('.annals-ornament');
        const ornament = document.querySelector('.annals-ornament__mark');
        const ornamentLayerStyles = ornamentLayer ? getComputedStyle(ornamentLayer) : null;
        const ornamentRect = ornamentLayer?.getBoundingClientRect();
        const ornamentStyles = ornament ? getComputedStyle(ornament) : null;
        const dust = document.querySelector('.annals-dust');
        const searchTokenProbe = document.createElement('span');
        searchTokenProbe.style.color = 'var(--annals-header-gold)';
        document.body.append(searchTokenProbe);
        const searchIconUsesToken = searchIcon
          ? getComputedStyle(searchIcon).color === getComputedStyle(searchTokenProbe).color
          : null;
        searchTokenProbe.remove();
        const contentTrackProbe = document.createElement('span');
        contentTrackProbe.style.cssText = 'position:absolute;visibility:hidden;width:var(--annals-content-track)';
        document.body.append(contentTrackProbe);
        const expectedContentTrack = contentTrackProbe.getBoundingClientRect().width;
        contentTrackProbe.remove();
        const h2 = article?.querySelector('h2');
        const h3 = article?.querySelector('h3');
        const h4 = article?.querySelector('h4');
        const articleStyles = article ? getComputedStyle(article) : null;
        const contentStyles = content ? getComputedStyle(content) : null;
        const canvasStyles = getComputedStyle(document.body);
        const primaryNavLink = document.querySelector('.md-sidebar--primary .md-nav__link');
        const secondaryNavLink = document.querySelector('.md-sidebar--secondary .md-nav__link');
        const tabLink = document.querySelector('.md-tabs__link');
        const desktopAuxiliaryButtons = [
          header?.querySelector('.md-header__button[for="__drawer"]'),
          header?.querySelector('.md-header__button[for="__search"]')
        ].filter((node) => node && getComputedStyle(node).display !== 'none' && node.offsetWidth);
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
        const paragraphRect = paragraph?.getBoundingClientRect();
        const pathRect = path?.offsetWidth ? path.getBoundingClientRect() : null;
        const headerInnerRect = headerInner?.getBoundingClientRect();
        const headerTitleRect = headerTitle?.getBoundingClientRect();
        const headerLogoRect = headerLogo?.getBoundingClientRect();
        const headerTitleTextRect = headerTitleText?.getBoundingClientRect();
        const headerLogoIconRect = headerLogoIcon?.getBoundingClientRect();
        const tabsGridRect = tabsGrid?.getBoundingClientRect();
        const mainInnerRect = document.querySelector('.md-main__inner')?.getBoundingClientRect();
        const heroRect = hero?.getBoundingClientRect();
        const searchRect = searchForm?.getBoundingClientRect();
        const searchIconRect = searchIconElement?.getBoundingClientRect();
        const paletteRect = paletteButtons[0]?.getBoundingClientRect();
        const tabRect = tabLink?.getBoundingClientRect();
        const tabHitTarget = tabRect
          ? document.elementFromPoint(tabRect.left + tabRect.width / 2, tabRect.top + tabRect.height / 2)
          : null;
        const searchHitTarget = searchRect
          ? document.elementFromPoint(searchRect.left + searchRect.width / 2, searchRect.top + searchRect.height / 2)
          : null;
        return {
          viewport: window.innerWidth,
          layoutViewportWidth: document.documentElement.clientWidth,
          viewportHeight: window.innerHeight,
          scrollWidth: document.documentElement.scrollWidth,
          scrollHeight: document.documentElement.scrollHeight,
          isHome,
          headerHeight: header?.getBoundingClientRect().height ?? 0,
          headerBackground: headerStyles?.backgroundColor ?? null,
          headerInnerLeft: headerInnerRect?.left ?? null,
          headerInnerWidth: headerInnerRect?.width ?? null,
          headerTitleTop: headerTitleRect?.top ?? null,
          headerTitleHeight: headerTitleRect?.height ?? null,
          headerLogoTop: headerLogoRect?.top ?? null,
          headerLogoHeight: headerLogoRect?.height ?? null,
          headerTitleTextCenter: headerTitleTextRect
            ? headerTitleTextRect.top + headerTitleTextRect.height / 2
            : null,
          headerLogoIconCenter: headerLogoIconRect
            ? headerLogoIconRect.top + headerLogoIconRect.height / 2
            : null,
          desktopAuxiliaryButtons: desktopAuxiliaryButtons.length,
          headerBottomBorder: headerStyles ? parseFloat(headerStyles.borderBottomWidth) : null,
          tabsVisible: Boolean(tabs && getComputedStyle(tabs).display !== 'none' && tabs.offsetHeight),
          tabsBackground: tabsStyles?.backgroundColor ?? null,
          tabsGridLeft: tabsGridRect?.left ?? null,
          tabsGridWidth: tabsGridRect?.width ?? null,
          tabsBottomBorder: tabsStyles ? parseFloat(tabsStyles.borderBottomWidth) : null,
          tabsClientHeight: tabs?.clientHeight ?? 0,
          tabsScrollHeight: tabs?.scrollHeight ?? 0,
          tabsVerticalOverflow: Boolean(tabs && tabs.scrollHeight > tabs.clientHeight),
          tabsOverflowY: tabsStyles?.overflowY ?? null,
          tabsListClientHeight: tabsList?.clientHeight ?? 0,
          tabsListScrollHeight: tabsList?.scrollHeight ?? 0,
          tabsListVerticalOverflow: Boolean(tabsList && tabsList.scrollHeight > tabsList.clientHeight),
          tabsListOverflowY: tabsListStyles?.overflowY ?? null,
          heroActions: article ? article.querySelectorAll('.hero-actions a').length : 0,
          heroLeft: heroRect?.left ?? null,
          heroWidth: heroRect?.width ?? null,
          mainInnerLeft: mainInnerRect?.left ?? null,
          mainInnerWidth: mainInnerRect?.width ?? null,
          articleLeft: rect?.left ?? -1,
          articleRightGap: rect ? window.innerWidth - rect.right : -1,
          contentLeft: content?.getBoundingClientRect().left ?? -1,
          contentWidth: content?.getBoundingClientRect().width ?? -1,
          expectedContentTrack,
          h1Left: h1rect?.left ?? -1,
          h1Right: h1rect?.right ?? -1,
          pathLeft: pathRect?.left ?? null,
          paragraphWidth: paragraphRect?.width ?? null,
          contentBackground: contentStyles?.backgroundColor ?? null,
          canvasBackground: canvasStyles.backgroundColor,
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
          paletteTop: paletteRect?.top ?? null,
          paletteHeight: paletteRect?.height ?? null,
          paletteBoxShadow: paletteButtons[0] ? getComputedStyle(paletteButtons[0]).boxShadow : null,
          searchTop: searchRect?.top ?? null,
          searchHeight: searchRect?.height ?? null,
          searchCenter: searchRect ? searchRect.top + searchRect.height / 2 : null,
          searchIconCenter: searchIconRect ? searchIconRect.top + searchIconRect.height / 2 : null,
          searchHitTarget: Boolean(searchForm && searchHitTarget && searchForm.contains(searchHitTarget)),
          searchIconUsesToken,
          ornamentPresent: Boolean(ornament && ornament.offsetHeight),
          ornamentMask: ornamentStyles?.maskImage ?? ornamentStyles?.webkitMaskImage ?? null,
          ornamentOpacity: ornamentStyles ? parseFloat(ornamentStyles.opacity) : null,
          ornamentPosition: ornamentLayerStyles?.position ?? null,
          ornamentZIndex: ornamentLayerStyles?.zIndex ?? null,
          ornamentWidth: ornamentRect?.width ?? null,
          ornamentCenterX: ornamentRect ? ornamentRect.left + ornamentRect.width / 2 : null,
          ornamentCenterY: ornamentRect ? ornamentRect.top + ornamentRect.height / 2 : null,
          primaryNavSize: primaryNavLink ? parseFloat(getComputedStyle(primaryNavLink).fontSize) : null,
          primaryNavLineHeight: primaryNavLink ? parseFloat(getComputedStyle(primaryNavLink).lineHeight) : null,
          secondaryNavSize: secondaryNavLink ? parseFloat(getComputedStyle(secondaryNavLink).fontSize) : null,
          secondaryNavLineHeight: secondaryNavLink ? parseFloat(getComputedStyle(secondaryNavLink).lineHeight) : null,
          tabSize: tabLink ? parseFloat(getComputedStyle(tabLink).fontSize) : null,
          tabPointerEvents: tabLink ? getComputedStyle(tabLink).pointerEvents : null,
          tabHitTarget: Boolean(tabLink && tabHitTarget && tabLink.contains(tabHitTarget)),
          dustPresent: Boolean(dust && dust.offsetHeight),
          dustPointerEvents: dust ? getComputedStyle(dust).pointerEvents : null,
          dustEffect: dust?.dataset.annalsEffect ?? null,
          dustFrameRate: dust?.dataset.annalsFrameRate ?? null,
          dustParticleCount: dust ? Number(dust.dataset.annalsParticleCount || 0) : 0,
          dustParticleMix: dust?.dataset.annalsParticleMix ?? null,
          dustParticleShapes: dust?.dataset.annalsParticleShapes ?? null,
          dustFlowerMotion: dust?.dataset.annalsFlowerMotion ?? null,
          dustFlowerAngle: dust ? Number(dust.dataset.annalsFlowerAngle || 0) : null,
          dustReadingIntensity: dust ? Number(dust.dataset.annalsReadingIntensity || 0) : 0,
          dustPainted: dust?.dataset.annalsPainted === 'true',
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


def inspect_mobile_search(driver: webdriver.Chrome) -> dict[str, object] | None:
    """Open the compact search sheet and verify its visible focus treatment."""
    triggers = driver.find_elements("css selector", ".md-header__button[for='__search']")
    trigger = next((node for node in triggers if node.is_displayed()), None)
    if not trigger:
        return None
    trigger.click()
    WebDriverWait(driver, 2).until(
        lambda current: current.execute_script("return document.querySelector('#__search')?.checked")
    )
    search_input = driver.find_element("css selector", ".md-search__input")
    search_input.click()
    time.sleep(0.4)
    return driver.execute_script(
        """
        const field = document.querySelector('.md-search__form');
        const input = document.querySelector('.md-search__input');
        const panel = document.querySelector('.md-search__output');
        const inner = document.querySelector('.md-search__inner');
        const fieldRect = field.getBoundingClientRect();
        const panelRect = panel.getBoundingClientRect();
        const fieldStyles = getComputedStyle(field);
        const inputStyles = getComputedStyle(input);
        const panelStyles = getComputedStyle(panel);
        return {
          fieldHeight: fieldRect.height,
          fieldLeft: fieldRect.left,
          fieldRightGap: document.documentElement.clientWidth - fieldRect.right,
          fieldRadius: parseFloat(fieldStyles.borderTopLeftRadius),
          fieldBorder: parseFloat(fieldStyles.borderTopWidth),
          fieldShadow: fieldStyles.boxShadow,
          inputOutline: inputStyles.outlineStyle,
          inputOutlineWidth: parseFloat(inputStyles.outlineWidth),
          panelLeft: panelRect.left,
          panelRightGap: document.documentElement.clientWidth - panelRect.right,
          panelRadius: parseFloat(panelStyles.borderTopLeftRadius),
          panelBackground: panelStyles.backgroundColor,
          innerBackground: getComputedStyle(inner).backgroundColor
        };
        """
    )


def inspect_mobile_drawer(driver: webdriver.Chrome) -> dict[str, object] | None:
    """Open the compact drawer and ensure its links remain above the overlay."""
    triggers = driver.find_elements("css selector", ".md-header__button[for='__drawer']")
    trigger = next((node for node in triggers if node.is_displayed()), None)
    if not trigger:
        return None
    driver.execute_script("arguments[0].click()", trigger)
    WebDriverWait(driver, 2).until(
        lambda current: current.execute_script("return document.querySelector('#__drawer')?.checked")
    )
    time.sleep(0.35)
    state = driver.execute_script(
        """
        const drawer = document.querySelector('.md-sidebar--primary');
        const overlay = document.querySelector('.md-overlay');
        const drawerRect = drawer?.getBoundingClientRect();
        const drawerTarget = drawerRect
          ? document.elementFromPoint(drawerRect.left + 24, Math.min(drawerRect.bottom - 1, drawerRect.top + 124))
          : null;
        const links = [...(drawer?.querySelectorAll('a[href]') ?? [])]
          .filter((node) => node.offsetWidth && node.offsetHeight && !node.classList.contains('md-logo'));
        const link = links.find((node) => {
          const rect = node.getBoundingClientRect();
          const target = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
          return target && node.contains(target);
        });
        return {
          drawerVisible: Boolean(drawer && drawer.offsetWidth && drawer.offsetHeight),
          drawerHitTarget: Boolean(drawer && drawerTarget && drawer.contains(drawerTarget)),
          linkHitTarget: Boolean(link),
          overlayCoversDrawer: Boolean(
            overlay && drawerTarget && (drawerTarget === overlay || overlay.contains(drawerTarget))
          ),
          targetClass: drawerTarget?.className ?? null
        };
        """
    )
    driver.execute_script(
        """
        const toggle = document.querySelector('#__drawer');
        if (toggle) {
          toggle.checked = false;
          toggle.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """
    )
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765/")
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    header_backgrounds: dict[str, str] = {}
    category_navigation_checked = False
    palette_continuity_checked = False
    mobile_search_schemes_checked: set[str] = set()
    mobile_drawer_checked = False
    flower_rotation_checked = False
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
                    "probe.style.color = 'var(--annals-header-gold)';"
                    "document.body.append(probe);"
                    "const matches = getComputedStyle(icon).color === getComputedStyle(probe).color;"
                    "probe.remove();"
                    "return matches;"
                )
            )
            driver.execute_script("window.stop()")
            result = inspect(driver)
            label = f"{route} ({scheme}) at {width}x{height}"
            if not result["isHome"] and result["headerBackground"]:
                header_backgrounds.setdefault(scheme, result["headerBackground"])
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
                if width >= 1480 and abs(result["contentWidth"] - result["expectedContentTrack"]) > 1:
                    errors.append(f"{label}: desktop content surface left its stable track {result}")
                if width >= 1480:
                    layout_width = min(result["layoutViewportWidth"], result["scrollWidth"])
                    expected_content_left = (layout_width - result["expectedContentTrack"]) / 2
                    if abs(result["contentLeft"] - expected_content_left) > 2:
                        errors.append(f"{label}: desktop content surface is no longer centered {result}")
                    for edge in ("headerInnerLeft", "tabsGridLeft"):
                        if result[edge] is not None and abs(result[edge] - result["mainInnerLeft"]) > 2:
                            errors.append(f"{label}: {edge} no longer aligns with the reading shell {result}")
                    for measure in ("headerInnerWidth", "tabsGridWidth"):
                        if result[measure] is not None and abs(result[measure] - result["mainInnerWidth"]) > 2:
                            errors.append(f"{label}: {measure} no longer matches the reading shell {result}")
                    if result["paragraphWidth"] is not None and result["paragraphWidth"] < 820:
                        errors.append(f"{label}: desktop paragraph leaves excessive unused article width {result}")
                if result["contentBackground"] not in ("rgba(0, 0, 0, 0)", "transparent"):
                    errors.append(f"{label}: main reading area regained a boxed surface {result}")
                if not result["ornamentPresent"] or result["ornamentMask"] in (None, "none"):
                    errors.append(f"{label}: centered watermark is missing or not masked {result}")
                if result["ornamentPosition"] != "fixed" or result["ornamentZIndex"] != "0":
                    errors.append(f"{label}: watermark is not a fixed background layer {result}")
                visible_layout_width = min(result["layoutViewportWidth"], result["scrollWidth"])
                if result["ornamentCenterX"] is not None and abs(result["ornamentCenterX"] - visible_layout_width / 2) > 2:
                    errors.append(f"{label}: watermark is not horizontally centered in the viewport {result}")
                if result["ornamentCenterY"] is not None and abs(result["ornamentCenterY"] - result["viewportHeight"] / 2) > 2:
                    errors.append(f"{label}: watermark is not vertically centered in the viewport {result}")
                if result["ornamentWidth"] is not None:
                    minimum_ornament_width = 400 if width >= 1220 else 240
                    if result["ornamentWidth"] < minimum_ornament_width:
                        errors.append(f"{label}: centered watermark is too small {result}")
                    if width >= 1220 and result["ornamentWidth"] > 605:
                        errors.append(f"{label}: centered watermark is too large {result}")
                if result["ornamentOpacity"] is not None and result["ornamentOpacity"] > 0.07:
                    errors.append(f"{label}: centered watermark is too visually strong {result}")
                for size_key in ("primaryNavSize", "secondaryNavSize"):
                    if result[size_key] is not None and result[size_key] < 14:
                        errors.append(f"{label}: {size_key} is too small for comfortable navigation {result}")
                for size_key, line_key in (("primaryNavSize", "primaryNavLineHeight"), ("secondaryNavSize", "secondaryNavLineHeight")):
                    if result[size_key] and result[line_key] and result[line_key] / result[size_key] < 1.5:
                        errors.append(f"{label}: {line_key} is too tight {result}")
                if result["tabsVisible"] and result["tabSize"] is not None and result["tabSize"] < 14:
                    errors.append(f"{label}: desktop tab labels are too small {result}")
                if width >= 1480 and not result["dustPresent"]:
                    errors.append(f"{label}: desktop archive dust layer is missing {result}")
                if width >= 1480 and result["dustPresent"]:
                    if result["dustPointerEvents"] != "none":
                        errors.append(f"{label}: ambient field intercepts pointer input {result}")
                    if result["dustEffect"] != "heraldic-field":
                        errors.append(f"{label}: ambient field is not the selected heraldic treatment {result}")
                    if result["dustFrameRate"] != "30":
                        errors.append(f"{label}: ambient field lost its frame-rate limit {result}")
                    if not 32 <= result["dustParticleCount"] <= 46:
                        errors.append(f"{label}: ambient field particle budget changed {result}")
                    mix = [int(value) for value in str(result["dustParticleMix"] or "").split("/") if value.isdigit()]
                    if len(mix) != 3 or sum(mix) != result["dustParticleCount"]:
                        errors.append(f"{label}: ambient field particle mix is invalid {result}")
                    else:
                        ratios = [value / sum(mix) for value in mix]
                        if not (0.67 <= ratios[0] <= 0.72 and 0.17 <= ratios[1] <= 0.22 and 0.08 <= ratios[2] <= 0.13):
                            errors.append(f"{label}: ambient field lost its 70/20/10 mix {result}")
                    if result["dustParticleShapes"] != "dust/filament/flower-u2740":
                        errors.append(f"{label}: ambient field lost its literal flower glyph treatment {result}")
                    if result["dustFlowerMotion"] != "continuous-rotation":
                        errors.append(f"{label}: flower glyphs lost their continuous rotation {result}")
                    if abs(result["dustReadingIntensity"] - 0.2) > 0.001:
                        errors.append(f"{label}: ambient field reading attenuation changed {result}")
                    if not result["dustPainted"]:
                        errors.append(f"{label}: ambient field canvas exists but has not painted {result}")
                    if not flower_rotation_checked:
                        time.sleep(0.2)
                        next_angle = driver.execute_script(
                            "return Number(document.querySelector('.annals-dust')?.dataset.annalsFlowerAngle || 0)"
                        )
                        if abs(next_angle - result["dustFlowerAngle"]) < 0.001:
                            errors.append(f"{label}: flower glyph angle is not changing {result}")
                        flower_rotation_checked = True
            if result["tabsVisible"]:
                if result["headerBackground"] != result["tabsBackground"]:
                    errors.append(f"{label}: header and tabs are not one continuous color field {result}")
                if result["headerBottomBorder"] > 0 or result["tabsBottomBorder"] > 0:
                    errors.append(f"{label}: header or tabs regained a persistent border {result}")
                if result["tabsVerticalOverflow"]:
                    errors.append(f"{label}: tabs wrapper has vertical overflow {result}")
                if result["tabsListVerticalOverflow"]:
                    errors.append(f"{label}: tabs list has vertical overflow {result}")
                if result["tabsOverflowY"] not in ("hidden", "clip"):
                    errors.append(f"{label}: tabs wrapper permits vertical scrolling {result}")
                if result["tabsListOverflowY"] not in ("hidden", "clip"):
                    errors.append(f"{label}: tabs list permits vertical scrolling {result}")
                if result["tabPointerEvents"] == "none" or not result["tabHitTarget"]:
                    errors.append(f"{label}: visible category tabs cannot receive pointer input {result}")
            if result["h1Left"] < result["articleLeft"] - 1:
                errors.append(f"{label}: h1 escapes article {result}")
            if (
                not result["isHome"]
                and result["pathLeft"] is not None
                and abs(result["pathLeft"] - result["h1Left"]) > 1
            ):
                errors.append(f"{label}: breadcrumb does not align with the h1 {result}")
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
            if result["isHome"] and (
                result["heroLeft"] is None
                or abs(result["heroLeft"]) > 1
                or abs(result["heroWidth"] - result["layoutViewportWidth"]) > 1
            ):
                errors.append(f"{label}: homepage hero does not fill the viewport {result}")
            if not result["isHome"] and width >= 1220:
                if result["desktopAuxiliaryButtons"]:
                    errors.append(f"{label}: desktop header exposes drawer or duplicate search buttons {result}")
                if result["paletteHeight"] is None or abs(result["paletteHeight"] - result["searchHeight"]) > 1:
                    errors.append(f"{label}: theme control and search field are not the same height {result}")
                if result["searchHeight"] is None or result["searchHeight"] > 36:
                    errors.append(f"{label}: desktop search field is too tall {result}")
                if not result["searchHitTarget"]:
                    errors.append(f"{label}: desktop search field cannot receive pointer input {result}")
                if result["paletteTop"] is None or abs(result["paletteTop"] - result["searchTop"]) > 1:
                    errors.append(f"{label}: theme control and search field are not vertically aligned {result}")
                for control in ("headerTitle", "headerLogo"):
                    if result[f"{control}Height"] is None or abs(result[f"{control}Height"] - result["searchHeight"]) > 1:
                        errors.append(f"{label}: {control} and search field are not the same height {result}")
                    if result[f"{control}Top"] is None or abs(result[f"{control}Top"] - result["searchTop"]) > 1:
                        errors.append(f"{label}: {control} and search field are not vertically aligned {result}")
                for center in ("headerTitleTextCenter", "headerLogoIconCenter", "searchIconCenter"):
                    if result[center] is None or abs(result[center] - result["searchCenter"]) > 1:
                        errors.append(f"{label}: {center} is not optically centered with the search field {result}")
                if result["paletteBoxShadow"] not in (None, "none"):
                    errors.append(f"{label}: theme control regained the exposed lower edge {result}")
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

            if (
                not palette_continuity_checked
                and not result["isHome"]
                and width >= 1220
                and result["scrollHeight"] > result["viewportHeight"] + 100
            ):
                target = min(420, result["scrollHeight"] - result["viewportHeight"])
                driver.execute_script(
                    "document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,arguments[0])",
                    target,
                )
                time.sleep(0.08)
                before = driver.execute_script("return window.scrollY")
                scrolled_chrome = driver.execute_script(
                    """
                    const header = document.querySelector('.md-header');
                    const tabs = document.querySelector('.md-tabs');
                    const headerRect = header?.getBoundingClientRect();
                    const tabsRect = tabs?.getBoundingClientRect();
                    return {
                      headerTop: headerRect?.top ?? null,
                      headerHeight: headerRect?.height ?? null,
                      tabsBottom: tabsRect?.bottom ?? null
                    };
                    """
                )
                if scrolled_chrome["tabsBottom"] is not None and scrolled_chrome["tabsBottom"] > 1:
                    errors.append(f"{label}: category tabs did not scroll out of view {scrolled_chrome}")
                if (
                    scrolled_chrome["headerTop"] is None
                    or abs(scrolled_chrome["headerTop"]) > 1
                    or scrolled_chrome["headerHeight"] > 50
                ):
                    errors.append(f"{label}: compact brand header did not remain available {scrolled_chrome}")
                palette = driver.find_elements("css selector", ".md-header__option label:not([hidden])")
                if palette:
                    palette[0].click()
                    time.sleep(0.35)
                    after = driver.execute_script("return window.scrollY")
                    if abs(after - before) > 1:
                        errors.append(f"{label}: palette switch changed scroll position from {before} to {after}")
                    active = driver.execute_script("return document.activeElement?.id || document.activeElement?.tagName")
                    if active and str(active).startswith("__palette_"):
                        errors.append(f"{label}: pointer palette switch left the hidden input focused")
                    palette_continuity_checked = True

            if args.artifacts:
                args.artifacts.mkdir(parents=True, exist_ok=True)
                name = route.strip("/").replace("/", "-") or "home"
                driver.save_screenshot(str((args.artifacts / f"{name}-{scheme}-{width}.png").resolve()))

            if scheme not in mobile_search_schemes_checked and not result["isHome"] and 700 <= width < 960:
                search_panel = inspect_mobile_search(driver)
                if not search_panel:
                    errors.append(f"{label}: compact search trigger is missing")
                else:
                    if search_panel["inputOutline"] != "none" and search_panel["inputOutlineWidth"] > 0:
                        errors.append(f"{label}: compact search keeps a hard input outline {search_panel}")
                    if search_panel["fieldBorder"] > 0 or search_panel["fieldShadow"] != "none":
                        errors.append(f"{label}: compact search field regained a border or ring {search_panel}")
                    if not 43 <= search_panel["fieldHeight"] <= 45:
                        errors.append(f"{label}: compact search field height is outside its touch target {search_panel}")
                    for inset in ("fieldLeft", "fieldRightGap", "panelLeft", "panelRightGap"):
                        if search_panel[inset] < 12:
                            errors.append(f"{label}: compact search panel touches the viewport edge {search_panel}")
                    if search_panel["fieldRadius"] < 20 or search_panel["panelRadius"] < 10:
                        errors.append(f"{label}: compact search surfaces lost their rounded shape {search_panel}")
                    if args.artifacts:
                        driver.save_screenshot(
                            str((args.artifacts / f"{name}-{scheme}-{width}-search.png").resolve())
                        )
                    mobile_search_schemes_checked.add(scheme)

            if not mobile_drawer_checked and not result["isHome"] and width < 600:
                drawer_state = inspect_mobile_drawer(driver)
                if not drawer_state:
                    errors.append(f"{label}: compact drawer trigger is missing")
                else:
                    if not drawer_state["drawerVisible"]:
                        errors.append(f"{label}: compact drawer did not open {drawer_state}")
                    if (
                        not drawer_state["drawerHitTarget"]
                        or not drawer_state["linkHitTarget"]
                        or drawer_state["overlayCoversDrawer"]
                    ):
                        errors.append(f"{label}: compact drawer link is covered by the overlay {drawer_state}")
                    mobile_drawer_checked = True

            if not category_navigation_checked and result["tabsVisible"] and width >= 1480:
                driver.execute_script("window.scrollTo(0, 0)")
                time.sleep(0.05)
                current_path = driver.execute_script("return location.pathname")
                target = next(
                    (
                        link for link in driver.find_elements("css selector", ".md-tabs__link")
                        if link.is_displayed()
                        and driver.execute_script("return new URL(arguments[0].href).pathname", link) != current_path
                    ),
                    None,
                )
                if target:
                    try:
                        target.click()
                        WebDriverWait(driver, 3).until(
                            lambda current: current.execute_script("return location.pathname") != current_path
                        )
                        category_navigation_checked = True
                    except Exception as error:  # Selenium reports interception with actionable context.
                        errors.append(f"{label}: visible category tab click failed: {error}")
    finally:
        close_browser(driver)

    if header_backgrounds.get("default") == header_backgrounds.get("slate"):
        errors.append(f"light and dark header colors are identical: {header_backgrounds}")

    if errors:
        print("Layout validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Layout validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

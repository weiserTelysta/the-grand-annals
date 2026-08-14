(() => {
  document.documentElement.classList.add("has-js");

  const scriptUrl = document.currentScript
    ? new URL(document.currentScript.src, window.location.href)
    : new URL("assets/javascripts/annals.js", document.baseURI);

  const periods = {
    morning: {
      range: [6, 12],
      file: "Telysta&Losalind_Library_day_01"
    },
    afternoon: {
      range: [12, 18],
      file: "Telysta&Losalind_Library_day_02"
    },
    evening: {
      range: [18, 22],
      file: "Telysta&Losalind_Library_night_01"
    },
    night: {
      range: [22, 6],
      file: "Telysta&Losalind_Library_night_02"
    }
  };

  function getCurrentPeriod(hour) {
    return Object.entries(periods).find(([, config]) => {
      const [start, end] = config.range;
      return start < end
        ? hour >= start && hour < end
        : hour >= start || hour < end;
    })?.[0] || "night";
  }

  function revealHero(body) {
    window.requestAnimationFrame(() => body.classList.add("hero-ready"));
  }

  function getHeroImageVariant() {
    if (window.matchMedia("(max-width: 48em)").matches) return "mobile-960";

    const pixelWidth = window.innerWidth * Math.min(window.devicePixelRatio || 1, 2);
    return pixelWidth > 1800 ? "desktop-2560" : "desktop-1600";
  }

  function initializeHero() {
    const hero = document.querySelector("[data-hero]");
    if (!hero || hero.dataset.initialized === "true") return;

    hero.dataset.initialized = "true";
    const body = document.body;
    const period = document.documentElement.dataset.annalsPeriod
      || getCurrentPeriod(new Date().getHours());
    const variant = document.documentElement.dataset.annalsImageVariant
      || getHeroImageVariant();
    const imageUrl = new URL(
      `../illustration/${periods[period].file}-${variant}.webp`,
      scriptUrl
    );

    Object.keys(periods).forEach((key) => body.classList.remove(`time-${key}`));
    body.classList.add(`time-${period}`);

    const image = new Image();
    image.decoding = "async";
    image.fetchPriority = "high";
    image.src = imageUrl.href;

    const applyImage = () => {
      hero.style.setProperty("--hero-image", `url("${imageUrl.href}")`);
      revealHero(body);
    };

    if (image.complete) applyImage();
    else {
      image.addEventListener("load", applyImage, { once: true });
      image.addEventListener("error", () => revealHero(body), { once: true });
    }

    window.setTimeout(() => revealHero(body), 180);
  }

  function enhanceAccessibility() {
    const searchDialog = document.querySelector(
      '.md-search[role="dialog"]'
    );

    if (searchDialog && !searchDialog.hasAttribute("aria-label")) {
      searchDialog.setAttribute("aria-label", "站内搜索");
    }

    document.querySelectorAll("nav.md-nav[aria-labelledby]").forEach((nav) => {
      const labelId = nav.getAttribute("aria-labelledby");
      const label = labelId ? document.getElementById(labelId) : null;
      if (label?.textContent.trim()) return;

      const title = nav.querySelector(":scope > .md-nav__title");
      const titleText = title?.textContent.trim();
      if (!titleText) return;

      nav.removeAttribute("aria-labelledby");
      nav.setAttribute("aria-label", `导航分组：${titleText}`);
    });
  }

  function synchronizeColorScheme() {
    const scheme = document.body?.dataset.mdColorScheme === "slate"
      ? "slate"
      : "default";
    const isCover = document.documentElement.dataset.annalsPage === "home";
    const canvas = isCover ? "#0c1119" : scheme === "slate" ? "#1b1819" : "#f7f1ed";
    const chrome = isCover ? "#0c1119" : scheme === "slate" ? "#242021" : "#f3ede3";
    const themeColor = document.querySelector("meta[data-annals-theme-color]");

    document.documentElement.dataset.annalsScheme = scheme;
    document.documentElement.style.colorScheme = scheme === "slate"
      ? "dark"
      : "light";
    document.documentElement.style.backgroundColor = canvas;
    if (themeColor) themeColor.content = chrome;
  }

  function observeColorScheme() {
    const body = document.body;
    if (!body || body.dataset.annalsSchemeObserver === "true") return;

    body.dataset.annalsSchemeObserver = "true";
    synchronizeColorScheme();

    new MutationObserver(synchronizeColorScheme).observe(body, {
      attributes: true,
      attributeFilter: ["data-md-color-scheme"]
    });
  }

  function initializeTocCursor() {
    document.querySelectorAll(".md-nav--secondary").forEach((toc) => {
      const cursor = toc.querySelector(":scope > .annals-toc-cursor");
      if (!cursor || toc.dataset.annalsCursorInitialized === "true") return;

      toc.dataset.annalsCursorInitialized = "true";
      let frame = 0;

      const update = () => {
        frame = 0;
        const links = [...toc.querySelectorAll(".md-nav__link[href]")]
          .filter((link) => link.offsetHeight);
        const active = toc.querySelector(".md-nav__link--active") || links[0];
        if (!active) return;

        const tocRect = toc.getBoundingClientRect();
        const activeRect = active.getBoundingClientRect();
        const height = Math.min(18, Math.max(12, activeRect.height * 0.64));
        const x = activeRect.left - tocRect.left;
        const y = activeRect.top - tocRect.top + (activeRect.height - height) / 2;
        const ready = cursor.dataset.ready === "true";

        cursor.style.setProperty("--annals-toc-cursor-height", `${height}px`);
        cursor.style.setProperty("--annals-toc-cursor-x", `${x}px`);
        cursor.style.setProperty("--annals-toc-cursor-y", `${y}px`);
        if (!ready) {
          /* Commit the first position before enabling transitions; page load should not sweep the full TOC. */
          cursor.getBoundingClientRect();
          cursor.dataset.ready = "true";
        }
      };

      const scheduleUpdate = () => {
        if (frame) return;
        frame = window.requestAnimationFrame(update);
      };

      new MutationObserver(scheduleUpdate).observe(toc, {
        attributes: true,
        attributeFilter: ["class"],
        subtree: true
      });

      if (typeof ResizeObserver !== "undefined") {
        new ResizeObserver(scheduleUpdate).observe(toc);
      }

      scheduleUpdate();
      window.setTimeout(scheduleUpdate, 280);
    });
  }

  const disclosureStates = new WeakMap();

  function getDisclosureHeight(details, open) {
    if (open) return details.scrollHeight;

    const summary = details.querySelector(":scope > summary");
    const styles = getComputedStyle(details);
    return (summary?.offsetHeight || 0)
      + parseFloat(styles.paddingBlockStart)
      + parseFloat(styles.paddingBlockEnd)
      + parseFloat(styles.borderBlockStartWidth)
      + parseFloat(styles.borderBlockEndWidth);
  }

  function animateDisclosure(details, open) {
    const state = disclosureStates.get(details) || {};
    const startHeight = details.getBoundingClientRect().height;

    if (state.animation) {
      state.animation.onfinish = null;
      state.animation.cancel();
    }
    for (const animation of state.contentAnimations || []) animation.cancel();

    if (open && !details.open) details.open = true;

    details.dataset.annalsAnimating = "true";
    details.style.height = `${startHeight}px`;
    details.style.overflow = "hidden";

    const endHeight = getDisclosureHeight(details, open);
    const distance = Math.abs(endHeight - startHeight);
    const duration = Math.round(Math.min(320, Math.max(180, 170 + distance * 0.12)));
    const animation = details.animate(
      { height: [`${startHeight}px`, `${endHeight}px`] },
      {
        duration,
        easing: "cubic-bezier(0.2, 0, 0.38, 0.9)"
      }
    );

    const contentAnimations = [...details.children]
      .filter((element) => element.tagName !== "SUMMARY")
      .map((element) => element.animate(
        open
          ? [
              { opacity: 0.35, transform: "translateY(-4px)" },
              { opacity: 1, transform: "translateY(0)" }
            ]
          : [
              { opacity: 1, transform: "translateY(0)" },
              { opacity: 0.35, transform: "translateY(-3px)" }
            ],
        {
          duration: Math.min(duration, 180),
          easing: open
            ? "cubic-bezier(0, 0, 0.38, 0.9)"
            : "cubic-bezier(0.2, 0, 1, 0.9)",
          fill: "both"
        }
      ));

    disclosureStates.set(details, {
      animation,
      contentAnimations,
      targetOpen: open
    });

    animation.onfinish = () => {
      for (const contentAnimation of contentAnimations) contentAnimation.cancel();
      if (!open) details.open = false;
      details.style.removeProperty("height");
      details.style.removeProperty("overflow");
      delete details.dataset.annalsAnimating;
      disclosureStates.delete(details);
    };
  }

  function initializeDisclosures() {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    document.querySelectorAll(".md-typeset details[class] > summary").forEach((summary) => {
      if (summary.dataset.annalsDisclosureInitialized === "true") return;
      summary.dataset.annalsDisclosureInitialized = "true";

      summary.addEventListener("click", (event) => {
        if (reducedMotion.matches || typeof summary.animate !== "function") return;

        const details = summary.parentElement;
        const state = disclosureStates.get(details);
        const targetOpen = !(state?.targetOpen ?? details.open);
        event.preventDefault();
        animateDisclosure(details, targetOpen);
      });
    });
  }

  function initializePage() {
    observeColorScheme();
    enhanceAccessibility();
    initializeHero();
    initializeTocCursor();
    initializeDisclosures();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializePage, { once: true });
  } else {
    initializePage();
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(initializePage);
  }
})();

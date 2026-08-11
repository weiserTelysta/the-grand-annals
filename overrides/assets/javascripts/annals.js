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
    const breadcrumb = document.querySelector('.md-path[aria-label="导航栏"]');

    if (searchDialog && !searchDialog.hasAttribute("aria-label")) {
      searchDialog.setAttribute("aria-label", "站内搜索");
    }

    if (breadcrumb) breadcrumb.setAttribute("aria-label", "面包屑");

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
    const canvas = isCover ? "#0c1119" : scheme === "slate" ? "#1d191a" : "#f8f4e8";
    const themeColor = document.querySelector("meta[data-annals-theme-color]");

    document.documentElement.dataset.annalsScheme = scheme;
    document.documentElement.style.colorScheme = scheme === "slate"
      ? "dark"
      : "light";
    document.documentElement.style.backgroundColor = canvas;
    if (themeColor) themeColor.content = canvas;
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

  function initializePage() {
    observeColorScheme();
    enhanceAccessibility();
    initializeHero();
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

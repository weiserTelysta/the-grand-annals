(() => {
  const FRAME_INTERVAL = 1000 / 30;
  const state = {
    animationFrame: 0,
    canvas: null,
    context: null,
    lastFrame: 0,
    particles: [],
    readingBounds: null,
    resizeFrame: 0
  };

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const desktopLayout = window.matchMedia("(min-width: 76.25em)");

  function parseColorToken(name, fallback) {
    const value = getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
    return /^\d+\s+\d+\s+\d+$/.test(value) ? value : fallback;
  }

  function sideRegions(width) {
    const shell = document.querySelector(".md-main__inner")?.getBoundingClientRect();
    if (!shell) return [];

    const safeGap = 14;
    return [
      { start: 0, end: Math.max(0, shell.left - safeGap) },
      { start: Math.min(width, shell.right + safeGap), end: width }
    ].filter((region) => region.end - region.start >= 44);
  }

  function updateReadingBounds() {
    const article = document.querySelector(".md-content__inner")?.getBoundingClientRect();
    const content = document.querySelector(".md-content")?.getBoundingClientRect();
    state.readingBounds = article && content
      ? {
          articleLeft: article.left - 24,
          articleRight: article.right + 24,
          contentLeft: content.left,
          contentRight: content.right
        }
      : null;
  }

  function randomX(width, regions, preferSides) {
    if (preferSides && regions.length) {
      const region = regions[Math.floor(Math.random() * regions.length)];
      return {
        start: region.start,
        end: region.end,
        value: region.start + Math.random() * (region.end - region.start)
      };
    }
    return { start: -24, end: width + 24, value: Math.random() * width };
  }

  function createParticles(width, height) {
    const regions = sideRegions(width);
    const count = Math.max(32, Math.min(46, Math.round(width / 48)));
    const dustLimit = Math.round(count * 0.7);
    const filamentLimit = dustLimit + Math.round(count * 0.2);

    return Array.from({ length: count }, (_, index) => {
      const kind = index < dustLimit ? "dust" : index < filamentLimit ? "filament" : "flower";
      const horizontal = randomX(width, regions, Math.random() < 0.52);
      const depth = 0.72 + Math.random() * 0.56;
      return {
        alpha: kind === "flower"
          ? 0.14 + Math.random() * 0.06
          : kind === "filament"
            ? 0.065 + Math.random() * 0.04
            : 0.055 + Math.random() * 0.035,
        color: kind === "flower" ? (index % 3 === 0 ? 2 : 0) : index % 4 === 0 ? 1 : 0,
        depth,
        kind,
        phase: Math.random() * Math.PI * 2,
        phaseSpeed: 0.00016 + Math.random() * 0.0002,
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: kind === "flower"
          ? (Math.random() < 0.5 ? -1 : 1) * (0.00009 + Math.random() * 0.00006)
          : (Math.random() - 0.5) * 0.00012,
        size: kind === "dust"
          ? 0.5 + Math.random() * 0.45
          : kind === "filament"
            ? 6 + Math.random() * 5
            : 3 + Math.random() * 2,
        twinklePhase: Math.random() * Math.PI * 2,
        twinkleSpeed: 0.00028 + Math.random() * 0.00036,
        vx: (Math.random() - 0.5) * 0.012 * depth,
        vy: (kind === "flower" ? 0.004 + Math.random() * 0.007 : -(0.006 + Math.random() * 0.015)) * depth,
        x: horizontal.value,
        xEnd: horizontal.end,
        xStart: horizontal.start,
        y: Math.random() * height
      };
    });
  }

  function readingAttenuation(x) {
    const bounds = state.readingBounds;
    if (!bounds) return 1;
    if (x >= bounds.articleLeft && x <= bounds.articleRight) return 0.2;
    if (x >= bounds.contentLeft && x <= bounds.contentRight) return 0.55;
    return 1;
  }

  function drawDust(context, particle, color, alpha) {
    const halo = particle.size * 2.6;
    const gradient = context.createRadialGradient(
      particle.x,
      particle.y,
      0,
      particle.x,
      particle.y,
      halo
    );
    gradient.addColorStop(0, `rgb(${color} / ${alpha})`);
    gradient.addColorStop(0.3, `rgb(${color} / ${alpha * 0.48})`);
    gradient.addColorStop(1, `rgb(${color} / 0)`);
    context.fillStyle = gradient;
    context.beginPath();
    context.arc(particle.x, particle.y, halo, 0, Math.PI * 2);
    context.fill();
  }

  function drawFilament(context, particle, color, alpha) {
    const length = particle.size;
    context.save();
    context.translate(particle.x, particle.y);
    context.rotate(particle.rotation);
    const gradient = context.createLinearGradient(-length / 2, 0, length / 2, 0);
    gradient.addColorStop(0, `rgb(${color} / 0)`);
    gradient.addColorStop(0.46, `rgb(${color} / ${alpha * 0.72})`);
    gradient.addColorStop(0.58, `rgb(${color} / ${alpha})`);
    gradient.addColorStop(1, `rgb(${color} / 0)`);
    context.strokeStyle = gradient;
    context.lineCap = "round";
    context.lineWidth = 0.65 + particle.depth * 0.35;
    context.beginPath();
    context.moveTo(-length / 2, 0);
    context.quadraticCurveTo(0, particle.depth * 0.65, length / 2, 0);
    context.stroke();
    context.restore();
  }

  function drawFlower(context, particle, color, alpha) {
    const size = particle.size;
    context.save();
    context.translate(particle.x, particle.y);
    context.rotate(particle.rotation);
    context.fillStyle = `rgb(${color} / ${alpha})`;
    context.font = `${size * 2.8}px "Segoe UI Symbol", "Noto Sans Symbols 2", serif`;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText("❀", 0, 0);
    context.restore();
  }

  function sizeCanvas() {
    if (!state.canvas || !state.context || !desktopLayout.matches) return;

    const box = state.canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
    state.canvas.width = Math.max(1, Math.round(box.width * ratio));
    state.canvas.height = Math.max(1, Math.round(box.height * ratio));
    state.context.setTransform(ratio, 0, 0, ratio, 0, 0);
    updateReadingBounds();
    state.particles = createParticles(box.width, box.height);
    const mix = state.particles.reduce((counts, particle) => {
      counts[particle.kind] += 1;
      return counts;
    }, { dust: 0, filament: 0, flower: 0 });
    state.canvas.dataset.annalsEffect = "heraldic-field";
    state.canvas.dataset.annalsFrameRate = "30";
    state.canvas.dataset.annalsParticleCount = String(state.particles.length);
    state.canvas.dataset.annalsParticleMix = `${mix.dust}/${mix.filament}/${mix.flower}`;
    state.canvas.dataset.annalsParticleShapes = "dust/filament/flower-u2740";
    state.canvas.dataset.annalsFlowerMotion = "continuous-rotation";
    state.canvas.dataset.annalsReadingIntensity = "0.2";
  }

  function queueFrame() {
    if (!reducedMotion.matches && !document.hidden) {
      state.animationFrame = window.requestAnimationFrame(draw);
    }
  }

  function draw(timestamp = 0) {
    if (!state.context || !state.canvas) return;
    if (state.lastFrame && timestamp - state.lastFrame < FRAME_INTERVAL) {
      queueFrame();
      return;
    }

    const box = state.canvas.getBoundingClientRect();
    const colors = [
      parseColorToken("--annals-dust-primary", "126 82 72"),
      parseColorToken("--annals-dust-secondary", "169 137 91"),
      parseColorToken("--annals-dust-glint", "192 160 94")
    ];
    const elapsed = state.lastFrame ? Math.min(67, timestamp - state.lastFrame) : FRAME_INTERVAL;
    state.lastFrame = timestamp;
    state.context.clearRect(0, 0, box.width, box.height);

    for (const particle of state.particles) {
      particle.phase += particle.phaseSpeed * elapsed;
      particle.rotation += particle.rotationSpeed * elapsed;
      particle.twinklePhase += particle.twinkleSpeed * elapsed;
      const curve = particle.kind === "flower" ? 0.01 : 0.008;
      particle.x += (particle.vx + Math.sin(particle.phase) * curve * particle.depth) * elapsed;
      particle.y += particle.vy * elapsed;

      if (particle.y < -24) particle.y = box.height + 24;
      if (particle.y > box.height + 24) particle.y = -24;
      if (particle.x < particle.xStart) particle.x = particle.xEnd;
      if (particle.x > particle.xEnd) particle.x = particle.xStart;

      const wave = (Math.sin(particle.twinklePhase) + 1) / 2;
      const twinkle = particle.kind === "flower"
        ? 0.52 + wave * 0.48
        : 0.66 + wave * 0.34;
      const alpha = particle.alpha * twinkle * readingAttenuation(particle.x);
      const color = colors[particle.color];

      if (particle.kind === "dust") drawDust(state.context, particle, color, alpha);
      else if (particle.kind === "filament") drawFilament(state.context, particle, color, alpha);
      else drawFlower(state.context, particle, color, alpha);
    }

    const flower = state.particles.find((particle) => particle.kind === "flower");
    if (flower) state.canvas.dataset.annalsFlowerAngle = flower.rotation.toFixed(4);
    state.canvas.dataset.annalsPainted = "true";
    queueFrame();
  }

  function stop() {
    if (state.animationFrame) window.cancelAnimationFrame(state.animationFrame);
    state.animationFrame = 0;
    state.lastFrame = 0;
  }

  function restart() {
    stop();
    if (!state.canvas || !desktopLayout.matches || reducedMotion.matches) return;
    sizeCanvas();
    queueFrame();
  }

  function removeCanvas() {
    stop();
    state.canvas?.remove();
    state.canvas = null;
    state.context = null;
    state.particles = [];
  }

  function initializeAmbientField() {
    const isReadingPage = document.documentElement.dataset.annalsPage === "content";
    if (!isReadingPage || !desktopLayout.matches) {
      removeCanvas();
      return;
    }

    if (!state.canvas?.isConnected) {
      state.canvas = document.createElement("canvas");
      state.canvas.className = "annals-dust";
      state.canvas.setAttribute("aria-hidden", "true");
      document.querySelector(".md-container")?.prepend(state.canvas);
      state.context = state.canvas.getContext("2d", { alpha: true });
    }

    restart();
  }

  window.addEventListener("resize", () => {
    if (state.resizeFrame) return;
    state.resizeFrame = window.requestAnimationFrame(() => {
      state.resizeFrame = 0;
      initializeAmbientField();
    });
  }, { passive: true });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else restart();
  });

  reducedMotion.addEventListener?.("change", restart);
  desktopLayout.addEventListener?.("change", initializeAmbientField);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAmbientField, { once: true });
  } else {
    initializeAmbientField();
  }

  if (typeof document$ !== "undefined") document$.subscribe(initializeAmbientField);
})();

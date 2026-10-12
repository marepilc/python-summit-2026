/* Silnik prezentacji: nawigacja, kroki i animacje wykresów.
   Animacje czytają klasy i atrybuty data-* zapisane w SVG przez pyDreamplet
   (np. data-dy = przesunięcie etykiety przez algorytm kolizji). */
(() => {
  "use strict";
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const D = (ms) => (REDUCED ? 0 : ms);
  const EASE = "cubic-bezier(.2,.7,.1,1)";

  const stage = document.querySelector(".stage");
  const slides = [...document.querySelectorAll(".slide")];
  const progress = document.querySelector(".progress");
  const numEl = document.querySelector(".chrome .num");
  const sectionEl = document.querySelector(".chrome .section");
  // stopka jak w szablonie PYS26: „numer · sekcja”; sekcja = tytuł ostatniego slajdu „Krok N z 4”
  const DEFAULT_SECTION = sectionEl?.textContent || "";
  let lastSection = DEFAULT_SECTION;
  const sectionOf = slides.map((s) => {
    if (s.querySelector(".center > .kicker") && s.classList.contains("dark")) lastSection = s.querySelector("h1")?.textContent.trim() || lastSection;
    return s.dataset.section || lastSection;
  });
  let idx = 0, step = 0, running = [];

  // ---------------------------------------------------------------- skalowanie sceny
  function fit() {
    const s = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = `translate(-50%, -50%) scale(${s})`;
  }
  addEventListener("resize", fit);
  fit();

  // ---------------------------------------------------------------- kod bez łamania linii
  // Kod na slajdzie nigdy się nie zawija (zawinięty Python jest niepoprawny wizualnie):
  // gdy linia nie mieści się w ramce, zmniejszamy font bloku, maksymalnie do 15 px.
  function fitCode(root = document) {
    root.querySelectorAll("pre.code").forEach((pre) => {
      if (!pre.clientWidth) return; // ukryty (krok jeszcze nie pokazany) — dopasujemy po pokazaniu
      pre.style.fontSize = "";
      let size = parseFloat(getComputedStyle(pre).fontSize);
      while (pre.scrollWidth > pre.clientWidth + 1 && size > 15) {
        size -= 0.5;
        pre.style.fontSize = `${size}px`;
      }
    });
  }

  // ---------------------------------------------------------------- narzędzia animacji
  function anim(el, frames, opts) {
    const a = el.animate(frames, { duration: D(opts.duration ?? 600), delay: D(opts.delay ?? 0),
      easing: opts.easing ?? EASE, fill: "both" });
    running.push(a);
    return a;
  }
  function tween(ms, fn, delay = 0) {
    if (REDUCED || ms === 0) { fn(1); return; }
    const t0 = performance.now() + delay;
    let alive = true;
    running.push({ cancel: () => { alive = false; }, finish: () => { alive = false; fn(1); } });
    const tick = (now) => {
      if (!alive) return;
      const t = Math.min(1, Math.max(0, (now - t0) / ms));
      fn(1 - Math.pow(1 - t, 3));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  // WAAPI: cancel (stan końcowy = naturalny stan elementu); tweeny: finish (ustawiają wartość końcową)
  function stopAll() {
    running.forEach((a) => { try { (typeof Animation !== "undefined" && a instanceof Animation) ? a.cancel() : a.finish(); } catch (_) {} });
    running = [];
  }
  const $$ = (root, sel) => [...root.querySelectorAll(sel)];
  const setVis = (els, v) => els.forEach((e) => { e.style.opacity = v ? "" : "0"; });
  function drawLine(path, opts = {}) {
    const len = path.getTotalLength();
    path.style.strokeDasharray = `${len}`;
    return anim(path, [{ strokeDashoffset: len }, { strokeDashoffset: 0 }], opts);
  }
  function clipReveal(svg, group, ms, delay = 0) {
    // odsłanianie od lewej: clipPath z prostokątem, którego szerokość rośnie
    const NS = "http://www.w3.org/2000/svg";
    let cp = svg.querySelector("clipPath.reveal");
    const vb = svg.viewBox.baseVal;
    if (!cp) {
      cp = document.createElementNS(NS, "clipPath");
      cp.setAttribute("class", "reveal");
      cp.id = "rv" + Math.random().toString(36).slice(2, 8);
      const r = document.createElementNS(NS, "rect");
      r.setAttribute("x", "0"); r.setAttribute("y", "-50"); r.setAttribute("height", String(vb.height + 100));
      cp.appendChild(r);
      svg.insertBefore(cp, svg.firstChild);
    }
    const rect = cp.firstChild;
    group.setAttribute("clip-path", `url(#${cp.id})`);
    rect.setAttribute("width", "0");
    tween(ms, (t) => rect.setAttribute("width", String(t * vb.width)), D(delay));
  }
  function countUp(el, delay = 0) {
    const to = parseFloat(el.dataset.to), digits = +(el.dataset.digits || 0);
    const pre = el.dataset.prefix || "", suf = el.dataset.suffix || "";
    const fmt = (v) => pre + v.toFixed(digits).replace(".", ",") + suf;
    el.textContent = fmt(0);
    tween(1400, (t) => { el.textContent = fmt(to * t); }, D(delay));
  }

  // ---------------------------------------------------------------- kontrolery wykresów
  // f(root, step, animate) — ustawia stan dla danego kroku; animate=false przy cofaniu.
  const C = {};

  C.stripes = (root, _s, animate) => {
    const rects = $$(root, ".stripe");
    if (!animate) return;
    rects.forEach((r, i) => {
      r.style.transformBox = "fill-box"; r.style.transformOrigin = "bottom";
      anim(r, [{ opacity: 0, transform: "scaleY(.15)" }, { opacity: 1, transform: "scaleY(1)" }],
        { duration: 700, delay: 200 + i * 38 });
    });
  };

  C.mix = (root, s, animate) => {
    const svg = root.querySelector("svg");
    const marks = svg.querySelector(".marks");
    const layers = $$(svg, ".layer"), gaps = $$(svg, ".gap");
    const labels = $$(svg, "g.label"), leaders = $$(svg, ".leader"), annots = $$(svg, ".annot");
    // krok 1: warstwy
    if (s >= 1) {
      if (animate && s === 1) clipReveal(svg, marks, 1600);
      else { marks.removeAttribute("clip-path"); }
    } else { clipReveal(svg, marks, 0); svg.querySelector("clipPath.reveal rect")?.setAttribute("width", "0"); }
    // krok 2: szczeliny w kolorze papieru
    gaps.forEach((g, i) => {
      g.style.opacity = s >= 2 ? "" : "0";
      if (s === 2 && animate) drawLine(g, { duration: 900, delay: i * 90 });
    });
    // krok 3: etykiety w miejscu kotwic (jeszcze nachodzą na siebie)
    labels.forEach((g) => {
      const dy = parseFloat(g.dataset.dy || "0");
      g.style.opacity = s >= 3 ? "" : "0";
      g.style.transform = s === 3 ? `translateY(${dy}px)` : "";
      if (s === 3 && animate) anim(g, [{ opacity: 0 }, { opacity: 1 }], { duration: 500 });
      if (s === 4 && animate) {
        anim(g, [{ transform: `translateY(${dy}px)` }, { transform: "translateY(0)" }],
          { duration: 900, delay: 250, easing: "cubic-bezier(.5,0,.1,1)" });
      }
    });
    // krok 4: łączniki
    leaders.forEach((l) => {
      l.style.opacity = s >= 4 ? "" : "0";
      if (s === 4 && animate) drawLine(l, { duration: 600, delay: 900 });
    });
    // krok 5: adnotacje
    annots.forEach((a, i) => {
      a.style.opacity = s >= 5 ? "" : "0";
      if (s === 5 && animate) {
        anim(a, [{ opacity: 0, transform: "translateY(-14px)" }, { opacity: 1, transform: "none" }],
          { duration: 600, delay: i * 250 });
      }
    });
  };

  C.dumbbell = (root, _s, animate) => {
    if (!animate) return;
    $$(root, "g.row").forEach((row, i) => {
      const dx = parseFloat(row.dataset.dx || "0");
      const end = row.querySelector(".end"), stem = row.querySelector(".stem");
      const delay = 300 + i * 70;
      anim(end, [{ transform: `translateX(${dx}px)` }, { transform: "translateX(0)" }],
        { duration: 1100, delay, easing: "cubic-bezier(.6,0,.15,1)" });
      stem.style.transformBox = "fill-box"; stem.style.transformOrigin = "right";
      anim(stem, [{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }],
        { duration: 1100, delay, easing: "cubic-bezier(.6,0,.15,1)" });
    });
  };

  C.ranking = (root, _s, animate) => {
    if (!animate) return;
    $$(root, ".bar").forEach((b, i) => {
      b.style.transformBox = "fill-box"; b.style.transformOrigin = "left";
      anim(b, [{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], { duration: 900, delay: 300 + i * 35 });
    });
  };

  C.multiples = (root, _s, animate) => {
    if (!animate) return;
    $$(root, ".line").forEach((l) => drawLine(l, { duration: 1800, delay: 300 + 250 * +l.dataset.panel,
      easing: "cubic-bezier(.45,0,.2,1)" }));
    $$(root, ".wash").forEach((w) => anim(w, [{ opacity: 0 }, { opacity: 1 }],
      { duration: 900, delay: 1300 + 250 * +w.dataset.panel }));
    $$(root, ".end, .value").forEach((e) => anim(e, [{ opacity: 0 }, { opacity: 1 }],
      { duration: 400, delay: 2100 + 250 * +e.dataset.panel }));
  };

  C.waffle = (root, _s, animate) => {
    if (!animate) return;
    $$(root, ".cell").forEach((c) => {
      c.style.transformBox = "fill-box"; c.style.transformOrigin = "center";
      anim(c, [{ opacity: 0, transform: "scale(.2)" }, { opacity: 1, transform: "scale(1)" }],
        { duration: 450, delay: 200 + 16 * +c.dataset.i, easing: "cubic-bezier(.3,1.4,.5,1)" });
    });
  };

  C.pipeline = (root, _s, animate) => {
    if (!animate) return;
    $$(root, "[data-seq]").forEach((el) => {
      const n = +el.dataset.seq;
      // linie przerywane (data.json) tylko wjeżdżają — rysowanie nadpisałoby wzór kresek
      if (el.matches("path") && !el.hasAttribute("stroke-dasharray")) drawLine(el, { duration: 600, delay: 250 + n * 260 });
      else anim(el, [{ opacity: 0, transform: "translateY(10px)" }, { opacity: 1, transform: "none" }],
        { duration: 500, delay: 250 + n * 260 });
    });
  };

  C.swatches = (root, _s, animate) => {
    if (!animate) return;
    $$(root, ".sw .bar").forEach((b, i) => anim(b, [{ transform: "scaleY(0)" }, { transform: "scaleY(1)" }],
      { duration: 900, delay: 200 + i * 110 }));
  };

  C.count = (root, _s, animate) => {
    $$(root, ".count").forEach((el, i) => {
      if (animate) countUp(el, 300 + i * 200);
      else el.textContent = (el.dataset.prefix || "") + (+el.dataset.to).toFixed(+(el.dataset.digits || 0)).replace(".", ",") + (el.dataset.suffix || "");
    });
  };

  C.stagger = (root, _s, animate) => {
    if (!animate) return;
    $$(root, "[data-stagger]").forEach((el, i) => anim(el,
      [{ opacity: 0, transform: "translateY(18px)" }, { opacity: 1, transform: "none" }],
      { duration: 600, delay: 150 + i * 90 }));
  };

  C.pages = (root, _s, animate) => {
    const imgs = $$(root, ".pages img");
    const n = imgs.length;
    imgs.forEach((img, i) => {
      const rot = (i - (n - 1) / 2) * 4, x = 80 + i * 330, y = Math.abs(i - (n - 1) / 2) * 22;
      const final = `translate(${x}px, ${y}px) rotate(${rot}deg)`;
      img.style.transform = final;
      if (animate) anim(img, [{ opacity: 0, transform: `translate(${80 + (n - 1) * 165}px, 140px) rotate(0deg)` },
        { opacity: 1, transform: final }], { duration: 1100, delay: 200 + i * 140, easing: "cubic-bezier(.3,1.15,.4,1)" });
    });
  };

  // ---------------------------------------------------------------- „jedna linijka”: zmiana akcentu na żywo
  const BASE_ACCENT = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim().toUpperCase();
  let currentAccent = BASE_ACCENT;
  function setAccent(hex) {
    hex = hex.toUpperCase();
    document.querySelectorAll("svg [fill], svg [stroke]").forEach((el) => {
      ["fill", "stroke"].forEach((a) => { if ((el.getAttribute(a) || "").toUpperCase() === currentAccent) el.setAttribute(a, hex); });
    });
    document.documentElement.style.setProperty("--accent", hex);
    document.querySelectorAll("[data-accent-code]").forEach((el) => { el.textContent = `"${hex}"`; });
    document.querySelectorAll(".swatch-btns button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.c.toUpperCase() === hex)));
    currentAccent = hex;
  }
  // Każdy krok slajdu (klik / strzałka) to kolejny kolor z kółek, ostatni krok wraca do bazowego.
  // Kliknięcie kółka ustawia kolor ręcznie; wyjście ze slajdu przywraca bazowy.
  document.querySelectorAll(".swatch-btns button").forEach((b) => b.addEventListener("click", (e) => {
    e.stopPropagation(); setAccent(b.dataset.c);
  }));
  C.accentsteps = (root, s) => {
    const seq = [...$$(root, ".swatch-btns button")].map((b) => b.dataset.c.toUpperCase())
      .filter((c) => c !== BASE_ACCENT).concat(BASE_ACCENT);
    setAccent(s > 0 ? seq[Math.min(s, seq.length) - 1] : BASE_ACCENT);
    const reset = () => setAccent(BASE_ACCENT);
    running.push({ cancel: reset, finish: reset });
  };

  // ---------------------------------------------------------------- nawigacja
  const maxStep = (s) => +(s.dataset.steps || 0);
  function applySteps(slide, s) {
    $$(slide, "[data-step]").forEach((el) => el.classList.toggle("on", s >= +el.dataset.step));
    // data-only="2 3" — widoczny tylko w tych krokach; data-current — wyróżniony w tych krokach
    const inList = (v) => v.split(" ").map(Number).includes(s);
    $$(slide, "[data-only]").forEach((el) => el.classList.toggle("on", inList(el.dataset.only)));
    $$(slide, "[data-current]").forEach((el) => el.classList.toggle("current", inList(el.dataset.current)));
  }
  function runControllers(slide, s, animate) {
    [slide, ...$$(slide, "[data-ctrl]")].filter((el) => el.dataset.ctrl).forEach((el) => el.dataset.ctrl.split(" ").forEach((k) => C[k]?.(el, s, animate)));
  }
  function render(newIdx, newStep, animate) {
    stopAll();
    const changed = newIdx !== idx || !slides[newIdx].classList.contains("active");
    slides.forEach((s, i) => s.classList.toggle("active", i === newIdx));
    idx = newIdx; step = newStep;
    const slide = slides[idx];
    stage.classList.toggle("on-dark", slide.classList.contains("dark"));
    stage.classList.toggle("on-brand", slide.classList.contains("brand"));
    applySteps(slide, step);
    fitCode(slide);
    runControllers(slide, step, animate && (changed || maxStep(slide) > 0));
    progress.style.width = `${((idx + 1) / slides.length) * 100}%`;
    numEl.textContent = String(idx + 1);
    if (sectionEl) sectionEl.textContent = sectionOf[idx];
    try { history.replaceState(null, "", `#${idx + 1}${step ? "." + step : ""}`); } catch (_) {}
  }
  function next() {
    const s = slides[idx];
    if (step < maxStep(s)) render(idx, step + 1, true);
    else if (idx < slides.length - 1) render(idx + 1, 0, true);
  }
  function prev() {
    if (step > 0) render(idx, step - 1, false);
    else if (idx > 0) render(idx - 1, maxStep(slides[idx - 1]), false);
  }
  function go(i) { render(Math.max(0, Math.min(slides.length - 1, i)), 0, true); }

  addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"].includes(k)) { e.preventDefault(); next(); }
    else if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(k)) { e.preventDefault(); prev(); }
    else if (k === "Home") go(0);
    else if (k === "End") go(slides.length - 1);
    else if (k === "f" || k === "F") {
      if (document.fullscreenElement) document.exitFullscreen?.();
      else document.documentElement.requestFullscreen?.().catch(() => {});
    } else if (k === "r" || k === "R") render(idx, step, true); // powtórz animację
  });
  stage.addEventListener("click", (e) => {
    if (e.target.closest("a, button")) return;
    (e.clientX < innerWidth * 0.25 ? prev : next)();
  });
  let touchX = null;
  addEventListener("touchstart", (e) => { touchX = e.touches[0].clientX; }, { passive: true });
  addEventListener("touchend", (e) => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) (dx < 0 ? next : prev)();
    touchX = null;
  });

  // ---------------------------------------------------------------- start
  const help = document.querySelector(".help");
  setTimeout(() => { if (help) help.style.opacity = "0"; }, 4000);
  // #15 = slajd 15, #15.3 = slajd 15 w kroku 3 (próby, zrzuty)
  const [hSlide, hStep] = (location.hash || "").replace("#", "").split(".").map((x) => parseInt(x, 10));
  const start = Math.max(0, Math.min(slides.length - 1, Number.isFinite(hSlide) ? hSlide - 1 : 0));
  const startStep = Number.isFinite(hStep) ? Math.max(0, Math.min(maxStep(slides[start]), hStep)) : 0;
  // fonty muszą być gotowe, zanim zmierzymy ścieżki i ruszymy z animacją
  (document.fonts?.ready || Promise.resolve()).then(() => fitCode() || render(start, startStep, true));
})();

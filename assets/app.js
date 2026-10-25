// Switzerland 2027: shared behaviour (theme, reveal animations, deck navigation, filters)
(function () {
  window.__ch27 = true; // tells the inline failsafe in <head> that animations are running
  const root = document.documentElement;

  // ---------- theme toggle (remembered per browser, optional) ----------
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
  };
  const saved = store.get("ch27-theme");
  if (saved) root.setAttribute("data-theme", saved);
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dark = root.getAttribute("data-theme")
        ? root.getAttribute("data-theme") === "dark"
        : matchMedia("(prefers-color-scheme: dark)").matches;
      const next = dark ? "light" : "dark";
      root.setAttribute("data-theme", next);
      store.set("ch27-theme", next);
    });
  });

  // ---------- top bar + progress ----------
  const bar = document.querySelector(".topbar");
  const progress = document.querySelector(".progress");
  function onScroll() {
    const y = window.scrollY;
    const max = document.documentElement.scrollHeight - innerHeight;
    if (progress) progress.style.width = (max > 0 ? (y / max) * 100 : 0) + "%";
    if (bar) bar.classList.toggle("solid", y > innerHeight * 0.6);
  }
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // ---------- animated counters ----------
  function countUp(el) {
    if (el.dataset.done) return;
    el.dataset.done = "1";
    const target = Number(el.dataset.count);
    const prefix = el.dataset.prefix || "";
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fmt = (n) => prefix + Math.round(n).toLocaleString("en-US").replace(/,/g, " ");
    if (reduce) { el.textContent = fmt(target); return; }
    const t0 = performance.now(), dur = 1400;
    (function tick(t) {
      const p = Math.min(1, (t - t0) / dur);
      el.textContent = fmt(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(tick);
    })(t0);
  }

  // ---------- reveal on view ----------
  // Each animated element is observed on its own, so tall slides on phones still reveal everything.
  const reveals = document.querySelectorAll(".reveal");
  const show = (el) => {
    el.classList.add("in");
    el.querySelectorAll("[data-count]").forEach(countUp);
  };
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        show(e.target);
        io.unobserve(e.target);
      });
    }, { threshold: 0, rootMargin: "0px 0px -6% 0px" });
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach(show);
  }

  // ---------- deck navigation ----------
  const slides = Array.from(document.querySelectorAll(".slide"));
  if (slides.length) {
    const dots = document.querySelector(".dots");
    const count = document.querySelector(".count");
    slides.forEach((s, i) => {
      if (!dots) return;
      const a = document.createElement("a");
      a.href = "#" + s.id;
      a.title = s.dataset.title || "Slide " + (i + 1);
      a.setAttribute("aria-label", a.title);
      dots.appendChild(a);
    });
    let current = 0;
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        current = slides.indexOf(e.target);
        if (count) count.textContent = current + 1 + " / " + slides.length;
        if (dots) Array.from(dots.children).forEach((d, i) => d.classList.toggle("on", i === current));
      });
    }, { threshold: 0.5 });
    slides.forEach((s) => spy.observe(s));
    const go = (d) => {
      const i = Math.max(0, Math.min(slides.length - 1, current + d));
      slides[i].scrollIntoView({ behavior: "smooth" });
    };
    addEventListener("keydown", (e) => {
      if (e.target.closest("input, select, textarea")) return;
      if (["ArrowDown", "PageDown", "ArrowRight"].includes(e.key) || (e.key === " " && !e.shiftKey)) { e.preventDefault(); go(1); }
      if (["ArrowUp", "PageUp", "ArrowLeft"].includes(e.key) || (e.key === " " && e.shiftKey)) { e.preventDefault(); go(-1); }
    });
    document.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => go(Number(b.dataset.go))));
  }

  // ---------- overview filters & sorting ----------
  const grid = document.querySelector(".cards");
  if (grid) {
    const cards = Array.from(grid.children);
    const chips = document.querySelectorAll("[data-filter]");
    chips.forEach((c) => c.addEventListener("click", () => {
      chips.forEach((x) => x.setAttribute("aria-pressed", String(x === c)));
      const f = c.dataset.filter;
      cards.forEach((card) => {
        const ok = f === "all" || card.dataset.tags.split(" ").includes(f);
        card.classList.toggle("hidden", !ok);
      });
    }));
    const sel = document.querySelector("#sort");
    if (sel) sel.addEventListener("change", () => {
      const key = sel.value;
      const sorted = cards.slice().sort((a, b) => Number(a.dataset[key]) - Number(b.dataset[key]));
      sorted.forEach((c) => grid.appendChild(c));
    });
  }
})();

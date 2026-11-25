// Shared code for every page: data loading, CSV parsing, dates, and SVG charts.
"use strict";

const JW = (() => {
  // ---------- service worker (installable app + offline) ----------
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
  }
  const setOffline = () => document.documentElement.classList.toggle("offline", !navigator.onLine);
  window.addEventListener("online", setOffline);
  window.addEventListener("offline", setOffline);
  document.addEventListener("DOMContentLoaded", setOffline);

  // ---------- CSV (RFC 4180: quoted fields, doubled quotes, newlines in quotes) ----------
  function parseCSV(text) {
    const rows = [];
    let row = [], field = "", i = 0, inQuotes = false;
    while (i < text.length) {
      const c = text[i];
      if (inQuotes) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
          inQuotes = false; i++; continue;
        }
        field += c; i++; continue;
      }
      if (c === '"') { inQuotes = true; i++; continue; }
      if (c === ",") { row.push(field); field = ""; i++; continue; }
      if (c === "\r") { i++; continue; }
      if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; i++; continue; }
      field += c; i++;
    }
    if (field !== "" || row.length) { row.push(field); rows.push(row); }
    const header = rows.shift() || [];
    return rows.filter(r => r.length === header.length).map(r => {
      const o = {};
      header.forEach((h, k) => { o[h] = r[k]; });
      o.in_role = o.in_role === "true";
      o.first_run = o.first_run === "true";
      return o;
    });
  }

  // The service worker answers from the network when online and from its cache when offline.
  async function loadStatus() {
    const r = await fetch("data/status.json", { cache: "no-cache" });
    if (!r.ok) throw new Error("status.json " + r.status);
    return r.json();
  }
  async function loadHistory() {
    const r = await fetch("data/history.csv", { cache: "no-cache" });
    if (!r.ok) throw new Error("history.csv " + r.status);
    return parseCSV(await r.text());
  }

  // ---------- dates (all YYYY-MM-DD UTC strings) ----------
  const toMs = d => Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10));
  const daysBetween = (a, b) => Math.round((toMs(b) - toMs(a)) / 86400000);
  const addDays = (d, n) => new Date(toMs(d) + n * 86400000).toISOString().slice(0, 10);
  function dateRange(a, b) {
    const out = [];
    for (let d = a; d <= b; d = addDays(d, 1)) out.push(d);
    return out;
  }
  const lastRunDate = rows => rows.reduce((m, r) => (r.last_seen > m ? r.last_seen : m), "");
  const shortDate = d => new Date(toMs(d)).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
  const fmtTime = iso => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) + " (" + iso.replace("T", " ").replace("Z", " UTC") + ")";
  };
  const nf = new Intl.NumberFormat();
  const fmt = n => nf.format(n);
  const pct = x => (x * 100).toFixed(1) + "%";
  function median(arr) {
    if (!arr.length) return null;
    const s = [...arr].sort((a, b) => a - b), m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }

  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = u => (/^https?:\/\//i.test(u || "") ? u : "#");

  function postingItem(r, extra = "") {
    return `<li><div class="p-main"><a class="p-title" href="${esc(safeUrl(r.url))}" target="_blank" rel="noopener">${esc(r.title)}</a>` +
      (r.in_role ? `<span class="badge">Credit role</span>` : "") +
      `<div class="p-meta">${esc(r.employer)}${r.location ? " · " + esc(r.location) : ""}${extra}</div></div></li>`;
  }

  function showError(el, err) {
    el.innerHTML = `<div class="card"><strong>Could not load the data.</strong> <span class="muted">${esc(err.message || err)}</span></div>`;
  }

  // ---------- charts (plain SVG with hover tooltips) ----------
  // Axis max for counts: 4 gridline steps, each a whole "nice" number.
  function niceMax(v) {
    const raw = Math.max(1, Math.ceil(v / 4));
    const p = Math.pow(10, Math.floor(Math.log10(raw))), n = raw / p;
    const step = Math.max(1, (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p);
    return Math.ceil(step) * 4;
  }
  // Charts are drawn at the container's real pixel width so text stays 11px,
  // and redrawn when the window is resized.
  const charts = new Set();
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => charts.forEach(draw => draw()), 150);
  });
  function register(draw) { charts.add(draw); draw(); }
  const widthOf = el => Math.max(260, Math.round(el.clientWidth || 640));
  function attachTooltip(container) {
    const tip = document.createElement("div");
    tip.className = "tooltip";
    container.appendChild(tip);
    container.querySelectorAll("[data-tip]").forEach(el => {
      const show = () => {
        const box = el.getBoundingClientRect(), host = container.getBoundingClientRect();
        tip.textContent = el.getAttribute("data-tip");
        tip.style.display = "block";
        tip.style.left = Math.min(Math.max(box.left + box.width / 2 - host.left, 60), host.width - 60) + "px";
        tip.style.top = (box.top - host.top) + "px";
        el.classList.add("hl");
      };
      const hide = () => { tip.style.display = "none"; el.classList.remove("hl"); };
      el.addEventListener("mouseenter", show);
      el.addEventListener("mouseleave", hide);
      el.addEventListener("focus", show);
      el.addEventListener("blur", hide);
    });
  }

  // Vertical bars over a list of categories (e.g. dates). data: [{label, value, tip}]
  function columnChart(container, data, opts = {}) {
    register(() => drawColumns(container, data, opts));
  }
  function drawColumns(container, data, { cls = "s1", height = 220, valueLabel = "" } = {}) {
    const W = widthOf(container), H = height, m = { t: 12, r: 8, b: 28, l: 40 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const max = niceMax(Math.max(1, ...data.map(d => d.value)));
    const step = iw / Math.max(1, data.length), bw = Math.max(2, Math.min(36, step - 2));
    let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(valueLabel)}">`;
    for (let k = 0; k <= 4; k++) {
      const v = (max / 4) * k, y = m.t + ih - (v / max) * ih;
      s += `<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${y}" y2="${y}"/>`;
      s += `<text x="${m.l - 6}" y="${y + 4}" text-anchor="end">${fmt(v)}</text>`;
    }
    const every = Math.ceil(data.length / Math.max(2, Math.floor(iw / 60)));
    data.forEach((d, i) => {
      const x = m.l + i * step + (step - bw) / 2, h = (d.value / max) * ih, y = m.t + ih - h;
      if (h > 0) {
        const r = Math.min(4, bw / 2, h);
        // rounded top, square base anchored to the baseline
        s += `<path class="bar ${cls}" tabindex="0" data-tip="${esc(d.tip || d.label + ": " + fmt(d.value))}" d="M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + bw - r}Q${x + bw},${y} ${x + bw},${y + r}V${y + h}Z"/>`;
      } else {
        s += `<rect x="${x}" y="${m.t}" width="${bw}" height="${ih}" fill="transparent" tabindex="0" data-tip="${esc(d.tip || d.label + ": 0")}"/>`;
      }
      if (i % every === 0) s += `<text x="${x + bw / 2}" y="${H - 8}" text-anchor="middle">${esc(d.short || d.label)}</text>`;
    });
    s += `<line class="axis" x1="${m.l}" x2="${W - m.r}" y1="${m.t + ih}" y2="${m.t + ih}"/></svg>`;
    container.innerHTML = s;
    attachTooltip(container);
  }

  // Horizontal bars, one row per category. data: [{label, value}]
  function barChart(container, data, opts = {}) {
    register(() => drawBars(container, data, opts));
  }
  function drawBars(container, data, { cls = "s1", valueLabel = "" } = {}) {
    const row = 26, W = widthOf(container), labelW = Math.min(210, Math.round(W * 0.4)), m = { t: 4, r: 56, b: 4 };
    const maxChars = Math.max(10, Math.floor(labelW / 6.5));
    const H = m.t + m.b + row * data.length, iw = W - labelW - m.r;
    const max = Math.max(1, ...data.map(d => d.value));
    let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(valueLabel)}">`;
    data.forEach((d, i) => {
      const y = m.t + i * row, w = Math.max(0, (d.value / max) * iw), bh = row - 8;
      const label = d.label.length > maxChars ? d.label.slice(0, maxChars - 1) + "…" : d.label;
      s += `<text x="${labelW - 8}" y="${y + bh / 2 + 8}" text-anchor="end">${esc(label)}</text>`;
      if (w > 0) {
        const r = Math.min(4, bh / 2, w);
        s += `<path class="bar ${cls}" tabindex="0" data-tip="${esc(d.label + ": " + fmt(d.value))}" d="M${labelW},${y + 4}H${labelW + w - r}Q${labelW + w},${y + 4} ${labelW + w},${y + 4 + r}V${y + 4 + bh - r}Q${labelW + w},${y + 4 + bh} ${labelW + w - r},${y + 4 + bh}H${labelW}Z"/>`;
      }
      s += `<text class="label-strong" x="${labelW + w + 6}" y="${y + bh / 2 + 8}">${fmt(d.value)}</text>`;
    });
    s += `</svg>`;
    container.innerHTML = s;
    attachTooltip(container);
  }

  function tableView(rows, headers) {
    return `<details class="table-view"><summary>Show as table</summary><div class="table-wrap"><table><thead><tr>${headers.map((h, i) => `<th class="${i ? "num" : ""}">${esc(h)}</th>`).join("")}</tr></thead><tbody>` +
      rows.map(r => `<tr>${r.map((c, i) => `<td class="${i ? "num" : ""}">${esc(typeof c === "number" ? fmt(c) : c)}</td>`).join("")}</tr>`).join("") +
      `</tbody></table></div></details>`;
  }

  return { parseCSV, loadStatus, loadHistory, toMs, daysBetween, addDays, dateRange, lastRunDate, shortDate, fmtTime,
           fmt, pct, median, esc, safeUrl, postingItem, showError, columnChart, barChart, tableView, attachTooltip };
})();

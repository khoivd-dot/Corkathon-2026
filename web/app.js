// Imports check: renders the decision engine's answer. Data is written with textContent only.
// Everything the user types lives in this page's memory: no storage, no cookies, nothing in the URL.
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var SVGNS = "http://www.w3.org/2000/svg";
  function el(tag, text, cls) { var n = document.createElement(tag); if (text != null && text !== "") n.textContent = text; if (cls) n.className = cls; return n; }
  function sv(tag, attrs) { var n = document.createElementNS(SVGNS, tag); for (var k in attrs) n.setAttribute(k, attrs[k]); return n; }
  var UK = "Europe/London";
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  // ---------- Icons (built as DOM, never as HTML strings) ----------
  function icon(kind) {
    var s = sv("svg", { viewBox: "0 0 20 20", "aria-hidden": "true", focusable: "false" });
    var st = { fill: "none", stroke: "currentColor", "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round" };
    function p(d) { var n = sv("path", st); n.setAttribute("d", d); s.append(n); }
    function ring() { var c = sv("circle", st); c.setAttribute("cx", "10"); c.setAttribute("cy", "10"); c.setAttribute("r", "8"); s.append(c); }
    if (kind === "warn") { p("M10 2.5 1.5 17.5h17L10 2.5Z"); p("M10 8v4"); p("M10 14.6v.2"); }
    else if (kind === "calm") { ring(); p("m6.2 10.2 2.6 2.6 5-5.4"); }
    else { ring(); p("M7.8 7.6a2.3 2.3 0 1 1 3.2 2.1c-.7.3-1 .8-1 1.5v.3"); p("M10 14.5v.2"); }
    return s;
  }

  // ---------- Dates ----------
  function fmtWhen(v) {
    if (!v || v === "—") return "Not stated";
    if (/^\d{4}-\d{2}$/.test(v)) return MONTHS[+v.slice(5, 7) - 1] + " " + v.slice(0, 4);
    if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return new Date(v + "T12:00:00Z").toLocaleDateString("en-IE", { day: "numeric", month: "short", year: "numeric", timeZone: UK });
    var d = new Date(v);
    if (isNaN(d)) return v;
    return d.toLocaleDateString("en-IE", { day: "numeric", month: "short", timeZone: UK }) + ", " + clock(d);
  }
  function clock(d) { return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: UK }); }

  // ---------- Form ----------
  var FIELDS = ["importer", "origin_port", "transshipment_ports", "destination_port", "currency", "fixed_rate_pct", "stock_days", "lead_time_days", "window_start", "window_end"];
  var ORDER = ["importer", "origin_port", "transshipment_ports", "destination_port", "currency", "fixed_rate_share", "fixed_rate_pct", "stock_days", "lead_time_days", "window_start", "window_end", "_"];
  var LABELS = { importer: "Enter a client or company name", origin_port: "Enter the port your goods leave from",
    destination_port: "Enter the port your goods arrive at", currency: "Choose the invoice currency",
    fixed_rate_share: "Choose none, some or all", window_start: "Enter the earliest travel date", window_end: "Enter the latest travel date" };
  var form = $("inputs");

  function curName(code) {
    var o = form.currency.querySelector('option[value="' + code + '"]');
    if (code === "EUR") return "euro";
    return o ? o.textContent.replace(/\s*\([A-Z]{3}\)$/, "") : code;
  }

  function validate(f) {
    var errs = [];
    ["importer", "origin_port", "destination_port", "currency", "window_start", "window_end"].forEach(function (k) { if (!f[k].value.trim()) errs.push([k, LABELS[k]]); });
    if (!f.querySelector("input[name=fixed_rate_share]:checked")) errs.push(["fixed_rate_share", LABELS.fixed_rate_share]);
    ["stock_days", "lead_time_days"].forEach(function (k) {
      if (!/^\d+$/.test(f[k].value.trim())) errs.push([k, k === "stock_days" ? "Enter how many days your stock will last, as a whole number" : "Enter how many days a new order takes, as a whole number"]);
    });
    return errs.sort(function (a, b) { return ORDER.indexOf(a[0]) - ORDER.indexOf(b[0]); });
  }

  function readForm(f) {
    var share = f.querySelector("input[name=fixed_rate_share]:checked");
    var o = { fixed_rate_share: share ? share.value : "" };
    FIELDS.forEach(function (k) { o[k] = f[k].value.trim(); });
    return o;
  }
  function fillForm(o) {
    FIELDS.forEach(function (k) { form[k].value = o[k] || ""; });
    form.querySelectorAll("input[name=fixed_rate_share]").forEach(function (r) { r.checked = r.value === o.fixed_rate_share; });
    $("pct-field").hidden = o.fixed_rate_share !== "some";
  }

  function showErrors(errs) {
    var list = $("error-list"); list.replaceChildren();
    document.querySelectorAll(".field-error").forEach(function (n) { n.hidden = true; });
    document.querySelectorAll("[aria-invalid]").forEach(function (n) { n.removeAttribute("aria-invalid"); });
    if (!errs.length) { $("errors").hidden = true; document.title = document.title.replace(/^Error: /, ""); return; }
    showShipment(true);
    errs.forEach(function (e) {
      var li = el("li"); var a = el("a", e[1]); a.href = "#" + e[0]; li.append(a); list.append(li);
      var fe = $(e[0] + "-error"); if (fe) { fe.textContent = e[1]; fe.hidden = false; }
      var tgt = $(e[0]); if (tgt && tgt.tagName !== "FIELDSET") tgt.setAttribute("aria-invalid", "true"); if (!tgt) a.href = "#importer";
    });
    document.title = "Error: " + document.title.replace(/^Error: /, "");
    $("errors").hidden = false; $("errors").focus();
  }

  form.querySelectorAll("input[name=fixed_rate_share]").forEach(function (r) {
    r.addEventListener("change", function () { $("pct-field").hidden = !(r.value === "some" && r.checked); });
  });

  // Sensible default dates (the next three weeks), so two questions are already answered.
  (function () {
    var t = new Date(), iso = function (d) { return d.toISOString().slice(0, 10); };
    if (!form.window_start.value) form.window_start.value = iso(t);
    if (!form.window_end.value) form.window_end.value = iso(new Date(t.getTime() + 21 * 864e5));
  })();

  // ---------- Question ----------
  // Keyword match only: it picks which answer leads. It is not a chatbot.
  function intent(q) {
    q = (q || "").toLowerCase();
    var late = /late|delay|eta|arriv|on time|stock|run out|strike|port|happening|news|route/.test(q);
    var cost = /cost|dear|price|rate|euro|dollar|sterling|yuan|yen|franc|expens|pay|invoice|currenc|fx/.test(q);
    if (cost && !late) return ["cost", "stock", "route"];
    if (/happening|news|route|strike|port/.test(q) && !cost) return ["route", "stock", "cost"];
    return ["stock", "route", "cost"];
  }

  // ---------- Mode label ----------
  // Placeholder rows (mode "not_used", or status "unavailable" with no fetch) never set the label.
  function modeLabel(ans) {
    if (ans.example) return "Example data, not live";
    var used = (ans.sources || []).filter(function (x) { return x.mode !== "not_used" && !(x.status === "unavailable" && !x.checked_at); });
    return (ans.mode === "fallback" || used.some(function (x) { return x.mode === "fallback"; })) ? "Live sources unavailable: using saved data" : "Live public data";
  }

  // ---------- Verdicts: the three answers, from the engine's fields ----------
  function exposureOf(ans) {
    var x = (ans.delay && ans.delay.exposure) || {};
    var s = +x.stock_days, l = +x.lead_time_days;
    var buf = x.buffer_days != null ? x.buffer_days : s - l;
    return { buffer: buf, short: x.shortfall != null ? x.shortfall : buf < 0, raw: { stock: s, lead: l },
      arithmetic: x.arithmetic || ("Stock lasts " + s + " days. Lead time is " + l + " days. " + (buf < 0 ? "You're " + (-buf) + " days short." : "You have " + buf + " days spare.")) };
  }
  function srcRow(ans, re) { return (ans.sources || []).filter(function (s) { return re.test(s.name); })[0] || null; }

  function verdicts(ans, inputs) {
    var ex = exposureOf(ans), out = {};
    out.stock = { key: "stock", label: "Your stock", tone: ex.short ? "warn" : "calm",
      verdict: ex.short ? (-ex.buffer) + " days short" : ex.buffer === 0 ? "Just covers it" : ex.buffer + " days spare",
      body: ex.arithmetic, sure: ["From your own numbers.", ""], chip: ["Your details", ans.example ? "example figures" : "typed just now"], row: "you" };

    var d = ans.delay || {}, conf = ans.state === "alert" || ans.state === "covered";
    // Older example files carry no per-finding status: an alert's findings are its confirmed events.
    var finds = (d.findings || []).map(function (f) { return f.status ? f : Object.assign({}, f, { status: conf ? "confirmed" : "reported" }); });
    var confirmed = finds.filter(function (f) { return f.status === "confirmed"; });
    var g = srcRow(ans, /GDELT/i);
    var np = ans.news_ports || { checked: [], unknown: [] };
    var r = { key: "route", label: "Your route", findings: finds.slice(0, 3), row: "gdelt",
      chip: ["News", g ? "to " + fmtWhen(g.source_updated_at || g.reference_period) : "not checked"] };
    if (conf) {
      r.tone = "warn"; r.verdict = confirmed.length > 1 ? confirmed.length + " confirmed events" : "Confirmed event";
      r.body = d.reading; r.sure = ["Confirmed", "by an official carrier or port page that names your route."];
    } else if (finds.length) {
      r.tone = "unk"; r.verdict = finds.length === 1 ? "1 report, not confirmed" : finds.length + " reports, not confirmed";
      r.body = d.reading;
      r.sure = ["News only,", "so we can’t confirm either way."];
    } else {
      r.tone = "unk"; r.verdict = "Nothing reported";
      r.body = d.reading;
      r.sure = ["No report", "doesn’t mean on time: quiet delays may never make the news."];
    }
    var notes = [];
    if (np.unknown && np.unknown.length) notes.push("We didn’t search news for " + np.unknown.join(", ") + ": we don’t know that port name yet.");
    var saved = (np.checked || []).filter(function (p) { return p.mode === "fallback"; }).map(function (p) { return p.port; });
    if (saved.length && !ans.example) notes.push("News for " + saved.join(", ") + " is from a saved copy.");
    r.notes = notes;
    out.route = r;

    var fx = ans.fx || {}, pct = fx.eur_cost_change_pct;
    if (pct == null && fx.finding) { var m = /about ([\d.]+)% (higher|lower)/.exec(fx.finding); if (m) pct = (m[2] === "lower" ? -1 : 1) * +m[1]; }
    var c = { key: "cost", label: "Your cost in euro", body: fx.finding, row: "ecb",
      chip: ["ECB", fx.date_now ? "rate for " + fmtWhen(fx.date_now) : fx.source_updated_at ? "rate for " + fx.source_updated_at : "no rate loaded"],
      sure: ["Official ECB rate,", "not your bank’s rate."] };
    if (fx.status === "not_applicable" || (inputs && inputs.currency === "EUR")) { c.tone = "calm"; c.verdict = "No currency effect"; c.sure = ["Nothing to estimate:", fx.finding || "invoiced in euro."]; c.body = ""; c.chip = ["ECB", "not needed here"]; }
    else if (fx.status === "needs_share") { c.tone = "unk"; c.verdict = "Need your fixed share"; }
    else if (fx.status === "unavailable") { c.tone = "unk"; c.verdict = "Rate unavailable"; c.body = fx.finding + " We’ll have it when the ECB source is reachable."; }
    else if (pct != null) {
      var a = Math.abs(pct);
      if (a < 0.5) { c.tone = "calm"; c.verdict = "About the same"; }
      else if (pct > 0) { c.tone = "warn"; c.verdict = "About " + a.toFixed(1) + "% dearer"; }
      else { c.tone = "calm"; c.verdict = "About " + a.toFixed(1) + "% cheaper"; }
    } else { c.tone = "unk"; c.verdict = "Can’t tell"; }
    c.quote = fx.rate_now ? { cur: fx.currency || (inputs && inputs.currency), rate: fx.rate_now } : null;
    out.cost = c;
    return out;
  }

  // ---------- Source rows ----------
  function rowKey(name) {
    return /GDELT/i.test(name) ? "gdelt" : /ECB/i.test(name) ? "ecb" : /CSO/i.test(name) ? "cso" : /Eurostat|Comext/i.test(name) ? "comext" : /AIS|ship/i.test(name) ? "ais" : /advisor|Carrier/i.test(name) ? "adv" : "other";
  }
  function openSource(key) {
    var panel = $("sources-panel"); panel.open = true;
    document.querySelectorAll("#sources tr").forEach(function (tr) { tr.classList.toggle("hl", tr.getAttribute("data-key") === key); });
    var row = document.querySelector('#sources tr[data-key="' + key + '"]');
    var th = row ? row.querySelector("th") : null;
    if (th) { th.tabIndex = -1; th.focus({ preventScroll: true }); row.scrollIntoView({ block: "center" }); }
    else panel.scrollIntoView({ block: "start" });
  }

  // ---------- Shared bits ----------
  function link(text, href) { var a = el("a", text); a.href = href; a.target = "_blank"; a.rel = "noopener noreferrer"; a.append(el("span", " (opens in a new tab)", "sr")); return a; }
  var calmMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function svgText(x, y, txt, cls, anchor) { var t = sv("text", { x: x, y: y, class: cls, "text-anchor": anchor || "start" }); t.textContent = txt; return t; }
  function fmtDay(iso) { return new Date(iso + "T12:00:00Z").toLocaleDateString("en-IE", { day: "numeric", month: "short", timeZone: "UTC" }); }
  function stockSentence(s, l) { var b = s - l; return b < 0 ? "Your stock runs out " + (-b) + " days before a new order would arrive." : b === 0 ? "Your stock runs out on the day a new order would arrive." : "Your stock covers your lead time by " + b + " days."; }

  // ---------- Route map: ports you can open, a ship that sails the route once ----------
  var sailTimer = null;
  function renderMap(geo, ans) {
    var fig = $("routemap"), box = $("routemap-svg"); box.replaceChildren(); $("port-card").hidden = true;
    var pts = (geo || []).filter(function (p) { return typeof p.lat === "number" && typeof p.lon === "number"; });
    if (pts.length < 2) { fig.hidden = true; return null; }
    var lons = pts.map(function (p) { return p.lon; }), lats = pts.map(function (p) { return p.lat; });
    var x0 = Math.min.apply(0, lons), x1 = Math.max.apply(0, lons), y0 = Math.min.apply(0, lats), y1 = Math.max.apply(0, lats);
    var kx = Math.cos((y0 + y1) / 2 * Math.PI / 180);
    var spanX = Math.max((x1 - x0) * kx, 10), spanY = Math.max(y1 - y0, 10);
    var W = 640, pad = 80, H = Math.round(Math.max(340, Math.min(560, (W - 2 * pad) * spanY / spanX + 2 * pad)));
    var k = Math.min((W - 2 * pad) / spanX, (H - 2 * pad) / spanY);
    var cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    var P = function (p) { return [W / 2 + (p.lon - cx) * kx * k, H / 2 - (p.lat - cy) * k]; };
    var svg = sv("svg", { viewBox: "0 0 " + W + " " + H, role: "group", "aria-labelledby": "routemap-title", class: "rm route-map" });
    var t = sv("title", { id: "routemap-title" }); t.textContent = "Route map: " + pts.map(function (p) { return p.port; }).join(", then ") + ". Each port is a button that shows its details."; svg.append(t);
    var grat = sv("g", { "aria-hidden": "true" });
    for (var gl = -180; gl <= 180; gl += 10) { var gx = W / 2 + (gl - cx) * kx * k; if (gx > 0 && gx < W) grat.append(sv("line", { x1: gx, y1: 0, x2: gx, y2: H, class: "rm-grat" })); }
    for (var gt = -80; gt <= 80; gt += 10) { var gy = H / 2 - (gt - cy) * k; if (gy > 0 && gy < H) grat.append(sv("line", { x1: 0, y1: gy, x2: W, y2: gy, class: "rm-grat" })); }
    svg.append(grat);
    var d = "";
    pts.forEach(function (p, i) {
      var c = P(p); if (!i) { d = "M" + c[0].toFixed(1) + " " + c[1].toFixed(1); return; }
      var pr = P(pts[i - 1]), dx = c[0] - pr[0], dy = c[1] - pr[1];
      d += " Q" + ((pr[0] + c[0]) / 2 - dy * 0.18).toFixed(1) + " " + ((pr[1] + c[1]) / 2 + dx * 0.18).toFixed(1) + " " + c[0].toFixed(1) + " " + c[1].toFixed(1);
    });
    var route = sv("path", { d: d, class: "rm-route", "aria-hidden": "true" });
    svg.append(sv("path", { d: d, class: "rm-route-halo", "aria-hidden": "true" }), route);
    var ship = sv("g", { class: "rm-ship", "aria-hidden": "true" });
    ship.append(sv("circle", { r: 9, class: "rm-ship-wake" }), sv("path", { d: "M-7 3 L7 3 L4 -3 L-4 -3 Z", class: "rm-ship-hull" }));
    var placed = [];
    pts.forEach(function (p, i) {
      var c = P(p), ev = p.event === "confirmed" || p.event === "unconfirmed";
      var role = p.role === "origin" ? "From " : p.role === "destination" ? "To " : "Via ";
      var g = sv("g", { class: "rm-pt", tabindex: "0", role: "button", "aria-label": role + p.port + (p.event ? ", " + (p.event === "confirmed" ? "confirmed event" : "news report") : "") + ". Show details." });
      g.append(sv("circle", { cx: c[0], cy: c[1], r: 22, class: "rm-hit" }));
      g.append(sv("circle", { cx: c[0], cy: c[1], r: ev ? 9 : 7, class: "rm-port" + (p.event === "confirmed" ? " rm-confirmed" : ev ? " rm-unconfirmed" : "") }));
      var near = placed.filter(function (q) { return Math.abs(q[0] - c[0]) < 160 && Math.abs(q[1] - c[1]) < 50; })[0];
      var right = near ? c[0] < near[0] : c[0] > W * 0.6;
      if (near && !right && c[0] > W - 160) right = true;
      g.append(svgText(c[0] + (right ? -16 : 16), c[1] + (near ? 32 : -14), role + p.port + (p.event === "confirmed" ? " (confirmed)" : p.event === "unconfirmed" ? " (reported)" : ""), "rm-label", right ? "end" : "start"));
      function open() { svg.querySelectorAll(".rm-pt").forEach(function (n) { n.classList.toggle("on", n === g); }); showPort(p, ans, c, W, H); }
      g.addEventListener("click", open);
      g.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
      svg.append(g); placed.push(c);
    });
    svg.append(ship);
    box.append(svg);
    var len = route.getTotalLength ? route.getTotalLength() : 0;
    route.style.setProperty("--len", Math.ceil(len || 2000));
    function sail() {
      cancelAnimationFrame(sailTimer);
      if (!len) return;
      if (calmMotion) { var e0 = route.getPointAtLength(len); ship.setAttribute("transform", "translate(" + e0.x + " " + e0.y + ")"); return; }
      var t0 = null, dur = 3600;
      function step(ts) {
        if (t0 === null) t0 = ts;
        var f = Math.min(1, (ts - t0) / dur), e = f < .5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2;
        var pt = route.getPointAtLength(len * e), pt2 = route.getPointAtLength(Math.min(len, len * e + 1));
        var ang = Math.atan2(pt2.y - pt.y, pt2.x - pt.x) * 180 / Math.PI;
        ship.setAttribute("transform", "translate(" + pt.x.toFixed(1) + " " + pt.y.toFixed(1) + ") rotate(" + ang.toFixed(0) + ")");
        if (f < 1) sailTimer = requestAnimationFrame(step);
      }
      sailTimer = requestAnimationFrame(step);
    }
    $("sail").onclick = sail;
    var missing = (geo || []).filter(function (p) { return pts.indexOf(p) < 0; }).map(function (p) { return p.port; });
    $("routemap-cap").textContent = "A schematic, not for navigation. Port positions are approximate. Open a port for its news and notices." + (missing.length ? " We couldn’t place " + missing.join(", ") + " on the map." : "");
    fig.hidden = false;
    return { sail: sail };
  }

  function showPort(p, ans, c, W, H) {
    var card = $("port-card"); card.replaceChildren();
    var np = ans.news_ports || { checked: [], unknown: [] }, low = p.port.toLowerCase().replace(/\s*\(.*\)$/, "");
    var checked = (np.checked || []).filter(function (x) { return x.port.toLowerCase() === low; })[0];
    var unknown = (np.unknown || []).some(function (x) { return x.toLowerCase() === p.port.toLowerCase(); });
    var notice = ((ans.coverage || {}).ports || []).filter(function (x) { return x.port.toLowerCase() === low; })[0];
    var h = el("h4", p.port); card.append(h);
    var dl = el("dl");
    function row(a, b) { var d = el("div"); d.append(el("dt", a), el("dd", b)); dl.append(d); }
    row("Role", p.role === "origin" ? "Your goods leave from here" : p.role === "destination" ? "Your goods arrive here" : "Your goods change ship here");
    if (p.locode) row("Port code", p.locode);
    row("News", p.event === "confirmed" ? "A confirmed event names this port" : p.event === "unconfirmed" ? "A news report names this port, not confirmed" : unknown ? "Not searched: we don’t know this port name yet" : "No report names this port in your dates");
    if (checked) row("Checked", fmtWhen(checked.checked_at) + (checked.mode === "fallback" ? " (saved copy)" : ""));
    card.append(dl);
    if (notice) { var pn = el("p"); pn.append(link(p.port + "’s own notices", notice.url)); card.append(pn); }
    var close = el("button", "Close", "linkbtn"); close.type = "button";
    close.addEventListener("click", function () { card.hidden = true; document.querySelectorAll(".rm-pt.on").forEach(function (n) { n.classList.remove("on"); n.focus(); }); });
    card.append(close);
    card.style.setProperty("--x", (c[0] / W * 100).toFixed(1) + "%");
    card.style.setProperty("--y", (c[1] / H * 100).toFixed(1) + "%");
    card.classList.toggle("flip", c[0] / W > 0.55); card.classList.toggle("up", c[1] / H > 0.5);
    card.hidden = false;
  }

  // ---------- Stock runway: drag your own numbers ----------
  function runway(ex) {
    var wrap = el("div", null, "viz runway");
    var s0 = ex.stock, l0 = ex.lead, s = s0, l = l0;
    var svgBox = el("div", null, "rw-box");
    var out = el("p", null, "rw-out"); out.setAttribute("aria-live", "polite");
    var plan = el("p", null, "rw-plan");
    function draw() {
      svgBox.replaceChildren();
      var W = 640, H = 176, L = 16, R = 16, max = Math.max(14, Math.ceil(Math.max(s, l) / 7) * 7 + 7);
      var X = function (dd) { return L + (W - L - R) * dd / max; };
      var g = sv("svg", { viewBox: "0 0 " + W + " " + H, class: "rw", role: "img", "aria-label": "Your stock lasts " + s + " days; a new order placed today arrives on day " + l + "." });
      for (var dd = 0; dd <= max; dd += 7) { g.append(sv("line", { x1: X(dd), y1: 24, x2: X(dd), y2: 132, class: "rw-tick" })); g.append(svgText(X(dd), 160, dd === 0 ? "Today" : "Day " + dd, "rw-axis", dd === 0 ? "start" : dd === max ? "end" : "middle")); }
      var lo = Math.min(s, l), hi = Math.max(s, l);
      if (hi > lo) g.append(sv("rect", { x: X(lo), y: 18, width: X(hi) - X(lo), height: 120, class: s < l ? "rw-gap short" : "rw-gap spare" }));
      g.append(svgText(L, 16, "Your stock", "rw-name"));
      g.append(sv("rect", { x: X(0), y: 26, width: Math.max(4, X(s) - X(0)), height: 28, rx: 2, class: "rw-stock" }));
      g.append(svgText(L, 86, "A new order placed today", "rw-name"));
      g.append(sv("line", { x1: X(0), y1: 110, x2: X(l), y2: 110, class: "rw-transit" }));
      var boat = sv("path", { d: "M" + (X(l) - 11) + " 104 L" + (X(l) + 11) + " 104 L" + (X(l) + 7) + " 116 L" + (X(l) - 7) + " 116 Z", class: "rw-boat" });
      g.append(boat);
      var mid = (X(lo) + X(hi)) / 2;
      if (hi > lo && X(hi) - X(lo) > 70) g.append(svgText(mid, 76, (s < l ? (l - s) + " days short" : (s - l) + " days spare"), "rw-gaplab", "middle"));
      svgBox.append(g);
      out.textContent = stockSentence(s, l);
      plan.textContent = s < l ? "Order today and you’d be without stock for " + (l - s) + " days, unless a quicker route or an earlier shipment closes the gap." : s === l ? "Order today and the new stock lands as the old runs out: no margin for a delay." : "Order within the next " + (s - l) + " days and the new stock lands before you run out.";
      use.hidden = s === s0 && l === l0;
    }
    function slider(label, val, min, maxv, on) {
      var id = "rw-" + label.replace(/\W+/g, "").toLowerCase();
      var f = el("div", null, "rw-ctl");
      var lab = el("label", label); lab.htmlFor = id;
      var r = el("input"); r.type = "range"; r.id = id; r.min = min; r.max = maxv; r.step = 1; r.value = val;
      var o = el("output", val + " days"); o.htmlFor = id;
      r.addEventListener("input", function () { o.textContent = r.value + " days"; on(+r.value); draw(); });
      f.append(lab, r, o); return f;
    }
    var ctl = el("div", null, "rw-ctls");
    ctl.append(slider("Stock lasts", s, 0, Math.max(120, s0), function (v) { s = v; }), slider("New order takes", l, 1, Math.max(120, l0), function (v) { l = v; }));
    var use = el("button", "Check again with these numbers", "btn ghost"); use.type = "button";
    use.addEventListener("click", function () { form.stock_days.value = s; form.lead_time_days.value = l; if (form.requestSubmit) form.requestSubmit(); else form.dispatchEvent(new Event("submit", { cancelable: true })); });
    var note = el("p", "Try other numbers here. The answer above uses the ones you typed until you check again.", "small");
    wrap.append(svgBox, ctl, out, plan, note, use);
    draw();
    return wrap;
  }

  // ---------- Exchange rate: a chart you can scrub, a share you can slide ----------
  function fxViz(fx) {
    var ser = fx.series || [];
    var wrap = el("div", null, "viz fxviz");
    if (ser.length < 2) return null;
    var r0 = ser[0][1], cur = fx.currency;
    var pts = ser.map(function (x) { return { d: x[0], r: x[1], pct: (r0 / x[1] - 1) * 100 }; });
    var W = 640, H = 230, L = 52, R = 18, T = 18, B = 36;
    var lo = Math.min(0, Math.min.apply(0, pts.map(function (p) { return p.pct; }))), hi = Math.max(0, Math.max.apply(0, pts.map(function (p) { return p.pct; })));
    var padv = Math.max(0.5, (hi - lo) * 0.15); lo -= padv; hi += padv;
    var X = function (i) { return L + (W - L - R) * i / (pts.length - 1); }, Y = function (v) { return T + (H - T - B) * (hi - v) / (hi - lo); };
    var svg = sv("svg", { viewBox: "0 0 " + W + " " + H, class: "fxc", tabindex: "0", role: "img",
      "aria-label": "Euro cost of a " + cur + " invoice since " + fmtDay(pts[0].d) + ", " + pts.length + " ECB working days. Use the left and right arrow keys to read each day." });
    var step = (hi - lo) > 4 ? 1 : 0.5;
    for (var v = Math.ceil(lo / step) * step; v <= hi; v += step) {
      svg.append(sv("line", { x1: L, y1: Y(v), x2: W - R, y2: Y(v), class: Math.abs(v) < 1e-9 ? "fxc-zero" : "fxc-grid" }));
      svg.append(svgText(L - 8, Y(v) + 4, (v > 0 ? "+" : "") + v.toFixed(step < 1 ? 1 : 0) + "%", "fxc-axis", "end"));
    }
    [0, pts.length - 1].forEach(function (i) { svg.append(svgText(X(i), H - 10, fmtDay(pts[i].d), "fxc-axis", i ? "end" : "start")); });
    var d = pts.map(function (p, i) { return (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(p.pct).toFixed(1); }).join(" ");
    var area = d + " L" + X(pts.length - 1).toFixed(1) + " " + Y(0).toFixed(1) + " L" + X(0).toFixed(1) + " " + Y(0).toFixed(1) + " Z";
    svg.append(sv("path", { d: area, class: "fxc-area" }), sv("path", { d: d, class: "fxc-line" }));
    var last = pts[pts.length - 1];
    svg.append(sv("circle", { cx: X(pts.length - 1), cy: Y(last.pct), r: 5, class: "fxc-end" }));
    var cross = sv("g", { class: "fxc-cross", visibility: "hidden" });
    var vl = sv("line", { y1: T, y2: H - B, class: "fxc-vline" }), dot = sv("circle", { r: 5, class: "fxc-dot" });
    cross.append(vl, dot); svg.append(cross);
    var hit = sv("rect", { x: L, y: 0, width: W - L - R, height: H, class: "fxc-hit" }); svg.append(hit);
    var read = el("p", null, "fxc-read"); read.setAttribute("aria-live", "polite");
    var idx = pts.length - 1;
    function say(i) {
      idx = Math.max(0, Math.min(pts.length - 1, i)); var p = pts[idx];
      cross.setAttribute("visibility", "visible"); vl.setAttribute("x1", X(idx)); vl.setAttribute("x2", X(idx)); dot.setAttribute("cx", X(idx)); dot.setAttribute("cy", Y(p.pct));
      read.textContent = fmtDay(p.d) + ": €1 = " + p.r + " " + cur + ". A " + cur + " invoice cost about " + Math.abs(p.pct).toFixed(1) + "% " + (p.pct >= 0 ? "more" : "less") + " in euro than on " + fmtDay(pts[0].d) + ".";
    }
    function fromEvent(e) { var bb = svg.getBoundingClientRect(); var x = (e.clientX - bb.left) / bb.width * W; say(Math.round((x - L) / (W - L - R) * (pts.length - 1))); }
    hit.addEventListener("pointermove", fromEvent); hit.addEventListener("pointerdown", fromEvent);
    svg.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight" || e.key === "Home" || e.key === "End") { e.preventDefault(); say(e.key === "Home" ? 0 : e.key === "End" ? pts.length - 1 : idx + (e.key === "ArrowRight" ? 1 : -1)); }
    });
    svg.addEventListener("focus", function () { say(idx); });
    read.textContent = "Move along the line, or focus it and use the arrow keys, to read any day.";
    var title = el("p", "Euro cost of a " + cur + " invoice, change since " + fmtDay(pts[0].d), "viz-title");
    wrap.append(title, svg, read);

    // What if: the share you've fixed, and the invoice in euro
    var full = (r0 / last.r - 1) * 100;
    var startShare = Math.round((1 - (fx.unfixed_share == null ? 1 : fx.unfixed_share)) * 100);
    var ctl = el("div", null, "fx-ctls");
    var f1 = el("div", null, "rw-ctl");
    var l1 = el("label", "What if you’d fixed"); l1.htmlFor = "fx-share";
    var s1 = el("input"); s1.type = "range"; s1.id = "fx-share"; s1.min = 0; s1.max = 100; s1.step = 5; s1.value = startShare;
    var o1 = el("output", startShare + "%"); o1.htmlFor = "fx-share";
    f1.append(l1, s1, o1);
    var f2 = el("div", null, "rw-ctl amt");
    var l2 = el("label", "Invoice amount (" + cur + ")"); l2.htmlFor = "fx-amt";
    var a2 = el("input"); a2.id = "fx-amt"; a2.inputMode = "decimal"; a2.autocomplete = "off"; a2.placeholder = "12000";
    f2.append(l2, a2);
    ctl.append(f1, f2);
    var res = el("p", null, "fx-out"); res.setAttribute("aria-live", "polite");
    function whatIf() {
      var share = +s1.value / 100; o1.textContent = s1.value + "%";
      var pct = full * (1 - share);
      var txt = share >= 1 ? "With the whole invoice fixed, exchange rates don’t move its euro cost." :
        "With " + s1.value + "% fixed, the whole invoice would cost about " + Math.abs(pct).toFixed(1) + "% " + (pct >= 0 ? "more" : "less") + " in euro than on " + fmtDay(pts[0].d) + " (ECB rate as of " + fmtDay(last.d) + ").";
      var amt = parseFloat((a2.value || "").replace(/[, ]/g, ""));
      if (amt > 0 && share < 1) {
        var unf = amt * (1 - share), then = unf / r0, now = unf / last.r;
        txt += " The part you haven’t fixed: about " + eur(then) + " then, " + eur(now) + " now, a difference of " + eur(Math.abs(now - then)) + ".";
      }
      res.textContent = txt + " Not your bank’s rate.";
    }
    s1.addEventListener("input", whatIf); a2.addEventListener("input", whatIf);
    wrap.append(ctl, res);
    whatIf();
    var tbl = el("details", null, "fx-table");
    tbl.append(el("summary", "The rates as a table"));
    var t = el("table"); var th = el("thead"); var hr = el("tr");
    ["ECB date", cur + " per €1", "Euro cost vs " + fmtDay(pts[0].d)].forEach(function (h) { var c = el("th", h); c.scope = "col"; hr.append(c); }); th.append(hr); t.append(th);
    var tb = el("tbody");
    pts.forEach(function (p) { var tr = el("tr"); var c0 = el("th", fmtDay(p.d)); c0.scope = "row"; tr.append(c0); var a = el("td", String(p.r)); a.setAttribute("data-label", cur + " per €1"); var b = el("td", (p.pct >= 0 ? "+" : "") + p.pct.toFixed(2) + "%"); b.setAttribute("data-label", "Euro cost"); tr.append(a, b); tb.append(tr); });
    t.append(tb); tbl.append(t); wrap.append(tbl);
    return wrap;
  }
  var eurFmt = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
  function eur(v) { return eurFmt.format(v); }

  // ---------- The three answers, each with something to try ----------
  function renderPart(v, ans, inputs) {
    var sec = el("section", null, "part part-" + v.key); sec.id = "part-" + v.key; sec.setAttribute("data-tone", v.tone); sec.setAttribute("aria-labelledby", "t-" + v.key);
    var text = el("div", null, "part-text");
    var h = el("h3", v.label); h.id = "t-" + v.key; text.append(h);
    var tone = el("p", null, "tone"); tone.setAttribute("data-tone", v.tone); tone.append(icon(v.tone), document.createTextNode(v.verdict)); text.append(tone);
    if (v.body) text.append(el("p", v.body, "body"));
    if (v.findings && v.findings.length) {
      var ul = el("ul", null, "findings");
      v.findings.forEach(function (f) {
        var li = el("li"); li.append(el("span", f.status === "confirmed" ? "Confirmed" : "Reported", "badge " + (f.status === "confirmed" ? "conf" : "rep")));
        var title = f.text.replace(/^News reports \(not confirmed\): |^An official notice confirms: /, "");
        var url = (f.urls || [])[0];
        li.append(url ? link(title, url) : document.createTextNode(title));
        li.append(el("span", f.source + ", " + (f.source_updated_at || f.as_of) + (f.note ? ". " + f.note : ""), "meta"));
        ul.append(li);
      });
      text.append(ul);
    }
    (v.notes || []).forEach(function (n) { text.append(el("p", n, "sure")); });
    if (v.ais) text.append(v.ais);
    var sure = el("p", null, "sure"); sure.append(el("strong", "How sure: "), document.createTextNode(v.sure[0] + (v.sure[1] ? " " + v.sure[1] : ""))); text.append(sure);
    var chip = el("button", null, "srcchip"); chip.type = "button";
    chip.append(el("b", v.chip[0]), document.createTextNode(v.chip[1]));
    chip.setAttribute("aria-label", "Where this comes from: " + v.chip[0] + ", " + v.chip[1]);
    chip.addEventListener("click", function () { openSource(v.row); });
    text.append(chip);
    var viz = el("div", null, "part-viz");
    if (v.key === "stock") viz.append(runway(exposureOf(ans).raw));
    if (v.key === "route") { var fig = $("routemap"); viz.append(fig); }
    if (v.key === "cost") {
      var fv = (ans.fx && ans.fx.status === "computed") ? fxViz(ans.fx) : null;
      if (fv) viz.append(fv);
      if (v.quote) viz.append(quoteBox(v.quote));
      if (!viz.childNodes.length) viz.append(el("p", v.tone === "calm" ? "Nothing to chart: exchange rates don’t move a euro invoice." : "The chart appears once we have an ECB rate and the share you’ve fixed.", "viz-empty"));
    }
    sec.append(text, viz);
    return sec;
  }

  // Compare the user's own bank quote with the ECB reference rate. Stays on this page.
  function quoteBox(qt) {
    var wrap = el("div", null, "quote"), id = "bankq";
    var lab = el("label", "Your bank’s rate (" + qt.cur + " per €1)"); lab.htmlFor = id;
    var inp = el("input"); inp.id = id; inp.inputMode = "decimal"; inp.autocomplete = "off";
    var out = el("output"); out.htmlFor = id; out.setAttribute("aria-live", "polite");
    var base = "ECB reference: " + qt.rate + ".";
    out.textContent = base + " Type your bank’s quote to see its margin.";
    inp.addEventListener("input", function () {
      var b = parseFloat(inp.value.replace(",", "."));
      if (!(b > 0)) { out.textContent = base; return; }
      var m = (qt.rate / b - 1) * 100; // fewer units per euro from the bank means each unit costs you more
      out.textContent = base + " At your bank’s " + b + ", the invoice costs about " + Math.abs(m).toFixed(1) + "% " + (m >= 0 ? "more" : "less") + " in euro than at the reference rate.";
    });
    wrap.append(lab, inp, out);
    return wrap;
  }

  // Ship counts near each port (only when the server's AIS flag is on and a feed is configured).
  function aisBlock(ais) {
    if (!ais || !ais.ports || !ais.ports.length) return null;
    var p = el("p", null, "sure");
    p.append(el("strong", "Ships near your ports: "));
    p.append(document.createTextNode(ais.ports.map(function (x) { return x.port + ", " + x.waiting + " waiting and " + x.moving + " moving"; }).join("; ") + ". " + (ais.note || "")));
    return p;
  }

  // ---------- Render ----------
  var lastAnswer = null;

  function render(ans, inputs, q) {
    lastAnswer = ans;
    var label = modeLabel(ans);
    $("mode").textContent = label;
    $("mode-pill").setAttribute("data-tone", ans.example ? "example" : /saved/.test(label) ? "saved" : "live");
    $("answer-q").textContent = "Your question: “" + (q || ans.question) + "”";
    $("answer").textContent = ans.headline;
    $("freshness").textContent = ans.dates_line || ans.freshness || "";
    $("staleness").textContent = ans.staleness || ""; $("staleness").hidden = !(ans.mode === "fallback" && ans.staleness);

    var v = verdicts(ans, inputs);
    v.route.ais = aisBlock(ans.ais);
    var res = $("result"); res.hidden = false; res.removeAttribute("aria-busy");
    document.body.classList.add("answered");
    // The map is the route answer's picture: park it in the result before the parts are rebuilt.
    res.insertBefore($("routemap"), $("tiles"));
    var map = renderMap(ans.route_geo, ans);
    var tiles = $("tiles"); tiles.replaceChildren();
    var glance = $("glance"); glance.replaceChildren();
    intent(q).forEach(function (k) {
      tiles.append(renderPart(v[k], ans, inputs));
      var a = el("a", null, "glance-item"); a.href = "#part-" + k; a.setAttribute("data-tone", v[k].tone);
      a.append(el("span", v[k].label, "g-label"), el("span", null, "g-v"));
      a.lastChild.append(icon(v[k].tone), document.createTextNode(v[k].verdict));
      glance.append(a);
    });
    if (map) map.sail();
    ui.fillAll(); ui.wake(res); ui.roll(res);

    var todo = $("todo"); todo.replaceChildren();
    var acts = [ans.delay && ans.delay.action];
    if (v.cost.tone !== "calm" && ans.fx && ans.fx.action) acts.push(ans.fx.action);
    acts.filter(Boolean).slice(0, 2).forEach(function (a) { todo.append(el("li", a)); });

    var cov = $("coverage"); cov.replaceChildren();
    var c = ans.coverage || {};
    if (c.line) {
      cov.append(c.line + " ");
      (c.ports || []).forEach(function (p, i, all) { if (i) cov.append(i === all.length - 1 ? " and " : ", "); cov.append(link(p.port, p.url)); });
    }

    var tb = $("sources"); tb.replaceChildren();
    var rows = [{ name: "Your details", reference_period: "Today", published_at: "—", retrieved_at: "Typed on this page", use: "Stock, lead time, route and currency. Never saved." }].concat(ans.sources || []);
    rows.forEach(function (s) {
      var tr = el("tr"); tr.setAttribute("data-key", s.name === "Your details" ? "you" : rowKey(s.name));
      var th = el("th", s.name); th.scope = "row"; tr.append(th);
      var heads = ["Data for", "Published", "We fetched it", "How we used it"];
      var fetched = s.retrieved_at === "Typed on this page" ? s.retrieved_at : fmtWhen(s.retrieved_at) + (s.status === "snapshot" || s.mode === "fallback" ? " (saved copy)" : s.status === "stale" ? " (older copy)" : "");
      [fmtWhen(s.reference_period), fmtWhen(s.published_at), fetched, s.use].forEach(function (val, i) { var td = el("td", val); td.setAttribute("data-label", heads[i]); tr.append(td); });
      tb.append(tr);
    });
    $("working-summary").textContent = "Where this comes from (" + rows.length + " sources)";
  }

  // ---------- Shipments (this page only) ----------
  var book = [], current = -1, watchTimer = null;

  function summaryOf(ans, inputs) {
    var v = verdicts(ans, inputs);
    return { stock: [v.stock.tone, v.stock.verdict], route: [v.route.tone, v.route.verdict], cost: [v.cost.tone, v.cost.verdict], mode: modeLabel(ans) };
  }
  function routeOf(o) { return [o.origin_port].concat((o.transshipment_ports || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean), [o.destination_port]).join(" → "); }

  function shipLine(o) {
    var line = $("ship-line"); line.replaceChildren();
    var share = { none: "none fixed", some: (o.fixed_rate_pct ? o.fixed_rate_pct + "% fixed" : "some fixed"), all: "all fixed" }[o.fixed_rate_share] || "";
    [["For", o.importer], ["Route", routeOf(o)], ["Invoice", curName(o.currency) + (o.currency !== "EUR" && share ? ", " + share : "")],
     ["Stock lasts", o.stock_days + " days"], ["New order takes", o.lead_time_days + " days"]].forEach(function (x) {
      var d = el("div"); d.append(el("dt", x[0]), el("dd", x[1])); line.append(d);
    });
    $("ship-summary").hidden = false;
  }

  function showShipment(open) {
    $("shipment").hidden = !open;
    $("edit").setAttribute("aria-expanded", open ? "true" : "false");
    $("edit").textContent = open ? "Hide details" : "Change";
  }

  function diff(a, b) {
    var out = [], names = { stock: "Stock", route: "Route", cost: "Cost in euro" };
    ["route", "cost", "stock"].forEach(function (k) { if (a[k][1] !== b[k][1]) out.push(names[k] + ": was “" + a[k][1] + "”, now “" + b[k][1] + "”."); });
    if (a.mode !== b.mode) out.push("Data: was “" + a.mode + "”, now “" + b.mode + "”.");
    return out;
  }

  function renderBook() {
    var tb = $("book-rows"); tb.replaceChildren();
    $("book").hidden = !book.length;
    $("book-count").textContent = book.length ? "(" + book.length + ")" : "";
    book.forEach(function (s, i) {
      var tr = el("tr"); if (i === current) tr.className = "cur";
      var th = el("th"); th.scope = "row"; th.append(el("span", s.inputs.importer)); var sub = el("span", routeOf(s.inputs), "small"); sub.style.display = "block"; th.append(sub); tr.append(th);
      [["Stock", s.sum.stock], ["Route", s.sum.route], ["Cost in euro", s.sum.cost]].forEach(function (c) {
        var td = el("td"); td.setAttribute("data-label", c[0]);
        var v = el("span", null, "v"); v.setAttribute("data-tone", c[1][0]); v.append(icon(c[1][0]), document.createTextNode(c[1][1])); td.append(v); tr.append(td);
      });
      var tdc = el("td", clock(s.at) + (s.changes && s.changes.length ? ", changed" : "")); tdc.setAttribute("data-label", "Checked"); tr.append(tdc);
      var act = el("td"); act.setAttribute("data-label", "Actions");
      var open = el("button", i === current ? "Showing" : "Open", "linkbtn"); open.type = "button"; open.disabled = i === current;
      open.setAttribute("aria-label", (i === current ? "Showing " : "Open ") + s.inputs.importer);
      open.addEventListener("click", function () { showEntry(i); fillForm(s.inputs); });
      var rm = el("button", "Remove", "linkbtn"); rm.type = "button"; rm.setAttribute("aria-label", "Remove " + s.inputs.importer);
      rm.addEventListener("click", function () { book.splice(i, 1); if (current === i) current = -1; else if (current > i) current--; renderBook(); $("book-h").tabIndex = -1; $("book-h").focus(); });
      act.append(open, document.createTextNode(" "), rm); tr.append(act);
      tb.append(tr);
    });
  }

  function showChanges(s) {
    var box = $("changes"), ul = $("changes-list"); ul.replaceChildren();
    if (!s || !s.changes) { box.hidden = true; return; }
    if (!s.changes.length) ul.append(el("li", "Nothing changed. Checked again at " + clock(s.at) + "."));
    s.changes.forEach(function (c) { ul.append(el("li", c)); });
    $("changes-h").textContent = "What changed since " + clock(s.prevAt);
    box.hidden = false;
  }

  // ---------- Fetch ----------
  function busy(on, msg) {
    form.setAttribute("aria-busy", on ? "true" : "false");
    ["submit", "ask-btn", "recheck"].forEach(function (id) { $(id).disabled = on; });
    var st = $("status"); st.replaceChildren();
    if (on) { var orbs = el("span", null, "orbs"); orbs.setAttribute("aria-hidden", "true"); orbs.append(el("i"), el("i"), el("i")); st.append(orbs); }
    if (msg) st.append(document.createTextNode(msg));
    if (on && !$("result").hidden) $("result").setAttribute("aria-busy", "true");
    if (!on) $("result").removeAttribute("aria-busy");
    ui.beam(document.querySelector(".ask"), on);
    if (!$("result").hidden) ui.beam(document.querySelector(".verdict"), on);
  }

  function run(inputs, q, idx) {
    busy(true, "Checking public sources for " + routeOf(inputs).split(" → ").length + " ports…");
    return fetch("/api/answer", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(inputs) })
      .then(function (r) { return r.json().then(function (j) { if (r.status === 400 && j.errors) throw { fields: j.errors }; if (!r.ok) throw new Error("server"); return j; }); })
      .then(function (ans) {
        busy(false, "");
        var sum = summaryOf(ans, inputs), now = new Date();
        if (idx != null && book[idx]) {
          var e = book[idx];
          e.changes = diff(e.sum, sum); e.prevAt = e.at;
          e.ans = ans; e.sum = sum; e.at = now; e.q = q; e.inputs = inputs;
          return idx;
        }
        book.push({ inputs: inputs, ans: ans, sum: sum, at: now, q: q, changes: null });
        return book.length - 1;
      })
      .catch(function (e) {
        if (e && e.fields) { busy(false, ""); showErrors(Object.keys(e.fields).sort(function (x, y) { return ORDER.indexOf(x) - ORDER.indexOf(y); }).map(function (k) { return [k, e.fields[k]]; })); throw e; }
        busy(false, "We couldn’t reach our data sources. Your answers are still here; try again.");
        throw e;
      });
  }

  function showEntry(idx) {
    current = idx; var s = book[idx];
    shipLine(s.inputs); showShipment(false);
    render(s.ans, s.inputs, s.q); showChanges(s); renderBook();
    $("result").focus();
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var errs = validate(form);
    showErrors(errs); if (errs.length) return;
    var inputs = readForm(form), q = form.q.value.trim();
    // The shipment on screen, unchanged: check it again. Otherwise it's a new one.
    var same = current >= 0 && JSON.stringify(book[current].inputs) === JSON.stringify(inputs);
    run(inputs, q, same ? current : null).then(showEntry).catch(function () {});
  });

  document.querySelectorAll(".chip").forEach(function (b) {
    b.addEventListener("click", function () {
      form.q.value = b.getAttribute("data-q");
      if (lastAnswer && !$("result").hidden) {
        var s = book[current]; if (s) s.q = form.q.value;
        render(lastAnswer, s ? s.inputs : lastInputs, form.q.value); $("result").focus();
      } else { $("status").textContent = "Now describe your shipment below, or see an example."; form.origin_port.focus(); }
    });
  });

  var lastInputs = null;
  document.querySelectorAll("[data-example]").forEach(function (b) {
    b.addEventListener("click", function () {
      busy(true, "Loading the example…");
      fetch("examples/" + b.getAttribute("data-example") + ".json").then(function (r) { return r.json(); }).then(function (ans) {
        busy(false, ""); showErrors([]);
        var x = ans.inputs || {}, parts = (x.route || "").split(" → ");
        var inputs = { importer: x.importer || "Example", origin_port: parts[0] || "", transshipment_ports: parts.slice(1, -1).join(", "), destination_port: parts[parts.length - 1] || "",
          currency: x.currency || "USD", fixed_rate_share: x.hedged ? "all" : "none", fixed_rate_pct: "", stock_days: String(x.stock_days || 21), lead_time_days: String(x.lead_time_days || 35),
          window_start: form.window_start.value, window_end: form.window_end.value };
        lastInputs = inputs; fillForm(inputs); shipLine(inputs); showShipment(false); current = -1; renderBook();
        render(ans, inputs, form.q.value.trim()); showChanges(null); $("result").focus();
      }).catch(function () { busy(false, "We couldn’t load the example."); });
    });
  });

  $("edit").addEventListener("click", function () { var open = $("shipment").hidden; showShipment(open); if (open) form.origin_port.focus(); });

  $("add").addEventListener("click", function () {
    fillForm({ currency: form.currency.value, window_start: form.window_start.value, window_end: form.window_end.value });
    current = -1; $("ship-summary").hidden = true; showShipment(true); $("result").hidden = true; renderBook();
    form.scrollIntoView({ block: "start" }); form.origin_port.focus();
  });

  function recheckAll() {
    var i = 0, cur = current;
    function next() {
      if (i >= book.length) { if (cur >= 0 && book[cur]) showEntry(cur); $("watch-note").textContent = "All checked at " + clock(new Date()) + "."; return Promise.resolve(); }
      var k = i++; return run(book[k].inputs, book[k].q, k).then(next);
    }
    return next();
  }
  $("recheck").addEventListener("click", function () { if (current >= 0) run(book[current].inputs, book[current].q, current).then(showEntry).catch(function () {}); else $("status").textContent = "Examples don’t change. Check a shipment of your own to compare."; });
  $("check-all").addEventListener("click", function () { recheckAll().catch(function () {}); });
  $("watch").addEventListener("change", function () {
    clearInterval(watchTimer); watchTimer = null;
    if (this.checked) {
      watchTimer = setInterval(function () { recheckAll().catch(function () {}); }, 30 * 60 * 1000);
      $("watch-note").textContent = "Next check at " + clock(new Date(Date.now() + 30 * 60 * 1000)) + ". Changes appear above.";
    } else $("watch-note").textContent = "";
  });

  // ---------- Copy a plain-text summary ----------
  $("copy").addEventListener("click", function () {
    if (!lastAnswer) return;
    var s = book[current], inputs = s ? s.inputs : lastInputs, v = verdicts(lastAnswer, inputs), btn = this;
    var lines = [(inputs ? inputs.importer + ": " + routeOf(inputs) : "Shipment"), "", lastAnswer.headline, "",
      "Stock: " + v.stock.verdict + ". " + v.stock.body, "Route: " + v.route.verdict + ". " + v.route.body, "Cost in euro: " + v.cost.verdict + ". " + (v.cost.body || ""), "", "Worth checking:"]
      .concat(Array.prototype.map.call($("todo").children, function (li, i) { return (i + 1) + ". " + li.textContent; }))
      .concat(["", lastAnswer.dates_line || lastAnswer.freshness || "", "Sources: " + (lastAnswer.sources || []).filter(function (x) { return x.mode !== "not_used"; }).map(function (x) { return x.name; }).join(", ") + ". Not your bank's rate. News is a signal, not proof."]);
    (navigator.clipboard ? navigator.clipboard.writeText(lines.join("\n")) : Promise.reject())
      .then(function () { btn.textContent = "Copied"; setTimeout(function () { btn.textContent = "Copy a summary for a client"; }, 2500); },
        function () { btn.textContent = "Couldn’t copy: select the answer and copy it instead"; });
  });

  // ---------- Track it yourself ----------
  // ISO 6346 check digit. Runs on this page only; nothing is sent.
  var LETTER = (function () { var m = {}, v = 10; for (var c = 65; c <= 90; c++) { if (v % 11 === 0) v++; m[String.fromCharCode(c)] = v++; } return m; })();
  function containerCheck(raw) {
    var s = (raw || "").toUpperCase().replace(/[\s-]/g, "");
    if (!/^[A-Z]{3}[UJZ]\d{7}$/.test(s)) return { ok: false, msg: "A container number is 4 letters (the last is U, J or Z) then 7 digits, like MSCU1234566." };
    var sum = 0;
    for (var i = 0; i < 10; i++) sum += (i < 4 ? LETTER[s[i]] : +s[i]) * Math.pow(2, i);
    var cd = sum % 11 % 10;
    return cd === +s[10] ? { ok: true, s: s, owner: s.slice(0, 3) } : { ok: false, msg: "The check digit doesn’t match (we expected " + cd + " at the end). Check for a typo." };
  }
  var LINES = [
    [["MSK", "MRK", "MAE", "MRS", "SUD", "SEA"], "Maersk", "https://www.maersk.com/tracking/"],
    [["MSC", "MED", "MSD", "MSM"], "MSC", "https://www.msc.com/en/track-a-shipment"],
    [["CMA", "CGM", "APH", "APZ", "ANN"], "CMA CGM", "https://www.cma-cgm.com/ebusiness/tracking"],
    [["HLX", "HLB", "HAM", "UAC"], "Hapag-Lloyd", "https://www.hapag-lloyd.com/en/online-business/track/track-by-container-solution.html"],
    [["ONE", "NYK", "MOL", "KKF"], "Ocean Network Express (ONE)", "https://www.one-line.com/"],
    [["EGH", "EMC", "EIS", "EGS"], "Evergreen", "https://www.evergreen-line.com/"],
    [["CSN", "CBH", "CCL", "COS", "OOL"], "COSCO or OOCL", "https://lines.coscoshipping.com/"],
    [["ZIM", "ZCS"], "ZIM", "https://www.zim.com/tools/track-a-shipment"],
    [["YML", "YMM"], "Yang Ming", "https://www.yangming.com/"],
    [["HDM", "HMM"], "HMM", "https://www.hmm21.com/"]
  ];
  $("container-go").addEventListener("click", function () {
    var out = $("container-out"); out.replaceChildren();
    var r = containerCheck($("container_no").value);
    if (!r.ok) { out.append(el("span", "Not valid. ", "bad"), document.createTextNode(r.msg)); return; }
    var line = LINES.filter(function (l) { return l[0].indexOf(r.owner) >= 0; })[0];
    out.append(el("span", r.s + " is a valid container number. ", "ok"));
    if (line) { out.append(document.createTextNode("Owner code " + r.owner + "U belongs to " + line[1] + ". "), link("Open " + line[1] + " tracking", line[2]), document.createTextNode(" and paste the number there.")); }
    else out.append(document.createTextNode("We don’t know owner code " + r.owner + ". Many boxes belong to leasing companies, so ask your forwarder which line carries it."));
  });
  function imoOk(s) { var t = 0; for (var i = 0; i < 6; i++) t += +s[i] * (7 - i); return t % 10 === +s[6]; }
  $("vessel-go").addEventListener("click", function () {
    var out = $("vessel-out"); out.replaceChildren();
    var v = $("vessel").value.trim().replace(/^IMO\s*/i, "");
    if (!v) { out.append(el("span", "Enter a ship name or IMO number.", "bad")); return; }
    var isImo = /^\d{7}$/.test(v);
    if (isImo && !imoOk(v)) { out.append(el("span", "Not a valid IMO number: ", "bad"), document.createTextNode("the last digit doesn’t match the check.")); return; }
    var q = encodeURIComponent(v);
    out.append(document.createTextNode((isImo ? "IMO " + v + " is valid. " : "") + "Public trackers (their data, their terms):"));
    var ul = el("ul");
    [["VesselFinder", "https://www.vesselfinder.com/vessels?name=" + q], ["MarineTraffic", "https://www.marinetraffic.com/en/ais/index/search/all/keyword:" + q], ["MyShipTracking", "https://www.myshiptracking.com/vessels?name=" + q]]
      .forEach(function (t) { var li = el("li"); li.append(link(t[0], t[1])); ul.append(li); });
    out.append(ul);
  });
  ["container_no", "vessel"].forEach(function (id) {
    $(id).addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); $(id === "vessel" ? "vessel-go" : "container-go").click(); } });
  });
  // ---------- Interaction layer ----------
  // Ported by hand from bencho (MIT, Lorenzo Cabra) and libraries.dev (MIT, Jakub Antalik); see docs/third-party.md.
  // React and framer-motion are not used: the same maths runs on plain DOM, and every effect is off under reduced motion.
  var ui = (function () {
    var fine = window.matchMedia && window.matchMedia("(pointer: fine)").matches;
    var calm = calmMotion;
    var clamp = function (v, a, b) { return Math.min(b, Math.max(a, v)); };
    var mix = function (a, b, t) { return a + (b - a) * t; };
    // bencho lab/spring: frames not ms, damping raised to dt. tune 0..100 -> stiffness and decay.
    function springOf(tune) { return { k: 0.08 + tune / 100 * 0.16, d: 0.62 + tune / 100 * 0.2 }; }

    // Fallback fill for the native slider when the wake bars aren't drawn.
    function fill(r) { var lo = +r.min || 0, hi = +r.max || 100; r.style.setProperty("--fill", ((r.value - lo) / (hi - lo) * 100).toFixed(1) + "%"); }
    function fillAll() { document.querySelectorAll("input[type=range]").forEach(fill); }
    document.addEventListener("input", function (e) { if (e.target.type === "range") fill(e.target); });

    // ---- Border beam (libraries.dev): a 1px travelling stroke while a check runs.
    function beam(node, on) { if (!node) return; node.classList.add("beam"); node.classList.toggle("on", !!on); }

    // ---- Wake slider (bencho): bars fill to the value; bars the value sweeps past take energy from the drag speed.
    function wake(root) {
      root.querySelectorAll(".rw-ctl input[type=range]").forEach(function (r) {
        if (r.parentNode.classList.contains("wks")) return;
        var n = 36, box = el("div", null, "wks"), bars = [], energy = new Float32Array(n), raf = 0, lastT = 0, at = 0, lastBar = -1;
        for (var i = 0; i < n; i++) { var b = el("span", null, "wks-bar"); b.setAttribute("aria-hidden", "true"); bars.push(b); box.append(b); }
        r.parentNode.insertBefore(box, r); box.append(r);
        function frac() { var lo = +r.min || 0, hi = +r.max || 100; return (r.value - lo) / (hi - lo); }
        function paint() { var lit = Math.round(at * (n - 1)); bars.forEach(function (b, i) { if (i <= lit) b.setAttribute("data-on", ""); else b.removeAttribute("data-on"); }); }
        function loop() {
          if (raf || calm) return;
          var prev = performance.now();
          function run(now) {
            var dt = Math.min(0.05, (now - prev) / 1000); prev = now;
            var live = false, fall = Math.exp(-dt * 6.5);
            for (var i = 0; i < n; i++) { energy[i] *= fall; if (energy[i] < 0.002) energy[i] = 0; else live = true; bars[i].style.transform = energy[i] ? "scaleY(" + (1 + energy[i] * 1.6).toFixed(3) + ")" : ""; }
            raf = live ? requestAnimationFrame(run) : 0;
          }
          raf = requestAnimationFrame(run);
        }
        at = frac(); paint();
        r.addEventListener("input", function () {
          var now = performance.now(), f = frac(), w = box.getBoundingClientRect().width || 300;
          var speed = lastT ? Math.abs(f - at) * w / Math.max(0.008, (now - lastT) / 1000) : 0; lastT = now;
          var a = Math.round(at * (n - 1)), b = Math.round(f * (n - 1)), push = (1 - Math.exp(-speed / 900));
          for (var i = Math.min(a, b); i <= Math.max(a, b); i++) energy[i] = Math.max(energy[i], push);
          at = f; if (b !== lastBar) { lastBar = b; } paint(); loop();
        });
      });
    }

    // ---- Rolling counter (bencho): each digit is a strip 0-9 behind a window. A column's target is the count of
    // whole tens, hundreds... in the value, so the strips roll forward like an odometer, ones first, then each
    // column to the left a little later. Real value kept for screen readers.
    function roll(root) {
      if (calm) return;
      root.querySelectorAll(".tone, .g-v").forEach(function (n) {
        var t = Array.prototype.filter.call(n.childNodes, function (c) { return c.nodeType === 3 && /\d/.test(c.nodeValue); })[0];
        if (!t) return;
        var m = /(\d+(?:\.\d+)?)/.exec(t.nodeValue); if (!m) return;
        var wrap = el("span"), before = t.nodeValue.slice(0, m.index), after = t.nodeValue.slice(m.index + m[1].length);
        var digits = m[1].replace(".", ""), N = parseInt(digits, 10), odo = el("span", null, "odo"); odo.setAttribute("aria-hidden", "true");
        var cols = [], place = digits.length;
        Array.from(m[1]).forEach(function (ch) {
          if (ch === ".") { odo.append(el("span", ".", "odo-sep")); return; }
          place--;
          var col = el("span", null, "odo-col"), strip = el("span", null, "odo-strip");
          for (var d = 0; d <= 10; d++) strip.append(el("span", String(d % 10)));
          col.append(strip); odo.append(col);
          cols.push({ el: strip, p: place, pos: 0, vel: 0, target: Math.floor(N / Math.pow(10, place)), due: 0 });
        });
        wrap.append(document.createTextNode(before), el("span", m[1], "sr"), odo, document.createTextNode(after));
        n.replaceChild(wrap, t);
        var t0 = performance.now();
        cols.forEach(function (c) { c.due = t0 + 120 + c.p * 45; });
        var sp = springOf(45), prev = 0;
        function tick(ts) {
          var dt = prev ? clamp((ts - prev) / 16.67, 0, 2.5) : 1; prev = ts;
          var busy = false;
          cols.forEach(function (c) {
            if (ts < c.due) { busy = true; return; }
            c.vel += (c.target - c.pos) * sp.k * dt; c.vel *= Math.pow(sp.d, dt); c.pos += c.vel * dt;
            if (Math.abs(c.target - c.pos) < 0.02 && Math.abs(c.vel) < 0.02) { c.pos = c.target; c.vel = 0; } else busy = true;
            var md = ((c.pos % 10) + 10) % 10, smear = Math.min(3, Math.abs(c.vel) * 2.4);
            c.el.style.transform = "translateY(" + (-md * 1.1).toFixed(3) + "em)";
            c.el.style.filter = smear > 0.15 ? "blur(" + smear.toFixed(2) + "px)" : "";
          });
          if (busy) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      });
    }

    // ---- Magnetic headline: letters near the pointer lean in and take the brand colour, then spring back.
    function magnetic(h) {
      if (!h || calm || !fine) return;
      var text = h.textContent; h.textContent = "";
      h.append(el("span", text, "sr"));
      var vis = el("span", null, "mag"); vis.setAttribute("aria-hidden", "true");
      var letters = [];
      text.split(" ").forEach(function (w, i, all) {
        var ws = el("span", null, "mag-w");
        Array.from(w).forEach(function (ch) { var l = el("span", ch, "mag-l"); ws.append(l); letters.push(l); });
        vis.append(ws); if (i < all.length - 1) vis.append(document.createTextNode(" "));
      });
      h.append(vis);
      var raf = 0, px = 0, py = 0, on = false;
      function frame() {
        raf = 0;
        letters.forEach(function (l) {
          var b = l.getBoundingClientRect(), dx = px - (b.left + b.width / 2), dy = py - (b.top + b.height / 2), k = on ? Math.max(0, 1 - Math.hypot(dx, dy) / 140) : 0;
          l.style.transform = k ? "translate(" + (dx * k * .12).toFixed(1) + "px," + (dy * k * .12 - k * 6).toFixed(1) + "px) rotate(" + (dx / 140 * 10 * k).toFixed(1) + "deg)" : "";
          l.style.color = k > .45 ? "var(--brand)" : "";
        });
      }
      h.parentNode.addEventListener("pointermove", function (e) { px = e.clientX; py = e.clientY; on = true; if (!raf) raf = requestAnimationFrame(frame); });
      h.parentNode.addEventListener("pointerleave", function () { on = false; if (!raf) raf = requestAnimationFrame(frame); });
    }

    // ---- Tilt (bencho): the card SINKS under the pointer (the point you're over goes away), a dent of shadow
    // pools under it and the opposite rim catches light; the shadow tightens. One spring pair holds the state.
    function tilt(card) {
      if (!card || calm || !fine) return;
      var sheen = el("span", null, "tlt-sheen"); sheen.setAttribute("aria-hidden", "true"); card.append(sheen);
      var tx = 0, ty = 0, tl = 0, s = { x: 0, y: 0, l: 0, vx: 0, vy: 0, vl: 0 }, raf = 0, prev = 0, sp = springOf(50);
      var TILT = 4, SINK = 14, SHADE = 60;
      function tick(ts) {
        var dt = prev ? clamp((ts - prev) / 16.67, 0, 2.5) : 1; prev = ts;
        var moving = false;
        [["x", "vx", tx], ["y", "vy", ty], ["l", "vl", tl]].forEach(function (q) {
          s[q[1]] += (q[2] - s[q[0]]) * sp.k * dt; s[q[1]] *= Math.pow(sp.d, dt); s[q[0]] += s[q[1]] * dt;
          if (Math.abs(q[2] - s[q[0]]) > 0.001 || Math.abs(s[q[1]]) > 0.001) moving = true; else { s[q[0]] = q[2]; s[q[1]] = 0; }
        });
        var rx = -s.y * TILT, ry = s.x * TILT, ppx = (s.x + 1) / 2 * 100, ppy = (s.y + 1) / 2 * 100, dark = SHADE / 100 * 0.55 * s.l, rim = SHADE / 100 * 0.34 * s.l;
        card.style.transform = "translateZ(" + (-SINK * s.l).toFixed(2) + "px) rotateX(" + rx.toFixed(2) + "deg) rotateY(" + ry.toFixed(2) + "deg)";
        card.style.boxShadow = "0 " + mix(20, 9, s.l).toFixed(1) + "px " + mix(44, 24, s.l).toFixed(1) + "px -8px oklch(from var(--tilt-dent) l c h / " + mix(0.22, 0.15, s.l).toFixed(3) + ")";
        sheen.style.backgroundImage = "radial-gradient(42% 34% at " + ppx.toFixed(1) + "% " + ppy.toFixed(1) + "%, oklch(from var(--tilt-dent) l c h / " + dark.toFixed(3) + ") 0%, transparent 100%), radial-gradient(52% 42% at " + (100 - ppx).toFixed(1) + "% " + (100 - ppy).toFixed(1) + "%, oklch(from var(--tilt-rim) l c h / " + rim.toFixed(3) + ") 0%, transparent 100%)";
        raf = moving ? requestAnimationFrame(tick) : 0; if (!moving) prev = 0;
      }
      function go() { if (!raf) raf = requestAnimationFrame(tick); }
      card.addEventListener("pointermove", function (e) { var b = card.parentNode.getBoundingClientRect(); tx = clamp((e.clientX - b.left) / b.width * 2 - 1, -1, 1); ty = clamp((e.clientY - b.top) / b.height * 2 - 1, -1, 1); tl = 1; go(); });
      card.addEventListener("pointerleave", function () { tx = 0; ty = 0; tl = 0; go(); });
    }

    // ---- Magnifying dock falloff (bencho): scale falls off with distance from the pointer, nearest card most.
    function dock(row) {
      if (!row || calm || !fine) return;
      row.addEventListener("pointermove", function (e) {
        row.querySelectorAll(".glance-item").forEach(function (c) { var b = c.getBoundingClientRect(), d = Math.abs(e.clientX - (b.left + b.width / 2)); c.style.setProperty("--lift", Math.max(0, 1 - d / (b.width * 1.4)).toFixed(3)); });
      });
      row.addEventListener("pointerleave", function () { row.querySelectorAll(".glance-item").forEach(function (c) { c.style.setProperty("--lift", "0"); }); });
    }

    magnetic($("page-title")); tilt($("shot")); dock($("glance"));
    return { fillAll: fillAll, roll: roll, wake: wake, beam: beam };
  })();
})();

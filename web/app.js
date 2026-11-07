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
    if (!v || v === "—") return "—";
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
    return { buffer: buf, short: x.shortfall != null ? x.shortfall : buf < 0,
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
      chip: ["News", g ? "to " + fmtWhen(g.source_updated_at || g.reference_period) : "—"] };
    if (conf) {
      r.tone = "warn"; r.verdict = confirmed.length > 1 ? confirmed.length + " confirmed events" : "Confirmed event";
      r.body = d.reading; r.sure = ["Confirmed", "by an official carrier or port page that names your route."];
    } else if (finds.length) {
      r.tone = "unk"; r.verdict = finds.length === 1 ? "1 report, not confirmed" : finds.length + " reports, not confirmed";
      r.body = "We can’t determine whether your shipment is affected. " + d.reading;
      r.sure = ["News only,", "so we can’t confirm either way."];
    } else {
      r.tone = "unk"; r.verdict = "Nothing reported";
      r.body = "We can’t determine whether your shipment is affected. " + d.reading;
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
      chip: ["ECB", "rate for " + (fx.date_now ? fmtWhen(fx.date_now) : fx.source_updated_at || fx.as_of || "—")],
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

  // ---------- Route map ----------
  function renderMap(geo) {
    var fig = $("routemap"), box = $("routemap-svg"); box.replaceChildren();
    var pts = (geo || []).filter(function (p) { return typeof p.lat === "number" && typeof p.lon === "number"; });
    if (pts.length < 2) { fig.hidden = true; return; }
    var lons = pts.map(function (p) { return p.lon; }), lats = pts.map(function (p) { return p.lat; });
    var x0 = Math.min.apply(0, lons), x1 = Math.max.apply(0, lons), y0 = Math.min.apply(0, lats), y1 = Math.max.apply(0, lats);
    var kx = Math.cos((y0 + y1) / 2 * Math.PI / 180);
    var spanX = Math.max((x1 - x0) * kx, 10), spanY = Math.max(y1 - y0, 10);
    var W = 560, pad = 70, H = Math.round(Math.max(300, Math.min(560, (W - 2 * pad) * spanY / spanX + 2 * pad)));
    var k = Math.min((W - 2 * pad) / spanX, (H - 2 * pad) / spanY);
    var cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    var P = function (p) { return [W / 2 + (p.lon - cx) * kx * k, H / 2 - (p.lat - cy) * k]; };
    var svg = sv("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-labelledby": "routemap-title", class: "rm" });
    var t = sv("title", { id: "routemap-title" }); t.textContent = "Route sketch: " + pts.map(function (p) { return p.port; }).join(", then ") + "."; svg.append(t);
    for (var gl = -180; gl <= 180; gl += 10) { var gx = W / 2 + (gl - cx) * kx * k; if (gx > 0 && gx < W) svg.append(sv("line", { x1: gx, y1: 0, x2: gx, y2: H, class: "rm-grat" })); }
    for (var gt = -80; gt <= 80; gt += 10) { var gy = H / 2 - (gt - cy) * k; if (gy > 0 && gy < H) svg.append(sv("line", { x1: 0, y1: gy, x2: W, y2: gy, class: "rm-grat" })); }
    var d = "";
    pts.forEach(function (p, i) {
      var c = P(p); if (!i) { d = "M" + c[0].toFixed(1) + " " + c[1].toFixed(1); return; }
      var pr = P(pts[i - 1]), dx = c[0] - pr[0], dy = c[1] - pr[1];
      d += " Q" + ((pr[0] + c[0]) / 2 - dy * 0.18).toFixed(1) + " " + ((pr[1] + c[1]) / 2 + dx * 0.18).toFixed(1) + " " + c[0].toFixed(1) + " " + c[1].toFixed(1);
    });
    var route = sv("path", { d: d, class: "rm-route" });
    svg.append(sv("path", { d: d, class: "rm-route-halo" }), route);
    var placed = [];
    pts.forEach(function (p) {
      var c = P(p), ev = p.event === "confirmed" || p.event === "unconfirmed";
      svg.append(sv("circle", { cx: c[0], cy: c[1], r: ev ? 8 : 5.5, class: "rm-port" + (p.event === "confirmed" ? " rm-confirmed" : ev ? " rm-unconfirmed" : "") }));
      // Labels sit beside the dot, away from the map edge; a port close to one already
      // labelled gets its label on the far side and below, so names never overlap.
      var near = placed.filter(function (q) { return Math.abs(q[0] - c[0]) < 150 && Math.abs(q[1] - c[1]) < 48; })[0];
      var right = near ? c[0] < near[0] : c[0] > W * 0.6;
      if (near && !right && c[0] > W - 150) right = true;
      var lx = c[0] + (right ? -14 : 14), ly = c[1] + (near ? 40 : -8);
      var role = sv("text", { x: lx, y: ly - 18, class: "rm-role", "text-anchor": right ? "end" : "start" });
      role.textContent = p.role === "origin" ? "From" : p.role === "destination" ? "To" : "Via";
      var lab = sv("text", { x: lx, y: ly, class: "rm-label", "text-anchor": right ? "end" : "start" });
      lab.textContent = p.port + (p.event === "confirmed" ? " · confirmed" : p.event === "unconfirmed" ? " · reported" : "");
      svg.append(role, lab); placed.push(c);
    });
    var note = sv("text", { x: W - 10, y: H - 10, class: "rm-note", "text-anchor": "end" }); note.textContent = "Schematic, not for navigation"; svg.append(note);
    box.append(svg);
    if (route.getTotalLength) route.style.setProperty("--len", Math.ceil(route.getTotalLength()));
    var missing = (geo || []).filter(function (p) { return pts.indexOf(p) < 0; }).map(function (p) { return p.port; });
    $("routemap-cap").textContent = "Port positions are approximate. A dashed ring marks a news report, a filled dot a confirmed event." + (missing.length ? " We couldn’t place " + missing.join(", ") + " on the map." : "");
    fig.hidden = false;
  }

  // ---------- Tiles ----------
  function link(text, href) { var a = el("a", text); a.href = href; a.target = "_blank"; a.rel = "noopener noreferrer"; a.append(el("span", " (opens in a new tab)", "sr")); return a; }

  function renderTile(v) {
    var art = el("article", null, "tile"); art.setAttribute("aria-labelledby", "t-" + v.key);
    var h = el("h3", v.label); h.id = "t-" + v.key; art.append(h);
    var tone = el("p", null, "tone"); tone.setAttribute("data-tone", v.tone); tone.append(icon(v.tone), document.createTextNode(v.verdict)); art.append(tone);
    if (v.body) art.append(el("p", v.body, "body"));
    if (v.findings && v.findings.length) {
      var ul = el("ul", null, "findings");
      v.findings.forEach(function (f) {
        var li = el("li"); li.append(el("span", f.status === "confirmed" ? "Confirmed" : "Reported", "badge " + (f.status === "confirmed" ? "conf" : "rep")));
        var title = f.text.replace(/^News reports \(not confirmed\): |^An official notice confirms: /, "");
        var url = (f.urls || [])[0];
        li.append(url ? link(title, url) : document.createTextNode(title));
        li.append(el("span", f.source + ", " + (f.source_updated_at || f.as_of) + (f.note ? " · " + f.note : ""), "meta"));
        ul.append(li);
      });
      art.append(ul);
    }
    (v.notes || []).forEach(function (n) { art.append(el("p", n, "sure")); });
    if (v.ais) art.append(v.ais);
    var sure = el("p", null, "sure"); sure.append(el("strong", "How sure: "), document.createTextNode(v.sure[0] + (v.sure[1] ? " " + v.sure[1] : ""))); art.append(sure);
    if (v.quote) art.append(quoteBox(v.quote));
    var chip = el("button", null, "srcchip"); chip.type = "button";
    chip.append(el("b", v.chip[0]), document.createTextNode(v.chip[1]));
    chip.setAttribute("aria-label", "Where this comes from: " + v.chip[0] + ", " + v.chip[1]);
    chip.addEventListener("click", function () { openSource(v.row); });
    art.append(chip);
    return art;
  }

  // Compare the user's own bank quote with the ECB reference rate. Stays on this page.
  function quoteBox(qt) {
    var wrap = el("div", null, "quote"), id = "bankq";
    var lab = el("label", "Your bank’s rate (" + qt.cur + " per €1)"); lab.htmlFor = id; lab.style.margin = "0";
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
    var tiles = $("tiles"); tiles.replaceChildren();
    intent(q).forEach(function (k) { tiles.append(renderTile(v[k])); });

    var todo = $("todo"); todo.replaceChildren();
    var acts = [ans.delay && ans.delay.action];
    if (v.cost.tone !== "calm" && ans.fx && ans.fx.action) acts.push(ans.fx.action);
    acts.filter(Boolean).slice(0, 2).forEach(function (a) { todo.append(el("li", a)); });

    var cov = $("coverage"); cov.replaceChildren();
    var c = ans.coverage || {};
    if (c.line) {
      cov.append(c.line + " ");
      (c.ports || []).forEach(function (p, i) { if (i) cov.append(" · "); cov.append(link(p.port, p.url)); });
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

    var res = $("result"); res.hidden = false; res.removeAttribute("aria-busy");
    document.body.classList.add("answered");
    renderMap(ans.route_geo);
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
    var bits = [o.importer, routeOf(o), "Invoiced in " + curName(o.currency) + (o.currency !== "EUR" && share ? ", " + share : ""), "Stock lasts " + o.stock_days + " days", "New order takes " + o.lead_time_days + " days"];
    bits.forEach(function (b, i) { if (i) line.append(el("span", "·", "sep")); line.append(el("span", b)); });
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
    if (on) st.append(el("span", null, "spin"));
    if (msg) st.append(document.createTextNode(msg));
    if (on && !$("result").hidden) $("result").setAttribute("aria-busy", "true");
    if (!on) $("result").removeAttribute("aria-busy");
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
})();

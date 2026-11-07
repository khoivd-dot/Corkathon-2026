// Renders the decision engine's answer. Data is written with textContent only.
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var eur = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
  var usd = new Intl.NumberFormat("en-IE", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

  function el(tag, text, cls) { var n = document.createElement(tag); if (text) n.textContent = text; if (cls) n.className = cls; return n; }

  // Exposure in words, never a bare minus sign.
  function exposureText(stock, lead) {
    var gap = lead - stock;
    var sum = "Your stock lasts " + stock + " days. A new order takes " + lead + " days. ";
    if (gap > 0) return { text: sum + "Your stock runs out " + gap + " days before a new order would arrive.", short: true };
    return { text: sum + "Your stock covers your lead time.", short: false };
  }

  var LABELS = { importer: "Enter who imports the goods", origin_port: "Enter the port your goods leave from",
    destination_port: "Enter the port your goods arrive at", currency: "Choose the invoice currency",
    fixed_rate_share: "Choose none, some or all", window_start: "Enter the earliest travel date", window_end: "Enter the latest travel date" };
  var ORDER = ["importer", "origin_port", "transshipment_ports", "destination_port", "currency", "fixed_rate_share", "fixed_rate_pct", "stock_days", "lead_time_days", "window_start", "window_end", "_"];

  function validate(f) {
    var errs = [];
    ["importer", "origin_port", "destination_port", "currency", "window_start", "window_end"].forEach(function (k) { if (!f[k].value.trim()) errs.push([k, LABELS[k]]); });
    if (!f.querySelector("input[name=fixed_rate_share]:checked")) errs.push(["fixed_rate_share", LABELS.fixed_rate_share]);
    ["stock_days", "lead_time_days"].forEach(function (k) {
      var v = f[k].value;
      if (v === "" || !/^\d+$/.test(v)) errs.push([k, k === "stock_days" ? "Enter how many days your stock will last, as a whole number" : "Enter how many days a new order takes, as a whole number"]);
    });
    return errs;
  }

  function formBody(f) {
    var share = f.querySelector("input[name=fixed_rate_share]:checked");
    var o = { fixed_rate_share: share ? share.value : "" };
    ["importer", "origin_port", "transshipment_ports", "destination_port", "currency", "fixed_rate_pct", "stock_days", "lead_time_days", "window_start", "window_end"].forEach(function (k) { o[k] = f[k].value; });
    return JSON.stringify(o);
  }

  function showErrors(errs) {
    var list = $("error-list"); list.replaceChildren();
    document.querySelectorAll(".field-error").forEach(function (n) { n.hidden = true; });
    document.querySelectorAll("[aria-invalid]").forEach(function (n) { n.removeAttribute("aria-invalid"); });
    if (!errs.length) { $("errors").hidden = true; return; }
    errs.forEach(function (e) {
      var li = el("li"); var a = el("a", e[1]); a.href = "#" + e[0]; li.append(a); list.append(li);
      var fe = $(e[0] + "-error"); if (fe) { fe.textContent = e[1]; fe.hidden = false; } var tgt = $(e[0]); if (tgt && tgt.tagName !== "FIELDSET") tgt.setAttribute("aria-invalid", "true"); if (!tgt) a.href = "#importer";
    });
    document.title = "Error: " + document.title.replace(/^Error: /, "");
    $("errors").hidden = false; $("errors").focus();
  }


  var SVGNS = "http://www.w3.org/2000/svg";
  function sv(tag, attrs) { var n = document.createElementNS(SVGNS, tag); for (var k in attrs) n.setAttribute(k, attrs[k]); return n; }
  function renderMap(geo) {
    var fig = $("routemap"), box = $("routemap-svg"); box.replaceChildren();
    var pts = (geo || []).filter(function (p) { return typeof p.lat === "number" && typeof p.lon === "number"; });
    if (pts.length < 2) { fig.hidden = true; return; }
    var W = Math.max(320, Math.min(800, box.clientWidth || 800)), H = Math.round(Math.max(260, W * 0.45)), pad = 56;
    var lons = pts.map(function (p) { return p.lon; }), lats = pts.map(function (p) { return p.lat; });
    var x0 = Math.min.apply(0, lons), x1 = Math.max.apply(0, lons), y0 = Math.min.apply(0, lats), y1 = Math.max.apply(0, lats);
    var k = Math.min((W - 2 * pad) / Math.max(x1 - x0, 1), (H - 2 * pad) / Math.max(y1 - y0, 1));
    var ox = (W - (x1 - x0) * k) / 2, oy = (H - (y1 - y0) * k) / 2;
    var P = function (p) { return [ox + (p.lon - x0) * k, oy + (y1 - p.lat) * k]; };
    var names = pts.map(function (p) { return p.port; }).join(", then ");
    var svg = sv("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-labelledby": "routemap-title", class: "rm" });
    var t = sv("title", { id: "routemap-title" }); t.textContent = "Your route: " + names + "."; svg.append(t);
    for (var g = -180; g <= 180; g += 10) { var gx = ox + (g - x0) * k; if (gx > 0 && gx < W) svg.append(sv("line", { x1: gx, y1: 0, x2: gx, y2: H, class: "rm-grat" })); }
    for (var g2 = -80; g2 <= 80; g2 += 10) { var gy = oy + (y1 - g2) * k; if (gy > 0 && gy < H) svg.append(sv("line", { x1: 0, y1: gy, x2: W, y2: gy, class: "rm-grat" })); }
    var d = "";
    pts.forEach(function (p, i) { var c = P(p); if (!i) { d = "M" + c[0] + " " + c[1]; return; } var pr = P(pts[i - 1]); var mx = (pr[0] + c[0]) / 2, my = Math.min(pr[1], c[1]) - Math.abs(c[0] - pr[0]) * 0.15; d += " Q" + mx + " " + my + " " + c[0] + " " + c[1]; });
    svg.append(sv("path", { d: d, class: "rm-route-halo" }), sv("path", { d: d, class: "rm-route" }));
    var placed = [];
    pts.forEach(function (p) {
      var c = P(p), ev = p.event === "confirmed" || p.event === "unconfirmed";
      svg.append(sv("circle", { cx: c[0], cy: c[1], r: ev ? 9 : 6, class: "rm-port" + (p.event === "confirmed" ? " rm-confirmed" : ev ? " rm-unconfirmed" : "") }));
      var n = pts.indexOf(p) + 1, right = c[0] > W * 0.6;
      var lab = sv("text", { x: c[0] + (right ? -12 : 12), y: c[1] + (n % 2 ? -12 : 26), class: "rm-label", "text-anchor": right ? "end" : "start" });
      lab.textContent = String(n);
      svg.append(lab);
    });
    box.append(svg);
    var missing = (geo || []).filter(function (p) { return pts.indexOf(p) < 0; }).map(function (p) { return p.port; });
    $("routemap-cap").textContent = pts.map(function (p, i) { return (i + 1) + " " + p.port + (p.event === "confirmed" ? " (confirmed event)" : p.event === "unconfirmed" ? " (unconfirmed report)" : ""); }).join(" \u00b7 ") + ". Port positions are approximate. Route sketch, not for navigation." + (missing.length ? " We couldn\u2019t place " + missing.join(", ") + " on the map." : "");
    fig.hidden = false;
  }
  function render(ans, stock, lead) {
    $("mode").textContent = ans.example ? "Example data, not live" : (ans.mode === "fallback" || (ans.sources || []).some(function (x) { return x.mode === "fallback"; }) ? "Live sources unavailable: using saved data" : "Live public data");
    $("answer-q").textContent = "Your question: \u201c" + ans.question + "\u201d";
    $("freshness").textContent = ans.dates_line || ans.freshness || "";
    $("staleness").textContent = ans.staleness || ""; $("staleness").hidden = !(ans.mode === "fallback" && ans.staleness);
    var exp = exposureText(stock, lead);
    var headline = ans.state === "alert"
      ? (exp.short ? "Check your forwarder\u2019s ETA today: your stock runs out " + (lead - stock) + " days before a new order would arrive." : "Check your forwarder\u2019s ETA today.")
      : "We can\u2019t determine whether your shipment is affected.";
    $("answer").textContent = headline;
    $("delay-h").textContent = ans.delay.heading;
    var ol = $("delay-findings"); ol.replaceChildren();
    ans.delay.findings.forEach(function (f) {
      var li = el("li"); li.append(el("strong", "Finding: "), document.createTextNode(f.text));
      li.append(el("span", f.source + " as of " + (f.source_updated_at || f.as_of) + (f.checked_at ? ", checked " + f.checked_at : "") + (f.note ? " \u00b7 " + f.note : ""), "src")); ol.append(li);
    });
    ol.hidden = !ans.delay.findings.length;
    $("exposure").textContent = exp.text;
    $("delay-reading").textContent = ans.delay.reading;
    var act = $("delay-action");
    act.textContent = ans.state === "alert"
      ? "Ask your forwarder for a current ETA." + (exp.short ? " Consider ordering earlier." : "")
      : (exp.short ? "Your stock shortfall still applies. Ask your forwarder for a current ETA." : "We\u2019ll check again tomorrow.");
    act.className = exp.short ? "action" : "calm";
    var tb = $("sources"); tb.replaceChildren();
    ans.sources.forEach(function (s) {
      var tr = el("tr"); var th = el("th", s.name); th.scope = "row"; tr.append(th);
      var heads = ["Data for", "Published", "Retrieved", "How we used it"];
      [s.reference_period, s.published_at, s.retrieved_at, s.use + (s.status === "snapshot" ? " (snapshot)" : "")].forEach(function (v, i) { var td = el("td", v); td.setAttribute("data-label", heads[i]); tr.append(td); });
      tb.append(tr);
    });
    $("working-summary").textContent = "Show working (" + ans.sources.length + " sources)";
    var fx = ans.fx;
    $("fx-finding").textContent = fx.finding;
    $("fx-src").textContent = fx.source + " as of " + (fx.source_updated_at || fx.as_of) + (fx.checked_at ? ", checked " + fx.checked_at : "");
    $("fx-calc").textContent = (fx.eur_before != null && fx.eur_now != null) ? "Unfixed part: " + eur.format(fx.eur_before) + " then, about " + eur.format(fx.eur_now) + " now (illustrative)." : "";
    $("fx-calc").hidden = !$("fx-calc").textContent;
    var cov = $("coverage");
    if (!cov) { cov = el("p"); cov.id = "coverage"; $("delay-reading").after(cov); }
    cov.replaceChildren();
    if (ans.coverage && ans.coverage.line) {
      cov.append(ans.coverage.line + " ");
      ans.coverage.ports.forEach(function (p, i) {
        var a = el("a", p.port + " notices"); a.href = p.url; a.rel = "noopener"; a.target = "_blank";
        if (i) cov.append(", "); cov.append(a);
      });
    }
    $("fx-reading").textContent = fx.reading;
    $("fx-action").textContent = fx.action;
    renderMap(ans.route_geo); $("result").hidden = false; $("result").focus();
  }

  document.querySelectorAll("input[name=fixed_rate_share]").forEach(function (r) {
    r.addEventListener("change", function () { $("pct-field").hidden = r.value !== "some" || !r.checked; });
  });

  function busy(on, msg) { $("inputs").setAttribute("aria-busy", on ? "true" : "false"); $("submit").disabled = on; $("status").textContent = msg || ""; }

  $("inputs").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var f = ev.target, example = f.scenario.value;
    var errs = example ? [] : validate(f);
    showErrors(errs); if (errs.length) return;
    document.title = document.title.replace(/^Error: /, "");
    var stock = +f.stock_days.value || 21, lead = +f.lead_time_days.value || 35;
    busy(true, "Checking sources\u2026");
    var req = example
      ? fetch("examples/" + example + ".json").then(function (r) { return r.json(); })
      : fetch("/api/answer", { method: "POST", headers: { "Content-Type": "application/json" }, body: formBody(f) })
          .then(function (r) { return r.json().then(function (j) { if (r.status === 400 && j.errors) throw { fields: j.errors }; if (!r.ok) throw new Error("server"); return j; }); });
    req.then(function (ans) { busy(false, ""); render(ans, stock, lead); })
      .catch(function (e) {
        if (e && e.fields) { busy(false, ""); showErrors(Object.keys(e.fields).sort(function (x, y) { return ORDER.indexOf(x) - ORDER.indexOf(y); }).map(function (k) { return [k, e.fields[k]]; })); return; }
        busy(false, "We couldn\u2019t reach our data sources. Your answers are still here; try again.");
      });
  });
})();

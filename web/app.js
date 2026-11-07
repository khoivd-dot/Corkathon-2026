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

  function validate(f) {
    var errs = [];
    if (!f.importer.value.trim()) errs.push(["importer", "Enter who imports the goods"]);
    if (!f.route.value.trim()) errs.push(["route", "Enter the route, including any transshipment port"]);
    ["stock_days", "lead_time_days"].forEach(function (k) {
      var v = f[k].value;
      if (v === "" || !/^\d+$/.test(v)) errs.push([k, k === "stock_days" ? "Enter how many days your stock will last, as a whole number" : "Enter how many days a new order takes, as a whole number"]);
    });
    return errs;
  }

  function showErrors(errs) {
    var list = $("error-list"); list.replaceChildren();
    document.querySelectorAll(".field-error").forEach(function (n) { n.hidden = true; });
    document.querySelectorAll("[aria-invalid]").forEach(function (n) { n.removeAttribute("aria-invalid"); });
    if (!errs.length) { $("errors").hidden = true; return; }
    errs.forEach(function (e) {
      var li = el("li"); var a = el("a", e[1]); a.href = "#" + e[0]; li.append(a); list.append(li);
      var fe = $(e[0] + "-error"); fe.textContent = e[1]; fe.hidden = false; $(e[0]).setAttribute("aria-invalid", "true");
    });
    document.title = "Error: " + document.title.replace(/^Error: /, "");
    $("errors").hidden = false; $("errors").focus();
  }

  function render(ans, stock, lead) {
    $("mode").textContent = ans.example ? "Example data, not live" : "Snapshot data";
    $("answer-q").textContent = "Your question: \u201c" + ans.question + "\u201d";
    $("freshness").textContent = ans.freshness || "";
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
    $("fx-calc").textContent = fx.invoice_usd ? usd.format(fx.invoice_usd) + " invoice: " + eur.format(fx.eur_before) + " then, about " + eur.format(fx.eur_now) + " now (illustrative)." : "";
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
    $("result").hidden = false; $("result").focus();
  }

  $("inputs").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var f = ev.target, errs = validate(f);
    showErrors(errs); if (errs.length) return;
    document.title = document.title.replace(/^Error: /, "");
    var ports = f.route.value.split(/\s*(?:\u2192|->|,)\s*/).map(function (p) { return p.replace(/\s*\(.*\)$/, "").trim(); }).filter(Boolean);
    var end = new Date(), start = new Date(end - 14 * 864e5), iso = function (d) { return d.toISOString().slice(0, 10); };
    var body = { importer: f.importer.value, origin_port: ports[0] || "", destination_port: ports[ports.length - 1] || "",
      transshipment_ports: ports.slice(1, -1).join(","), currency: f.currency.value,
      fixed_rate_share: f.hedged.value === "yes" ? "all" : "none", stock_days: f.stock_days.value,
      lead_time_days: f.lead_time_days.value, window_start: iso(start), window_end: iso(end) };
    // Live answer from F; the example snapshots are only a labelled fallback when the API isn't there.
    fetch("api/answer", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) throw r; return r.json(); })
      .catch(function () { return fetch("examples/" + f.scenario.value + ".json").then(function (r) { return r.json(); }); })
      .then(function (ans) { render(ans, +f.stock_days.value, +f.lead_time_days.value); })
      .catch(function () { $("answer").textContent = "We couldn\u2019t load the answer. Your details are kept; try again."; $("result").hidden = false; });
  });
})();

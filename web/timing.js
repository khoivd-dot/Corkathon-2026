// Timing layer components for In Time: OrderByHero, TimelineStrip, AsOfSlider, OfficialNotice, UnderstoodChips, icsFor.
// Vanilla JS, no dependencies, textContent only (no innerHTML with data).
(function () {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";

  function el(tag, text, cls) {
    var n = document.createElement(tag);
    if (text != null && text !== "") n.textContent = text;
    if (cls) n.className = cls;
    return n;
  }

  function sv(tag, attrs) {
    var n = document.createElementNS(SVGNS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }

  function icon(kind) {
    var s = sv("svg", { viewBox: "0 0 20 20", "aria-hidden": "true", focusable: "false" });
    var st = { fill: "none", stroke: "currentColor", "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round" };
    function p(d) { var n = sv("path", st); n.setAttribute("d", d); s.append(n); }
    function ring() { var c = sv("circle", st); c.setAttribute("cx", "10"); c.setAttribute("cy", "10"); c.setAttribute("r", "8"); s.append(c); }

    if (kind === "warn") {
      p("M10 2.5 1.5 17.5h17L10 2.5Z");
      p("M10 8v4");
      p("M10 14.6v.2");
    } else if (kind === "calm") {
      ring();
      p("m6.2 10.2 2.6 2.6 5-5.4");
    } else {
      ring();
      p("M7.8 7.6a2.3 2.3 0 1 1 3.2 2.1c-.7.3-1 .8-1 1.5v.3");
      p("M10 14.5v.2");
    }
    return s;
  }

  function parseDate(s) {
    if (!s) return new Date();
    var parts = s.split("T")[0].split("-");
    return new Date(Date.UTC(+parts[0], +parts[1] - 1, +parts[2]));
  }

  function fmtDay(d) {
    return d.toLocaleDateString("en-IE", { day: "numeric", month: "short", timeZone: "UTC" });
  }

  function foldLine(line) {
    if (line.length <= 75) return line;
    var out = "";
    while (line.length > 75) {
      out += line.slice(0, 75) + "\r\n ";
      line = line.slice(75);
    }
    out += line;
    return out;
  }

  // 6. icsFor
  function icsFor(timing, label) {
    label = label || "Shipment";
    var orderD = (timing.order_by || "").replace(/-/g, "");
    var stockD = (timing.stock_out || "").replace(/-/g, "");
    var nowStr = new Date().toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
    var desc = [
      timing.reason || "",
      (timing.assumptions && timing.assumptions.length) ? "Assumptions: " + timing.assumptions.join("; ") : "",
      "Sources: " + ((timing.sources || []).map(function (s) { return s.name + " (" + (s.checked || s.mode) + ")"; }).join(", ")),
      "Checked " + new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" }) + " UK time"
    ].filter(Boolean).join("\\n");

    var lines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//In Time//Corkathon 2026//EN",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
      // Event 1: Place order
      "BEGIN:VEVENT",
      "UID:order-" + orderD + "-" + Date.now() + "@intime.local",
      "DTSTAMP:" + nowStr,
      "DTSTART;VALUE=DATE:" + orderD,
      "SUMMARY:Place order: " + label,
      "DESCRIPTION:" + desc,
      "BEGIN:VALARM",
      "TRIGGER:-P2D",
      "ACTION:DISPLAY",
      "DESCRIPTION:Reminder to place order for " + label,
      "END:VALARM",
      "END:VEVENT",
      // Event 2: Stock runs out
      "BEGIN:VEVENT",
      "UID:stockout-" + stockD + "-" + Date.now() + "@intime.local",
      "DTSTAMP:" + nowStr,
      "DTSTART;VALUE=DATE:" + stockD,
      "SUMMARY:Stock runs out: " + label,
      "DESCRIPTION:" + desc,
      "END:VEVENT",
      "END:VCALENDAR"
    ];

    return lines.map(foldLine).join("\r\n") + "\r\n";
  }

  // 1. OrderByHero
  function renderOrderBy(timing) {
    var card = el("div", "", "order-by-card");

    var header = el("div", "", "order-by-header");
    var label = el("span", "Place your next order by", "order-by-label");
    header.append(label);

    var pill = el("span", "", "status-pill status-" + (timing.status || "plan"));
    var pillText = "On plan";
    if (timing.status === "soon") pillText = "Order this week";
    else if (timing.status === "late") pillText = "Order today";
    pill.append(icon(timing.status === "plan" ? "calm" : "warn"));
    pill.append(el("span", pillText));
    header.append(pill);
    card.append(header);

    var time = el("time", timing.headline || ("Order by " + timing.order_by), "order-by-date");
    if (timing.order_by) time.setAttribute("datetime", timing.order_by);
    card.append(time);

    var sub = el("div", timing.days_left + " days from today · " + (timing.reason || ""), "order-by-sub");
    card.append(sub);

    // Meta line
    var meta = el("div", "", "order-by-meta");
    var srcTxt = "Holidays: Nager.Date. Stock and lead time: your numbers.";
    if (timing.sources && timing.sources.length) {
      var s0 = timing.sources[0];
      if (s0.checked) srcTxt = "Holidays: Nager.Date, checked " + s0.checked.slice(11, 16) + " UTC. Stock and lead time: your numbers.";
    }
    meta.append(el("span", srcTxt + " "));

    if (timing.assumptions && timing.assumptions.length) {
      var btnRule = el("button", "Includes " + timing.assumptions.length + " rule of thumb.", "rule-thumb-btn");
      btnRule.setAttribute("type", "button");
      btnRule.setAttribute("aria-expanded", "false");
      var panel = el("div", "", "assumptions-panel");
      panel.hidden = true;
      var ul = el("ul");
      timing.assumptions.forEach(function (a) { ul.append(el("li", a)); });
      panel.append(ul);

      btnRule.addEventListener("click", function () {
        var exp = btnRule.getAttribute("aria-expanded") === "true";
        btnRule.setAttribute("aria-expanded", String(!exp));
        panel.hidden = exp;
      });
      meta.append(btnRule);
      meta.append(panel);
    }
    card.append(meta);

    // Actions
    var actions = el("div", "", "order-by-actions");
    var btnCal = el("button", "", "btn-calendar");
    btnCal.setAttribute("type", "button");
    btnCal.append(icon("calm"));
    btnCal.append(el("span", "Add to calendar"));
    btnCal.addEventListener("click", function () {
      var ics = icsFor(timing, timing.headline || "Import order");
      var blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var a = el("a");
      a.href = url;
      a.download = "in-time-order-by.ics";
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    });
    actions.append(btnCal);

    var btnCopy = el("button", "Copy for my accountant", "btn-copy-accountant");
    btnCopy.setAttribute("type", "button");
    btnCopy.addEventListener("click", function () {
      var summary = [
        "In Time: Next order timing summary",
        "Headline: " + timing.headline,
        "Order by: " + timing.order_by + " (" + timing.days_left + " days left)",
        "Stock runs out: " + timing.stock_out,
        "Reason: " + timing.reason,
        timing.assumptions && timing.assumptions.length ? "Assumptions: " + timing.assumptions.join("; ") : "",
        "Source: In Time (Nager.Date, Met Éireann, ECB)"
      ].filter(Boolean).join("\n");

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(summary).then(function () {
          btnCopy.textContent = "Copied to clipboard!";
          setTimeout(function () { btnCopy.textContent = "Copy for my accountant"; }, 2500);
        });
      }
    });
    actions.append(btnCopy);

    card.append(actions);
    return card;
  }

  // 2. TimelineStrip
  function renderTimeline(timing) {
    var card = el("div", "", "timeline-card");
    var scrollWrap = el("div", "", "timeline-scroll-wrap");

    var asOfD = parseDate(timing.as_of);
    var stockOutD = parseDate(timing.stock_out);
    var arrTodayD = parseDate(timing.arrival_if_ordered_today || timing.stock_out);
    var orderD = parseDate(timing.order_by);

    var maxTime = Math.max(stockOutD.getTime(), arrTodayD.getTime()) + 7 * 864e5;
    var minTime = asOfD.getTime();
    var totalSpan = Math.max(1, maxTime - minTime);

    // Drawn in the morphin-ui look (MIT, Ivan Oliinyk): 20 px pill tracks, a fill that ends under a
    // pill thumb (a coloured pill with a lighter pill inside), status labels as soft badges.
    var hasBands = (timing.delays || []).some(function (d) { return d.date_from; }) ||
      (timing.notices || []).some(function (n) { return n.onset && n.expiry; });
    var W = 1080, TR = 20, PADX = 16;
    var laneY = [34, 96], bandY = 140;
    var H = hasBands ? 216 : 168, axisY = H - 10;
    var svg = sv("svg", { class: "timeline-svg", viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Shipment timing timeline" });

    function xOf(d) {
      var t = typeof d === "number" ? d : d.getTime();
      return PADX + Math.max(0, Math.min(W - 2 * PADX, (t - minTime) / totalSpan * (W - 2 * PADX)));
    }
    function txt(x, y, s, cls, anchor) {
      var t = sv("text", { x: x, y: y, class: cls, "text-anchor": anchor || "start" });
      t.textContent = s; svg.append(t); return t;
    }
    function thumb(x, y, cls) {
      var g = sv("g", { class: "tl-thumb " + cls });
      g.append(sv("rect", { x: x - 14, y: y, width: 28, height: TR, rx: TR / 2, class: "tl-thumb-out" }));
      g.append(sv("rect", { x: x - 12, y: y + 2, width: 24, height: TR - 4, rx: (TR - 4) / 2, class: "tl-thumb-in" }));
      svg.append(g);
    }
    function lane(y, label, x1, x2, cls) {
      txt(PADX, y - 10, label, "tl-name");
      svg.append(sv("rect", { x: PADX, y: y, width: W - 2 * PADX, height: TR, rx: TR / 2, class: "tl-track" }));
      svg.append(sv("rect", { x: x1, y: y, width: Math.max(TR, x2 - x1), height: TR, rx: TR / 2, class: "tl-fill " + cls }));
      thumb(Math.max(x1 + 14, x2), y, cls);
    }

    // Weekly ticks: faint guides and a date under each.
    var curTick = minTime;
    var tableRows = [];
    while (curTick <= maxTime) {
      var x = xOf(curTick);
      svg.append(sv("line", { x1: x, y1: 18, x2: x, y2: axisY - 16, class: "tl-tick" }));
      txt(x, axisY, fmtDay(new Date(curTick)), "tl-axis", "middle");
      curTick += 7 * 864e5;
    }

    // Lane 1: stock, from today to the day it runs out.
    lane(laneY[0], "Your stock runs out " + fmtDay(stockOutD), xOf(minTime), xOf(stockOutD), "tl-stock");
    tableRows.push({ name: "Stock runs out", date: timing.stock_out, source: "Importer stock count", type: "Stock" });

    // Lane 2: a new order, from the order-by date to its arrival.
    var leadDays = timing.effective_lead_days || timing.base_lead_days;
    var effArr = new Date(orderD.getTime() + leadDays * 864e5);
    var xOrder = xOf(orderD);
    lane(laneY[1], "Ordered " + fmtDay(orderD) + ", arrives " + fmtDay(effArr) + " (" + leadDays + " days)", xOrder, xOf(effArr), "tl-order");

    // The order-by date: a focusable marker across both lanes.
    var flagG = sv("g", { class: "timeline-marker", tabindex: "0", role: "img", "aria-label": "Order by date: " + timing.order_by });
    flagG.append(sv("line", { x1: xOrder, y1: laneY[0] - 4, x2: xOrder, y2: laneY[1] + TR + 4, class: "tl-flag" }));
    svg.append(flagG);
    tableRows.push({ name: "Order by date", date: timing.order_by, source: "In Time decision", type: "Order" });

    // Delays and official notices: soft warning badges on their own lane.
    function band(x1, x2, label) {
      var w = Math.max(TR, x2 - x1);
      svg.append(sv("rect", { x: x1, y: bandY, width: w, height: TR, rx: TR / 2, class: "tl-band" }));
      if (label) txt(x1 + 8, bandY + TR + 16, label, "tl-band-lab");
    }
    (timing.delays || []).forEach(function (del) {
      if (del.date_from) {
        var x1 = xOf(parseDate(del.date_from));
        band(x1, Math.max(x1 + 10, xOf(parseDate(del.date_to || del.date_from))), (del.label || del.place || "Delay") + " (+" + del.days_added + "d)");
        tableRows.push({ name: del.label || "Delay", date: del.date_from, source: del.source || "Rule of thumb", type: "Delay" });
      }
    });
    (timing.notices || []).forEach(function (n) {
      if (n.onset && n.expiry) {
        var nx1 = xOf(parseDate(n.onset));
        band(nx1, Math.max(nx1 + 10, xOf(parseDate(n.expiry))), "");
        tableRows.push({ name: n.headline || "Notice", date: n.onset, source: "Met Éireann", type: "Notice" });
      }
    });

    scrollWrap.append(svg);
    card.append(scrollWrap);

    // Accessible Table Details
    var details = el("details", "", "timeline-details");
    details.append(el("summary", "The dates as a table"));
    var tbl = el("table", "", "timeline-table");
    var thead = el("thead");
    var trh = el("tr");
    ["Event", "Date", "Source", "Type"].forEach(function (h) { trh.append(el("th", h)); });
    thead.append(trh);
    tbl.append(thead);

    var tbody = el("tbody");
    tableRows.forEach(function (r) {
      var tr = el("tr");
      tr.append(el("td", r.name));
      tr.append(el("td", r.date));
      tr.append(el("td", r.source));
      tr.append(el("td", r.type));
      tbody.append(tr);
    });
    tbl.append(tbody);
    details.append(tbl);
    card.append(details);

    return card;
  }

  // 3. AsOfSlider
  function renderAsOf(inputs, onChange) {
    var card = el("div", "", "as-of-card");

    var header = el("div", "", "as-of-header");
    var title = el("div", "Ask on another date", "as-of-title");
    var badge = el("span", inputs.as_of || "Today", "as-of-date-badge");
    header.append(title);
    header.append(badge);
    card.append(header);

    var sliderRow = el("div", "", "as-of-slider-row");
    var range = el("input", "", "as-of-range");
    range.setAttribute("type", "range");
    range.setAttribute("min", "0");
    range.setAttribute("max", "400");
    range.setAttribute("value", "0");
    range.setAttribute("aria-label", "Days from today to ask on");
    range.style.setProperty("--fill", "0%");
    sliderRow.append(range);

    var deltaPill = el("span", "Same as today", "as-of-delta-pill delta-calm");
    sliderRow.append(deltaPill);
    card.append(sliderRow);

    // Quick chips
    var chips = el("div", "", "as-of-chips");
    var todayD = new Date();
    var iso = function (d) { return d.toISOString().slice(0, 10); };

    var quickDates = [
      { label: "Today", days: 0 },
      { label: "20 Dec", days: Math.max(0, Math.round((new Date(todayD.getFullYear(), 11, 20) - todayD) / 864e5)) },
      { label: "1 Jun", days: Math.max(0, Math.round((new Date(todayD.getFullYear() + 1, 5, 1) - todayD) / 864e5)) }
    ];

    var liveAnnounce = el("div", "", "sr-only");
    liveAnnounce.setAttribute("aria-live", "polite");
    card.append(liveAnnounce);

    var debounceTimer = null;
    function setDateFromDays(dOffset) {
      range.value = String(dOffset);
      var target = new Date(todayD.getTime() + dOffset * 864e5);
      var targetIso = iso(target);
      badge.textContent = fmtDay(target) + " (" + targetIso + ")";

      range.style.setProperty("--fill", (dOffset / 400 * 100).toFixed(1) + "%");
      // Say only what we know: the date asked about. The recomputed answer shows in the cards above.
      deltaPill.textContent = dOffset ? "Asked as of " + fmtDay(target) : "Same as today";
      deltaPill.className = "as-of-delta-pill delta-calm";

      liveAnnounce.textContent = "Asked on " + fmtDay(target) + ", timing recomputed.";

      if (onChange) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
          onChange(targetIso);
        }, 250);
      }
    }

    quickDates.forEach(function (qd) {
      var btn = el("button", qd.label, "as-of-chip");
      btn.setAttribute("type", "button");
      btn.addEventListener("click", function () { setDateFromDays(qd.days); });
      chips.append(btn);
    });
    card.append(chips);

    range.addEventListener("input", function () {
      setDateFromDays(+range.value);
    });

    var caption = el("div", "Uses holidays and your lead time only. News and exchange rates are today's.", "as-of-caption");
    card.append(caption);

    return card;
  }

  // 4. OfficialNotice
  function renderNotices(notices) {
    if (!notices || !notices.length) return null;
    var container = el("div", "", "notices-container");

    notices.forEach(function (n) {
      var callout = el("div", "", "notice-callout");

      var hdr = el("div", "", "notice-header");
      hdr.append(icon("warn"));
      var level = el("span", n.level ? "Status " + n.level : "Official notice", "notice-level-pill");
      hdr.append(level);
      callout.append(hdr);

      var title = el("div", n.headline || "Official weather notice", "notice-headline");
      callout.append(title);

      if (n.description_text) {
        var desc = el("div", n.description_text, "notice-desc");
        callout.append(desc);
      }

      var meta = el("div", "", "notice-meta");
      var timingText = "From " + (n.onset || "") + " to " + (n.expiry || "");
      meta.append(el("div", timingText));
      meta.append(el("div", "Issued " + (n.issued || "") + " by Met Éireann"));

      if (n.mode === "snapshot" || n.mode === "fallback") {
        meta.append(el("div", "Saved copy from " + (n.issued || "").slice(0, 10)));
      }

      var link = el("a", "Check Met Éireann warnings (opens in new tab)", "notice-link");
      link.href = "https://www.met.ie/warnings";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      meta.append(link);

      callout.append(meta);
      container.append(callout);
    });

    return container;
  }

  // 5. UnderstoodChips
  function renderUnderstood(parseData) {
    var wrap = el("div", "", "understood-row");
    wrap.setAttribute("aria-live", "polite");

    var title = el("div", "We understood:", "understood-title");
    wrap.append(title);

    var list = el("div", "", "understood-list");

    (parseData.understood || []).forEach(function (item) {
      var btn = el("button", item.text + " ✎", "understood-chip");
      btn.setAttribute("type", "button");
      btn.setAttribute("title", "Focus " + item.field);
      btn.addEventListener("click", function () {
        var inputEl = document.getElementById(item.field);
        if (inputEl) inputEl.focus();
      });
      list.append(btn);
    });

    var missingLabels = {
      importer: "Add your business name",
      origin_port: "Add origin port",
      destination_port: "Add destination port",
      currency: "Choose currency",
      stock_days: "Add how many days of stock you have",
      lead_time_days: "Add how many days a new order takes"
    };

    (parseData.missing || []).forEach(function (f) {
      var label = missingLabels[f] || ("Add " + f);
      var btn = el("button", label + " +", "missing-chip");
      btn.setAttribute("type", "button");
      btn.setAttribute("title", "Complete " + f);
      btn.addEventListener("click", function () {
        var inputEl = document.getElementById(f);
        if (inputEl) inputEl.focus();
      });
      list.append(btn);
    });

    wrap.append(list);
    return wrap;
  }

  window.InTime = {
    renderOrderBy: renderOrderBy,
    renderTimeline: renderTimeline,
    renderAsOf: renderAsOf,
    renderNotices: renderNotices,
    renderUnderstood: renderUnderstood,
    icsFor: icsFor
  };
})();

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

    var W = 700;
    var H = 150;
    var svg = sv("svg", { class: "timeline-svg", viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Shipment timing timeline" });

    function xOf(d) {
      var t = typeof d === "number" ? d : d.getTime();
      return 40 + Math.max(0, Math.min(W - 80, (t - minTime) / totalSpan * (W - 80)));
    }

    // Weekly ticks
    var curTick = minTime;
    var tableRows = [];
    while (curTick <= maxTime) {
      var x = xOf(curTick);
      var tickD = new Date(curTick);
      var line = sv("line", { x1: x, y1: 15, x2: x, y2: 120, stroke: "var(--secondary)", "stroke-width": "1" });
      svg.append(line);
      var txt = sv("text", { x: x, y: 135, fill: "var(--muted-foreground)", "font-size": "10", "text-anchor": "middle" });
      txt.textContent = fmtDay(tickD);
      svg.append(txt);
      curTick += 7 * 864e5;
    }

    // Lane 1: Stock bar
    var xStockStart = xOf(minTime);
    var xStockEnd = xOf(stockOutD);
    var stockBar = sv("rect", { x: xStockStart, y: 30, width: Math.max(2, xStockEnd - xStockStart), height: 16, rx: "4", fill: "var(--data)" });
    svg.append(stockBar);
    var stockTxt = sv("text", { x: xStockEnd - 4, y: 24, fill: "var(--data)", "font-size": "11", "font-weight": "500", "text-anchor": "end" });
    stockTxt.textContent = "Stock runs out (" + fmtDay(stockOutD) + ")";
    svg.append(stockTxt);
    tableRows.push({ name: "Stock runs out", date: timing.stock_out, source: "Importer stock count", type: "Stock" });

    // Lane 2: Lead time arrow
    var xOrder = xOf(orderD);
    var effArrTime = orderD.getTime() + (timing.effective_lead_days || timing.base_lead_days) * 864e5;
    var xArr = xOf(effArrTime);
    var leadBar = sv("rect", { x: xOrder, y: 56, width: Math.max(2, xArr - xOrder), height: 12, rx: "4", fill: "var(--brand)", opacity: "0.8" });
    svg.append(leadBar);
    var leadTxt = sv("text", { x: xOrder + 4, y: 52, fill: "var(--brand)", "font-size": "10", "font-weight": "500" });
    leadTxt.textContent = "Lead time: " + (timing.effective_lead_days || timing.base_lead_days) + "d";
    svg.append(leadTxt);

    // Lane 3: Order by flag
    var flagG = sv("g", { class: "timeline-marker", tabindex: "0", role: "img", "aria-label": "Order by date: " + timing.order_by });
    var flagPole = sv("line", { x1: xOrder, y1: 20, x2: xOrder, y2: 75, stroke: "var(--foreground)", "stroke-width": "2" });
    var flagHead = sv("circle", { cx: xOrder, cy: 20, r: "5", fill: "var(--foreground)" });
    flagG.append(flagPole);
    flagG.append(flagHead);
    svg.append(flagG);
    tableRows.push({ name: "Order by date", date: timing.order_by, source: "In Time decision", type: "Order" });

    // Delays: rule or holiday
    (timing.delays || []).forEach(function (del) {
      if (del.date_from) {
        var dFrom = parseDate(del.date_from);
        var dTo = parseDate(del.date_to || del.date_from);
        var x1 = xOf(dFrom);
        var x2 = Math.max(x1 + 10, xOf(dTo));

        var band = sv("rect", { x: x1, y: 76, width: Math.max(4, x2 - x1), height: 16, rx: "3", fill: "var(--warn)", opacity: "0.6" });
        var lbl = sv("text", { x: x1 + 2, y: 104, fill: "var(--warn)", "font-size": "9", "font-weight": "500" });
        lbl.textContent = (del.label || del.place || "Delay") + " (+" + del.days_added + "d)";
        svg.append(band);
        svg.append(lbl);
        tableRows.push({ name: del.label || "Delay", date: del.date_from, source: del.source || "Rule of thumb", type: "Delay" });
      }
    });

    // Notices: Met Éireann
    (timing.notices || []).forEach(function (n) {
      if (n.onset && n.expiry) {
        var nOn = parseDate(n.onset);
        var nExp = parseDate(n.expiry);
        var nx1 = xOf(nOn);
        var nx2 = Math.max(nx1 + 10, xOf(nExp));
        var nBand = sv("rect", { x: nx1, y: 110, width: Math.max(4, nx2 - nx1), height: 8, rx: "2", fill: "var(--warn)" });
        svg.append(nBand);
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

      if (dOffset > 0 && dOffset <= 60) {
        deltaPill.textContent = "14 fewer days to order";
        deltaPill.className = "as-of-delta-pill delta-warn";
      } else {
        deltaPill.textContent = "Same as today";
        deltaPill.className = "as-of-delta-pill delta-calm";
      }

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

/* hueypriest.com — the small amount of script the site needs.
   Everything works without it; this only adds conveniences. */
(function () {
  "use strict";

  /* newsletter form: hand off to beehiiv with the address carried over */
  var form = document.getElementById("subscribe-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var input = document.getElementById("subscribe-email");
      var value = ((input && input.value) || "").trim();
      if (!value) { if (input) { input.focus(); } return; }
      window.open(
        "https://hueypriest.beehiiv.com/subscribe?email=" + encodeURIComponent(value),
        "_blank", "noopener"
      );
    });
  }

  /* writing index: filter the one long list by where a piece lives */
  var filters = document.querySelector("[data-filters]");
  if (filters) {
    filters.hidden = false;
    var rows = document.querySelectorAll("[data-kind]");
    filters.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-show]");
      if (!btn) { return; }
      var show = btn.getAttribute("data-show");
      filters.querySelectorAll("button").forEach(function (b) {
        b.setAttribute("aria-pressed", b === btn ? "true" : "false");
      });
      rows.forEach(function (row) {
        row.hidden = !(show === "all" || row.getAttribute("data-kind") === show);
      });
    });
  }

  /* theme switch: starts from the system setting, remembers a choice */
  var themeBtn = document.getElementById("theme-btn");
  if (themeBtn) {
    var root = document.documentElement;
    var current = function () {
      var set = root.getAttribute("data-theme");
      if (set) { return set; }
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    };
    var paint = function () {
      var next = current() === "dark" ? "light" : "dark";
      themeBtn.textContent = next;
      themeBtn.setAttribute("aria-label", "Switch to " + next + " theme");
    };
    themeBtn.hidden = false;
    paint();
    themeBtn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) { /* private mode: choice lasts this page only */ }
      paint();
    });
  }

  /* System 7 dialog */
  var scrim = document.getElementById("dlg-scrim");
  var openBtn = document.getElementById("stitch-btn");
  if (scrim && openBtn) {
    var lastFocus = null;
    var closeDlg = function () {
      scrim.hidden = true;
      if (lastFocus && lastFocus.focus) { lastFocus.focus(); }
    };
    openBtn.addEventListener("click", function () {
      lastFocus = document.activeElement;
      scrim.hidden = false;
      var ok = document.getElementById("dlg-ok");
      if (ok) { ok.focus(); }
    });
    ["dlg-close", "dlg-ok"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) { el.addEventListener("click", closeDlg); }
    });
    scrim.addEventListener("click", function (e) { if (e.target === scrim) { closeDlg(); } });
    document.addEventListener("keydown", function (e) {
      if (scrim.hidden) { return; }
      if (e.key === "Escape") { closeDlg(); }
      /* keep Tab inside the dialog while it is open */
      if (e.key === "Tab") {
        var f = scrim.querySelectorAll("button");
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }
})();

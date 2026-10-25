/*
 * The app's interactive pieces, as Alpine.js components (https://alpinejs.dev).
 *
 * Templates attach them with x-data="name(...)"; anything smaller is written
 * inline in the template. This file is loaded before alpine.min.js (see
 * base.html), so the registrations below are in place when Alpine starts.
 * Ticking a checklist item is htmx: the server returns the re-rendered card.
 *
 * Tailwind scans this file for class names (app/static/css/src/app.css).
 */

// Reload an events page when the tab comes back after this long hidden: the
// background sync (every few minutes) may have changed the events meanwhile.
const REFRESH_AFTER_MS = 60 * 1000;

document.addEventListener('alpine:init', () => {

  // x-confirm="Question?" on a form or button: ask before submitting or clicking.
  // The message is plain text, not a JavaScript expression.
  Alpine.directive('confirm', (el, { expression }) => {
    const event = el.tagName === 'FORM' ? 'submit' : 'click';
    el.addEventListener(event, (e) => {
      if (!window.confirm(expression)) {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
    });
  });

  // ── Fresh events after returning to the tab ──────────────────────────────
  // config: { prefix } — pages under it (the events pages) are reloaded when
  // the tab becomes visible again after REFRESH_AFTER_MS or more.
  Alpine.data('tabRefresh', (config) => ({
    hiddenSince: null,
    visibility() {
      if (document.visibilityState === 'hidden') {
        this.hiddenSince = Date.now();
        return;
      }
      const away = this.hiddenSince === null ? 0 : Date.now() - this.hiddenSince;
      this.hiddenSince = null;
      if (away > REFRESH_AFTER_MS && window.location.pathname.startsWith(config.prefix)) {
        window.location.reload();
      }
    },
  }));
});

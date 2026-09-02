function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function setWithExpiry(key, value, ttlMs) {
  const record = {
    value,
    expiresAt: Date.now() + ttlMs,
  };
  localStorage.setItem(key, JSON.stringify(record));
}

function getWithExpiry(key) {
  const raw = localStorage.getItem(key);
  if (!raw) return null;

  let record;
  try {
    record = JSON.parse(raw);
  } catch {
    localStorage.removeItem(key); // malformed entry, treat as absent
    return null;
  }

  if (Date.now() > record.expiresAt) {
    localStorage.removeItem(key);
    return null;
  }

  return record.value;
}

/**
 * This script handles displaying a reminder message to participants
 * and persisting which instruction version is currently shown
 * (browser vs. app).
 *
 * The reminder message is shown after 3 minutes if participants are at least on
 * page 3 of the instructions.
 *
 * Navigation between .instruction-page elements is handled by an
 * imported Vue component. This script treats Vue's output as the source of truth:
 * it detects which `.instruction-page` is currently visible (i.e.
 * actually rendered on screen — not `display: none` on itself OR on any
 * ancestor) and reacts via a MutationObserver whenever anything in the
 * document's style/class attributes changes, since visibility can be
 * toggled either on a page element directly or on a container that wraps
 * all of them (e.g. when the participant is navigated away from the
 * instructions section entirely).
 *
 * The page number itself now lives on a child element of each
 * `.instruction-page` (e.g. `<div class="instruction-page">
 * <div data-page="1">...</div></div>`), not on `.instruction-page`
 * itself. This data-page attribute is configured through DDM instructions.
 */
document.addEventListener('DOMContentLoaded', () => {
  const pageEls = Array.from(document.querySelectorAll('.instruction-page'));
  if (!pageEls.length) return;

  function getPageNumber(pageEl) {
    const numbered = pageEl.querySelector('[data-page]');
    return numbered ? Number(numbered.dataset.page) : null;
  }

  const pages = pageEls
    .map((el) => ({ el, num: getPageNumber(el) }))
    .filter((p) => p.num !== null && !Number.isNaN(p.num))
    .sort((a, b) => a.num - b.num);

  if (!pages.length) return;

  const PAGE_STORAGE_KEY = 'instructionCurrentPage';

  // Checks whether an element is actually rendered on screen, not just
  // whether its OWN `display` property is set to something other than
  // 'none'. getComputedStyle(el).display only reflects the element's own
  // declared value — it does NOT become 'none' just because an ancestor
  // is hidden. So an .instruction-page can still read as "visible" here
  // even after the whole instructions section has been hidden/unmounted
  // by a parent, if Vue never touched that page's own inline style.
  // checkVisibility() (where available) correctly walks the ancestor
  // chain; offsetParent is used as a fallback for older browsers.
  function isVisible(el) {
    if (typeof el.checkVisibility === 'function') {
      return el.checkVisibility({ checkOpacity: false, checkVisibilityCSS: true });
    }
    return el.offsetParent !== null || el.getClientRects().length > 0;
  }

  function getActivePageIndex() {
    const idx = pages.findIndex((p) => isVisible(p.el));
    return idx; // -1 means no .instruction-page is currently visible
  }

  let currentPageIndex = getActivePageIndex();

  const defaultVersionSource = document.querySelector('#default-instruction-version');
  let defaultInstructionVersion = 'app';
  if (defaultVersionSource) {
    try {
      defaultInstructionVersion = JSON.parse(defaultVersionSource.textContent);
    } catch {
      defaultInstructionVersion = 'app';
    }
  }

  let currentVersion = localStorage.getItem('instructionVersion') || defaultInstructionVersion;

  // ---------------------------------------------------------------------
  // Timer / reminder modal setup
  // ---------------------------------------------------------------------

  const TIMER_STORAGE_KEY = 'instructionTimerStart';
  const PAGE_THRESHOLD = 3; // timer starts once this page (or later) is reached

  // A stored timer start older than this is considered stale and is
  // discarded; a fresh timer is started instead.
  const TIMER_MAX_AGE_MS = 30 * 60 * 1000; // 30 minutes

  const limitSource = document.querySelector('#seconds-until-reminder');
  const modalTimeLimitSeconds = limitSource
    ? JSON.parse(limitSource.textContent)
    : null;

  let timerIntervalId = null;

  const REMINDER_REGISTERED_KEY = 'instructionReminderRegistered';
  const REMINDER_REGISTERED_TTL_MS = 2 * 24 * 60 * 60 * 1000; // 2 days | test value: 30 * 1000

  const reminderEndpointSource = document.querySelector('#reminder-registration-endpoint');
  let reminderRegistrationEndpoint = null;
  if (reminderEndpointSource) {
    try {
      reminderRegistrationEndpoint = JSON.parse(reminderEndpointSource.textContent);
    } catch {
      reminderRegistrationEndpoint = null;
    }
  }

  function registerGotReminderInfo() {
    if (!reminderRegistrationEndpoint) {
      console.error('Reminder registration endpoint not configured.');
      return;
    }

    fetch(reminderRegistrationEndpoint, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    }).catch((err) => {
      console.error('Failed to register reminder info:', err);
    });
  }

  // Returns the raw stored timer start (ms epoch), or null if absent.
  function getStoredTimerStart() {
    const raw = sessionStorage.getItem(TIMER_STORAGE_KEY);
    if (!raw) return null;
    const start = Number(raw);
    if (Number.isNaN(start)) return null;
    return start;
  }

  // A stored timer is considered stale (cache expired) once it is older
  // than TIMER_MAX_AGE_MS.
  function isStoredTimerStale(start) {
    return Date.now() - start > TIMER_MAX_AGE_MS;
  }

  // Discards a stale stored timer, if any. Returns true if a (still
  // valid) timer remains stored afterwards.
  function pruneStaleTimer() {
    const start = getStoredTimerStart();
    if (start === null) return false;
    if (isStoredTimerStale(start)) {
      sessionStorage.removeItem(TIMER_STORAGE_KEY);
      return false;
    }
    return true;
  }

  function startTimerIfNeeded() {
    if (pruneStaleTimer()) return; // a still-valid timer is already running
    sessionStorage.setItem(TIMER_STORAGE_KEY, String(Date.now()));
  }

  function restartTimer() {
    sessionStorage.setItem(TIMER_STORAGE_KEY, String(Date.now()));
  }

  function getElapsedSeconds() {
    const start = getStoredTimerStart();
    if (start === null) return 0;
    if (isStoredTimerStale(start)) {
      // Cache is older than 30 minutes: ignore it and start fresh.
      sessionStorage.setItem(TIMER_STORAGE_KEY, String(Date.now()));
      return 0;
    }
    return (Date.now() - start) / 1000;
  }

  function showTimerModal() {
    const modalEl = document.getElementById('infoModal');
    if (!modalEl) return;

    if (!getWithExpiry(REMINDER_REGISTERED_KEY)) {
      setWithExpiry(REMINDER_REGISTERED_KEY, true, REMINDER_REGISTERED_TTL_MS);
      registerGotReminderInfo();
    }

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function checkTimer() {
    if (modalTimeLimitSeconds == null || Number.isNaN(modalTimeLimitSeconds)) return;
    if (currentPageIndex === -1) return; // no instruction page visible, nothing to remind about

    const currentPageNum = pages[currentPageIndex].num;
    if (currentPageNum !== 3 && currentPageNum !== 4) return;

    if (getElapsedSeconds() >= modalTimeLimitSeconds) {
      showTimerModal();
      restartTimer(); // "restart" the timer once the modal has been shown
    }
  }

  function ensureTimerRunning() {
    if (timerIntervalId !== null) return;
    checkTimer(); // catch up immediately (e.g. right after a reload)
    timerIntervalId = setInterval(checkTimer, 1000);
  }

  function maybeStartTimerForCurrentPage() {
    if (currentPageIndex === -1) return; // no instruction page visible

    const pageNum = pages[currentPageIndex].num;
    if (pageNum >= PAGE_THRESHOLD) {
      startTimerIfNeeded();
      ensureTimerRunning();
    }
  }

  // If the timer was already started in a previous page load within this
  // session (e.g. user reloaded while on page 4+, or navigated back to an
  // earlier page after having reached page 4), resume ticking immediately —
  // but only if a page is actually visible right now.
  if (currentPageIndex !== -1 && pruneStaleTimer()) {
    ensureTimerRunning();
  }

  // ---------------------------------------------------------------------

  function renderPage() {
    if (currentPageIndex === -1) return; // nothing visible: don't touch version display, page storage, or timer

    renderInstructionVersion();
    maybeStartTimerForCurrentPage();
    sessionStorage.setItem(PAGE_STORAGE_KEY, String(pages[currentPageIndex].num));
  }

  function renderInstructionVersion() {
    if (currentPageIndex === -1) return;

    const currentPage = pages[currentPageIndex].el;

    currentPage.querySelectorAll('.instruction-section').forEach((section) => {
      const target = section.dataset.instructionVersion; // "app" | "browser"
      section.style.display = target === currentVersion ? '' : 'none';
    });

    document.querySelectorAll('.instruction-device-button[data-instruction-version]').forEach((btn) => {
      const isActiveVersion = btn.dataset.instructionVersion === currentVersion;
      btn.style.display = isActiveVersion ? 'none' : '';
    });
  }

  function scrollToTop() {
    void document.body.offsetHeight;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function setInstructionVersion(version) {
    currentVersion = version;
    localStorage.setItem('instructionVersion', version);
    renderInstructionVersion();
  }

  document.addEventListener('click', (e) => {
    const versionBtn = e.target.closest('.instruction-device-button[data-instruction-version]');
    if (versionBtn) {
      e.preventDefault();
      setInstructionVersion(versionBtn.dataset.instructionVersion);
    }
    // Page navigation is entirely owned by the DDM Vue component.
  });

  // React to Vue toggling visibility anywhere that could affect which
  // (if any) .instruction-page is actually rendered. This must watch more
  // than just the page elements themselves: a container that wraps all of
  // them can be hidden/unmounted without touching the page elements'
  // own style/class attributes, which would otherwise leave
  // currentPageIndex stuck pointing at a page that no longer renders.
  // Mutations are batched via requestAnimationFrame so a burst of
  // attribute/childList changes only triggers one recomputation.
  let pendingVisibilityCheck = false;

  function handlePossibleVisibilityChange() {
    if (pendingVisibilityCheck) return;
    pendingVisibilityCheck = true;
    requestAnimationFrame(() => {
      pendingVisibilityCheck = false;
      const newIndex = getActivePageIndex();
      if (newIndex !== currentPageIndex) {
        currentPageIndex = newIndex;
        renderPage();
        scrollToTop();
      }
    });
  }

  const pageObserver = new MutationObserver(handlePossibleVisibilityChange);

  pageObserver.observe(document.body, {
    attributes: true,
    attributeFilter: ['style', 'class'],
    subtree: true,
    childList: true,
  });

  renderPage();
});

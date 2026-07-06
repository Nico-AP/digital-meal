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
 * Navigation between .instruction-page elements (data-page="1", "2", ...)
 * plus toggling between "app" and "browser" instruction sections
 * within the currently visible page.
 *
 * Only one page and one instruction-section (app vs. browser) is
 * shown at a time. The initial instruction version comes from Django
 * (via a json_script tag) and defaults to "app" if not provided.
 * It is not persisted anywhere — a reload always starts from the
 * server-provided (or default) value again.
 */
document.addEventListener('DOMContentLoaded', () => {
  const pages = Array.from(document.querySelectorAll('.instruction-page'))
    .sort((a, b) => Number(a.dataset.page) - Number(b.dataset.page));

  if (!pages.length) return;

  const PAGE_STORAGE_KEY = 'instructionCurrentPage';

  function getInitialPageIndex() {
    const storedPageNum = sessionStorage.getItem(PAGE_STORAGE_KEY);
    if (storedPageNum === null) return 0;

    const idx = pages.findIndex((p) => p.dataset.page === storedPageNum);
    return idx === -1 ? 0 : idx; // fall back to page 1 if the stored value is stale/invalid
  }

  let currentPageIndex = getInitialPageIndex();

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

  function startTimerIfNeeded() {
    if (sessionStorage.getItem(TIMER_STORAGE_KEY)) return; // already running
    sessionStorage.setItem(TIMER_STORAGE_KEY, String(Date.now()));
  }

  function restartTimer() {
    sessionStorage.setItem(TIMER_STORAGE_KEY, String(Date.now()));
  }

  function getElapsedSeconds() {
    const start = Number(sessionStorage.getItem(TIMER_STORAGE_KEY));
    if (!start) return 0;
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

    const currentPageNum = Number(pages[currentPageIndex].dataset.page);
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
    const pageNum = Number(pages[currentPageIndex].dataset.page);
    if (pageNum >= PAGE_THRESHOLD) {
      startTimerIfNeeded();
      ensureTimerRunning();
    }
  }

  // If the timer was already started in a previous page load within this
  // session (e.g. user reloaded while on page 4+, or navigated back to an
  // earlier page after having reached page 4), resume ticking immediately.
  if (sessionStorage.getItem(TIMER_STORAGE_KEY)) {
    ensureTimerRunning();
  }

  // ---------------------------------------------------------------------

  function renderPage() {
    pages.forEach((page, i) => {
      page.style.display = i === currentPageIndex ? '' : 'none';
    });
    renderInstructionVersion();
    updateNavButtons();
    maybeStartTimerForCurrentPage();

    // Persist so a reload resumes here.
    sessionStorage.setItem(PAGE_STORAGE_KEY, pages[currentPageIndex].dataset.page);
  }

  function renderInstructionVersion() {
    const currentPage = pages[currentPageIndex];

    currentPage.querySelectorAll('.instruction-section').forEach((section) => {
      const target = section.dataset.instructionVersion; // "app" | "browser"
      section.style.display = target === currentVersion ? '' : 'none';
    });

    document.querySelectorAll('.instruction-device-button[data-instruction-version]').forEach((btn) => {
      const isActiveVersion = btn.dataset.instructionVersion === currentVersion;
      btn.style.display = isActiveVersion ? 'none' : '';
    });
  }

  function updateNavButtons() {
    document.querySelectorAll('.instruction-back').forEach((btn) => {
      const isFirstPage = currentPageIndex === 0;
      btn.disabled = isFirstPage;
      btn.style.visibility = isFirstPage ? 'hidden' : '';
      btn.style.opacity = isFirstPage ? '0' : '';
    });
    document.querySelectorAll('.instruction-next').forEach((btn) => {
      const isLastPage = currentPageIndex === pages.length - 1;
      btn.disabled = isLastPage;
      btn.style.visibility = isLastPage ? 'hidden' : '';
      btn.style.opacity = isLastPage ? '0' : '';
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
      return;
    }

    if (e.target.closest('.instruction-next')) {
      if (currentPageIndex < pages.length - 1) {
        currentPageIndex++;
        renderPage();
        scrollToTop();
      }
    } else if (e.target.closest('.instruction-back')) {
      if (currentPageIndex > 0) {
        currentPageIndex--;
        renderPage();
        scrollToTop();
      }
    }
  });

  renderPage();
});

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

  let currentPageIndex = 0;
  let currentVersion = getInitialInstructionVersion();

  function getInitialInstructionVersion() {
    const el = document.getElementById('default-instruction-version');
    if (el) {
      try {
        const value = JSON.parse(el.textContent);
        if (value === 'app' || value === 'browser') {
          return value;
        }
      } catch (e) {
        // fall through to default below
      }
    }
    return 'app';
  }

  function renderPage() {
    pages.forEach((page, i) => {
      page.style.display = i === currentPageIndex ? '' : 'none';
    });
    renderInstructionVersion();
    updateNavButtons();
  }

  function renderInstructionVersion() {
    const currentPage = pages[currentPageIndex];

    currentPage.querySelectorAll('.instruction-section').forEach((section) => {
      const target = section.dataset.instructionVersion; // "app" | "browser"
      section.style.display = target === currentVersion ? '' : 'none';
    });

    // Switch buttons/links (e.g. "zur Browser-Anleitung"): only show the
    // one offering the OTHER version — i.e. hide it once you're already
    // viewing that version, since there'd be nothing to switch to.
    // display:none removes it from the tab order/accessibility tree too,
    // so this works for both <button> and <a> elements.
    // Scoped to `document`, not `currentPage`, since these links live
    // outside .instruction-page (in .instruction-wrapper).
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
    // Force the browser to synchronously commit any pending layout
    // changes (e.g. the display:none/'' toggles from renderPage())
    // before scrolling. This makes the scroll deterministic instead of
    // depending on assumptions about frame timing or other page behavior.
    void document.body.offsetHeight;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function setInstructionVersion(version) {
    currentVersion = version;
    renderInstructionVersion();
  }

  document.addEventListener('click', (e) => {
    // Scoped to .instruction-device-button for the same reason as above:
    // without it, clicks anywhere inside an .instruction-section (which
    // also carries data-instruction-version) would incorrectly match here.
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

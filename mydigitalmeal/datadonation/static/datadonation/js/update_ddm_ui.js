function applyDOMChanges() {
  document.querySelectorAll('.section-heading').forEach(el => {
    if (el.textContent.trim() === 'Datei auswählen') {
      el.closest('div.d-flex').style.display = 'none';
    }
  });

  document.querySelectorAll('.fw-bold').forEach(el => {
    if (el.textContent.trim() === 'Hier klicken um eine Datei auszuwählen') {
      el.textContent = 'Warte auf Datei';
    }
  });

  document.querySelectorAll('.uploader-section button').forEach(btn => {
    if (!btn.textContent.trim().includes('alle Daten anzeigen')) {
      btn.style.display = 'none';
    }
  });

  const container = document.querySelector('div.uploader-container');
  if (container) {
    const sections = container.querySelectorAll(':scope > div.uploader-section');
    if (sections.length === 3) {
      sections[0].style.display = 'none';
    }
  }

  const uapp = document.getElementById('uapp');
  if (uapp) {
    uapp.style.visibility = 'visible';
  }

}

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(applyDOMChanges, 0);

  new MutationObserver(applyDOMChanges).observe(document.body, {
    childList: true,
    subtree: true,
  });
});

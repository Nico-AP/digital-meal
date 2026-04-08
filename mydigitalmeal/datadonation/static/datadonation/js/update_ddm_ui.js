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
}

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(applyDOMChanges, 0);

  new MutationObserver(applyDOMChanges).observe(document.body, {
    childList: true,
    subtree: true,
  });
});

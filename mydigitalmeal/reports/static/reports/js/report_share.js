async function copyToClipboard(text) {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text);
  } else {
    // Legacy fallback
    const el = document.createElement('textarea');
    el.value = text;
    el.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
  }
}

async function shareReport(feedbackEl) {
  const url = window.location.origin;

  try {
    if (navigator.share) {
      await navigator.share({
        title: 'Dein Digital Meal TikTok Report',
        text: 'Mach auch mit um deinen TikTok Report zu erhalten',
        url,
      });
    } else {
      await copyToClipboard(url);
      showFeedback(feedbackEl, 'Link kopiert!');
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      await copyToClipboard(url).catch(() => null);
      showFeedback(feedbackEl, 'Link kopiert!');
    }
  }
}

function showFeedback(el, message) {
  if (!el) return;
  const original = el.textContent;
  el.textContent = message;
  el.disabled = true;
  setTimeout(() => {
    el.textContent = original;
    el.disabled = false;
  }, 2000);
}

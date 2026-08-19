// Helper function to fade out an element
function fadeOut(element, duration = 330) {
  element.style.transition = `opacity ${duration}ms`;
  element.style.opacity = '1';

  // Force reflow to ensure transition works
  element.offsetHeight;

  // Start fade out
  element.style.opacity = '0';

  // Hide element after transition completes
  setTimeout(() => {
    element.style.display = 'none';
    element.style.transition = '';
    element.style.opacity = '';
  }, duration);
}

function copyLinkToClipboard() {
  let participationLink = document.getElementById("teilnahmelink").value;
  const disclaimer = document.getElementById('copydisclaimer');

  try {
    navigator.clipboard.writeText(participationLink)
      .then(function () {
        disclaimer.style.display = 'block';
        setTimeout(function () {
          fadeOut(disclaimer);
        }, 330);
      })
      .catch(function () {
        alert("Der Link konnte nicht in die Zwischenablage kopiert werden. Hier ist der Link:\n\n" + participationLink);
      });
  } catch (err) {
    // navigator.clipboard is undefined (insecure context, old browser, etc.)
    alert("Der Link konnte nicht in die Zwischenablage kopiert werden. Hier ist der Link:\n\n" + participationLink);
  }
}

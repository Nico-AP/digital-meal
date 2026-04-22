let debounceTimer;

const observer = new MutationObserver(() => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {

    // Match any agreement-* radio inputs not yet tracked
    const radios = document.querySelectorAll(
      'input[name^="agreement-"]:not([data-listener])'
    );

    radios.forEach(radio => {
      radio.setAttribute('data-listener', 'true');
      radio.addEventListener('change', () => {
        updateFlowButton();
      });
    });

    updateFlowButton();

  }, 100);
});

function updateFlowButton() {
  const flowBtn = document.querySelector('.flow-btn, .custom-flow-btn');
  if (!flowBtn) return;

  const allGroups = getAgreementGroups();

  if (allGroups.size === 0) {
    // No radio groups present — reset to Skip
    flowBtn.classList.remove('btn', 'mdm-color-btn-v2', 'custom-flow-btn');
    flowBtn.classList.add('flow-btn');
    flowBtn.textContent = 'Skip';
    return;
  }

  const allAnswered = [...allGroups].every(name => {
    return document.querySelector(`input[name="${name}"]:checked`) !== null;
  });

  if (allAnswered) {
    flowBtn.classList.remove('flow-btn');
    flowBtn.classList.add('btn', 'mdm-color-btn-v2', 'custom-flow-btn');
    flowBtn.textContent = 'Weiter';
  } else {
    flowBtn.classList.remove('btn', 'mdm-color-btn-v2', 'custom-flow-btn');
    flowBtn.classList.add('flow-btn');
    flowBtn.textContent = 'Skip';
  }
}

function getAgreementGroups() {
  const names = new Set();
  document.querySelectorAll('input[name^="agreement-"]').forEach(radio => {
    names.add(radio.name);
  });
  return names;
}

observer.observe(document.body, { childList: true, subtree: true });

let debounceTimer;

const observer = new MutationObserver(() => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {

    const radios = document.querySelectorAll(
      'input[name="agreement-null"]:not([data-listener])'
    );

    radios.forEach(radio => {
      radio.setAttribute('data-listener', 'true');
      radio.addEventListener('change', () => {
        const flowBtn = document.querySelector('.flow-btn, .custom-flow-btn');
        flowBtn.classList.remove('flow-btn');
        flowBtn.classList.add('btn', 'mdm-color-btn-v2', 'custom-flow-btn');
        flowBtn.textContent = 'Weiter';
      });
    });

    if (document.querySelectorAll('input[name="agreement-null"]').length === 0) {
      const flowBtn = document.querySelector('.flow-btn, .custom-flow-btn');
      if (flowBtn) {
        flowBtn.classList.remove('btn', 'mdm-color-btn-v2', 'custom-flow-btn');
        flowBtn.classList.add('flow-btn');
        flowBtn.textContent = 'Skip';
      }
    }

  }, 100); // waits 100ms after the last DOM change before running
});

observer.observe(document.body, { childList: true, subtree: true });

const setInputType = (type) => {
  document.body.classList.remove('input-touch', 'input-keyboard');
  document.body.classList.add(`input-${type}`);
};

// Detect on first interaction
window.addEventListener('touchstart', () => setInputType('touch'), { once: true });
window.addEventListener('keydown', (e) => {
  if (['ArrowUp', 'ArrowDown'].includes(e.key)) setInputType('keyboard');
}, { once: true });

// Sensible default on load
setInputType('ontouchstart' in window ? 'touch' : 'keyboard');

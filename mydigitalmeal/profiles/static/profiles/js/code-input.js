const input = document.getElementById('id_code');

function syncBoxes() {
  const chars = input.value.toUpperCase().split('');
  const boxes = document.querySelectorAll('.mdm-code-box');

  boxes.forEach((box, i) => {
    const charEl = box.querySelector('.mdm-code-box-char');
    const ch = chars[i];
    charEl.textContent = ch || charEl.textContent || 'A';
    charEl.classList.toggle('filled', Boolean(ch));

    // highlight the box the next typed character will land in
    box.classList.toggle('active', i === chars.length && document.activeElement === input);
  });
}

input.addEventListener('input', syncBoxes);
input.addEventListener('focus', syncBoxes);
input.addEventListener('blur', syncBoxes);

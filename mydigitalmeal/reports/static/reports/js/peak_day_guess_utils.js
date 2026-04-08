document.addEventListener('click', (e) => {
  const btn = e.target.closest('.guess-btn');
  if (!btn) return;

  const guess = parseInt(btn.dataset.guessValue);
  const correct = parseInt(document.getElementById('peak-day-correct-guess').value);
  const isCorrect = guess === correct;

  const correctEl = document.getElementById('peak-day-guess-correct');
  const wrongEl = document.getElementById('peak-day-guess-wrong');
  const target = isCorrect ? correctEl : wrongEl;

  if (target === correctEl) {
    document.getElementById('answer-correct-outro').classList.remove('d-none');
  } else {
    document.getElementById('answer-wrong-outro').classList.remove('d-none');
  }

  const questionContainer = document.getElementById('peak-day-guess-question-container');

  // Step 1: fade out question
  questionContainer.style.transition = 'opacity 0.4s ease-in';
  questionContainer.style.opacity = '0';

  questionContainer.addEventListener('transitionend', () => {
    questionContainer.style.display = 'none';

    // Step 2: fade in answer
    target.style.display = 'block';
    target.style.opacity = '0';
    target.style.transform = 'scale(0.2)';
    target.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';

    target.offsetHeight; // force reflow

    target.style.opacity = '1';
    target.style.transform = 'scale(1)';
  }, { once: true });
});

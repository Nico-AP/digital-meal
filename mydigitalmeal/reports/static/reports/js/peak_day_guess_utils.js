document.addEventListener('click', (e) => {
  const btn = e.target.closest('.guess-btn');
  if (!btn) return;

  const guess = parseInt(btn.dataset.guessValue);
  const correct = parseInt(document.getElementById('peak-day-correct-guess').value);
  const isCorrect = guess === correct;

  const correctEl = document.getElementById('peak-day-guess-correct');
  const wrongEl = document.getElementById('peak-day-guess-wrong');
  const target = isCorrect ? correctEl : wrongEl;

  const questionContainer = document.getElementById('peak-day-guess-question-container');

  // Step 1: fade out question
  questionContainer.style.transition = 'opacity 0.4s ease-in';
  questionContainer.style.opacity = '0';

  questionContainer.addEventListener('transitionend', () => {
    questionContainer.style.display = 'none';

    // Step 2: fade in answer with slight upward drift
    target.style.display = 'block';
    target.style.opacity = '0';
    target.style.transform = 'translateY(12px)';
    target.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';

    target.offsetHeight; // force reflow

    target.style.opacity = '1';
    target.style.transform = 'translateY(0)';
  }, { once: true });
});

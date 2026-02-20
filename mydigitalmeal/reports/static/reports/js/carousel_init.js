const observer = new MutationObserver(() => {
  const carousel = document.querySelector('#reportCarousel');
  if (!carousel) return;

  const items = carousel.querySelectorAll('.carousel-item');
  if (items.length === 0) return;

  // Activate first item
  items[0].classList.add('active');

  // Populate indicators
  const indicators = document.querySelector('#reportCarouselIndicators');
  if (indicators) {
    indicators.innerHTML = ''; // clear existing
    items.forEach((_, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('data-bs-target', '#reportCarousel');
      button.setAttribute('data-bs-slide-to', index);
      button.setAttribute('aria-label', `Report Part ${index + 1}`);
      if (index === 0) {
        button.classList.add('active');
        button.setAttribute('aria-current', 'true');
      }
      indicators.appendChild(button);
    });
  }

  observer.disconnect();
});

observer.observe(document.body, { childList: true, subtree: true });

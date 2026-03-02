const navbar = document.querySelector('.mdm-info-header');
const logoFull = document.querySelector('.header-logo');
const logoIcon = document.querySelector('.header-icon');
const actionBtn = document.querySelector('.mdm-header-btn');

// Cache original heights before any scroll happens
const logoFullHeight = logoFull.scrollHeight;
const actionBtnHeight = actionBtn.scrollHeight;

const scrollStart = 0;   // scroll position where transition begins
const scrollEnd = 150;   // scroll position where transition is complete

window.addEventListener('scroll', () => {
  // progress goes from 0 to 1 as you scroll from scrollStart to scrollEnd
  const progress = Math.min(Math.max(
    (window.scrollY - scrollStart) / (scrollEnd - scrollStart),
  0), 1);

  // Full logo fades out
  logoFull.style.opacity = 1 - progress;
  logoFull.style.height = logoFullHeight * (1 - progress * 0.99) + 'px';
  logoFull.style.transform = `scale(${1 - progress * 0.2})`;
  actionBtn.style.opacity = 1 - progress;
  actionBtn.style.transform = `scale(${1 - progress * 0.2})`;
  actionBtn.style.height = actionBtnHeight * (1 - progress) + 'px';
  actionBtn.style.padding = `${16 * (1 - progress)}px ${40 * (1 - progress)}px`;
  actionBtn.style.fontSize = `${24 - progress * 0}px`;
  actionBtn.style.overflow = 'hidden';

  // Icon fades in
  logoIcon.style.opacity = progress;
  logoIcon.style.transform = `scale(${0.8 + progress * 0.2})`;

  // Navbar height shrinks
  const height = 180 - progress * 100;
  document.querySelector('.mdm-info-header').style.height = `${height}px`;
});

document.body.addEventListener('htmx:beforeSwap', (e) => {
  if (e.detail.target.id !== 'report-statistics') return;

  const icon = document.getElementById('report-load-screen-icon');
  const iconStatic = document.getElementById('report-load-screen-icon-static');
  const iconAnimated = document.getElementById('report-load-screen-icon-animated');

  const animatedBounds = iconAnimated.getBoundingClientRect();

  iconStatic.style.width = `${animatedBounds.width}px`;
  iconStatic.style.height = `${animatedBounds.height}px`;
  iconStatic.style.display = 'flex';
  iconStatic.style.alignItems = 'center';
  iconStatic.style.justifyContent = 'center';

  iconStatic.getBoundingClientRect();

  requestAnimationFrame(() => {
    iconAnimated.style.display = 'none';

    icon.style.transition = `transform 600ms linear 500ms`;
    icon.style.transform = 'translateX(-50%) translateY(-22vh)';

    iconStatic.style.transition = `width 600ms linear 500ms, height 600ms linear 500ms`;
    iconStatic.style.width = `calc(4vh * (200 / 57))`;
    iconStatic.style.height = '4vh';
  });
});

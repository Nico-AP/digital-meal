const navModal = document.getElementById('navModal');
const navToggle = document.querySelector('.nav-mobile-toggle');

const observer = new MutationObserver(() => {
  navToggle.style.opacity = navModal.classList.contains('show') ? '0' : '1';
});

observer.observe(navModal, { attributes: true, attributeFilter: ['class'] });

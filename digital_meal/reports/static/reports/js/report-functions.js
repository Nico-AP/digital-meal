function toggleButton(button, target) {
  // Hide all collapse-dates-plots elements
  document.querySelectorAll('.collapse-dates-plots').forEach(el => {
    el.classList.add('d-none');
  });

  // Show the target element
  document.querySelector(target).classList.remove('d-none');

  // Remove active class from all toggle buttons
  document.querySelectorAll('.toggle-btn').forEach(el => {
    el.classList.remove('toggle-btn-active');
  });

  // Add active class to the clicked button
  button.classList.add('toggle-btn-active');
}

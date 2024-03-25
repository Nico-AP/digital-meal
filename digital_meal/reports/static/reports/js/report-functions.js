function toggleButton(button, target) {
  $('.collapse-dates-plots').addClass('d-none');
  $(target).removeClass('d-none');
  $('.toggle-btn').removeClass('toggle-btn-active');
  $(button).addClass('toggle-btn-active')
}
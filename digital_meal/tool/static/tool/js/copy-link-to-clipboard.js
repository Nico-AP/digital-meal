function copyLinkToClipboard() {
  let participationLink = document.getElementById("teilnahmelink").value;
  navigator.clipboard.writeText(participationLink);
  $('#copydisclaimer').show();
  setTimeout(function () {
    $('#copydisclaimer').fadeOut();
  }, 330);
}
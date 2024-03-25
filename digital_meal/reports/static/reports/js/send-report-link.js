function sendLinkToReport(postUrl, csrfToken) {
  let emailAddress = $('#email-input').val();

  let mailFormat = /\S+@\S+\.\S+/;
  if (emailAddress.match(mailFormat)) {
    $('#email-input-error').hide();
  } else {
    $('#email-input-error').show();
    $('#send-link').modal('toggle');
    return false;
  }

  let reportUrl = window.location.href;
  $.ajax({
    type: 'POST',
    data: {'email': emailAddress, 'link': reportUrl},
    url: postUrl,
    headers: {
      'X-CSRFToken': csrfToken
    },
    success: function (data, status, result) {
      $('#send-mail-success').show();
      $('#send-mail-error').hide();
      $('#send-link-message').modal('toggle');
    },
    error: function (request, status, error) {
      $('#send-mail-success').hide();
      $('#send-mail-error').show();
      $('#send-link-message').modal('toggle');
    },
  });
}
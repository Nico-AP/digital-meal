document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("send-email-button").addEventListener("click", function () {
        let emailInput = document.getElementById("email-input");
        let emailAddress = emailInput.value;

        let mailFormat = /\S+@\S+\.\S+/;
        if (emailAddress.match(mailFormat)) {
            document.getElementById("email-input-error").style.display = "none";
        } else {
            document.getElementById("email-input-error").style.display = "block";
            let sendLinkModal = new bootstrap.Modal(document.getElementById("send-link"));
            sendLinkModal.hide();
            return false;
        }

        // Extract values from data attributes
        let emailDataDiv = document.getElementById("email-data");
        let postUrl = emailDataDiv.getAttribute("data-post-url");
        let csrfToken = emailDataDiv.getAttribute("data-csrf-token");
        sendLinkToReport(postUrl, csrfToken, emailAddress);
    });
});

function sendLinkToReport(postUrl, csrfToken, toAddress) {
    let reportUrl = window.location.href;

    fetch(postUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ email: toAddress, link: reportUrl })
    })
    .then(response => {
        if (response.ok) {
            document.getElementById("send-mail-success").style.display = "block";
            document.getElementById("send-mail-error").style.display = "none";
        } else {
            document.getElementById("send-mail-success").style.display = "none";
            document.getElementById("send-mail-error").style.display = "block";
        }

        let messageModal = new bootstrap.Modal(document.getElementById("send-link-message"));
        messageModal.show();
    })
    .catch(error => {
        console.error("Error:", error);
        document.getElementById("send-mail-success").style.display = "none";
        document.getElementById("send-mail-error").style.display = "block";

        let messageModal = new bootstrap.Modal(document.getElementById("send-link-message"));
        messageModal.show();
    });
}

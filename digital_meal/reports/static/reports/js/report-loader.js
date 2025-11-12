document.body.addEventListener('htmx:afterSwap', function() {
    const hasLoadedReportPart = document.querySelector('.loaded-report-part') !== null;
    const isLoadingDiv = document.getElementById('is-loading');
    const hasLoadedDiv = document.getElementById('intro-after-loading');

    if (hasLoadedReportPart) {
      isLoadingDiv.classList.add('fade-out');
      setTimeout(function(){
          hasLoadedDiv.classList.add('fade-in');
      }, 500);
    }
});

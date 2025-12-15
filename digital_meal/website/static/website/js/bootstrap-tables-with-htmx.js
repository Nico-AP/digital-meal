function initBootstrapTables(container) {
  $(container).find('[data-toggle="table"]').each(function() {
    if (!$(this).data('bootstrap.table')) {
      $(this).bootstrapTable();
    }
  });
}

// Initial page load
$(document).ready(function() {
  initBootstrapTables(document.body);
});

// After htmx swaps
document.body.addEventListener('htmx:afterSwap', function(evt) {
  initBootstrapTables(evt.detail.target);
});

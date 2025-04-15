function showHideSubModules(item) {
  let idToShow = '#'.concat($(item).attr('for'), '-sub-modules');
  $('#sub-module-placeholder').hide();
  $('.mt-sub-module-container').hide();
  $(idToShow).show();
}

function selectModule(moduleId) {
  let selectId = '#id_base_module';
  $(selectId).val(moduleId).change();
}

function selectSubModule(subModuleId, moduleId) {
  let selectId = '#id_sub_modules';
  let option = $(selectId + ' option[value=' + subModuleId + ']');
  let count = $('#module-counter-' + moduleId).text();

  if( $(option).attr('selected') ) {
    $(option).attr('selected', false);
    count--;
  } else {
    $(option).attr('selected', true);
    count++;
  }
  $(selectId).change();
  $('#module-counter-' + moduleId).text(count);
}

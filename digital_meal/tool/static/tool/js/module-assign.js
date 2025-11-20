function showHideSubModules(item) {
  let idToShow = '#'.concat(item.getAttribute('for'), '-sub-modules');

  // Hide the placeholder
  document.getElementById('sub-module-placeholder').style.display = 'none';

  // Hide all sub-module containers
  document.querySelectorAll('.mt-sub-module-container').forEach(el => {
    el.style.display = 'none';
  });

  // Show the target sub-module container
  document.querySelector(idToShow).style.display = 'block';
}

function selectModule(moduleId) {
  let selectId = '#id_base_module';
  const selectElement = document.querySelector(selectId);
  selectElement.value = moduleId;
  selectElement.dispatchEvent(new Event('change'));
}

function selectSubModule(subModuleId, moduleId) {
  let selectId = '#id_sub_modules';
  const selectElement = document.querySelector(selectId);
  const option = selectElement.querySelector('option[value="' + subModuleId + '"]');
  const counterElement = document.getElementById('module-counter-' + moduleId);
  let count = parseInt(counterElement.textContent);

  if (option.hasAttribute('selected')) {
    option.removeAttribute('selected');
    count--;
  } else {
    option.setAttribute('selected', 'selected');
    count++;
  }

  selectElement.dispatchEvent(new Event('change'));
  counterElement.textContent = '' + count;
}

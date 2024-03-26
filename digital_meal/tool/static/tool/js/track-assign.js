function showHideSubTracks(item) {
  let idToShow = '#'.concat($(item).attr('for'), '-subtracks');
  $('#sub-task-placeholder').hide();
  $('.mt-subtrack-container').hide();
  $(idToShow).show();
}

function selectTrack(trackId) {
  let selectId = '#id_track';
  $(selectId).val(trackId).change();
}

function selectSubTrack(trackId) {
  let selectId = '#id_sub_tracks';
  let option = $(selectId + ' option[value=' + trackId + ']')

  if( $(option).attr('selected') ) {
    $(option).attr('selected', false);
  } else {
    $(option).attr('selected', true);
  }
  $(selectId).change();
}

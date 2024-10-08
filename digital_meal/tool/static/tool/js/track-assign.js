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

function selectSubTrack(subTrackId, trackId) {
  let selectId = '#id_sub_tracks';
  let option = $(selectId + ' option[value=' + subTrackId + ']');
  let count = $('#modul-counter-' + trackId).text();

  if( $(option).attr('selected') ) {
    $(option).attr('selected', false);
    count--;
  } else {
    $(option).attr('selected', true);
    count++;
  }
  $(selectId).change();
  $('#modul-counter-' + trackId).text(count);
}

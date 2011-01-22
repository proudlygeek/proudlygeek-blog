/* Author: scroolose 
http://got-ravings.blogspot.com/2010/06/line-numbers-in-embedded-gists.html
*/

function addLineNumbersToAllGists() {
  $('.gist').each( function() {
      _addLineNumbersToGist('#' + $(this).attr('id'));
  });
}

function addLineNumbersToGist(id) {
  _addLineNumbersToGist('#gist-' + id);
}

function _addLineNumbersToGist(css_selector) {
  $(document).ready( function() {
    $(css_selector + ' .line').each(function(i, e) {
      $(this).prepend(
        $('<div/>').css({
          'float' : 'left',
          'width': '30px',
          'font-weight' : 'bold',
          'color': '#808080'
        }).text(++i)
      );
    });
  });
}

























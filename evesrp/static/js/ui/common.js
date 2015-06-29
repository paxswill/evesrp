var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

if (! ('ui' in EveSRP)) {
  EveSRP.ui = {}
}

EveSRP.ui.setLanguage = function setLanguage(ev) {
  var $target = $(ev.target),
      locale = $target.data('lang'),
      $form = $target.closest('form'),
      $localeInput = $form.find('#lang');
  $localeInput.val(locale);
  $form.submit();
  ev.preventDefault();
};

EveSRP.ui.renderFlashes = function renderFlashes(data) {
  var $content = $('#content'),
      flashes = data.flashed_messages;
  for (index in flashes) {
    var flashID = _.random(10000),
        flashInfo = flashes[index],
        flash;
    flashInfo.id = flashID;
    flash = Handlebars.templates.flash(flashes[index])
    $content.prepend(flash);
    window.setTimeout(function() {
      $('#flash-' + flashID).alert('close');
    }, 5000);
  }
};

EveSRP.ui.renderNavbar = function renderNavbar(data) {
  var navCounts = data.nav_counts;
  _.each(navCounts, function(count, key) {
    var $badge = $('#badge-' + key);
    if (count != 0) {
      $badge.text(count);
    } else {
      $badge.text('');
    }
  });
};

EveSRP.ui.setupEvents = function setupUIEvents() {
  $(document).ajaxComplete(function(ev, jqxhr) {
    var data = jqxhr.responseJSON;
    if (data && 'flashed_messages' in data) {
      EveSRP.ui.renderFlashes(jqxhr.responseJSON);
    }
    if (data && 'nav_counts' in data) {
      EveSRP.ui.renderNavbar(jqxhr.responseJSON);
    }
  });
  $(".langSelect").on('click', EveSRP.ui.setLanguage);
};
EveSRP.ui.setupEvents();

EveSRP.ui.setupClipboard = function setupClipboard() {
  ZeroClipboard.config({
    moviePath: $SCRIPT_ROOT + '/static/ZeroClipboard.swf'
  })
  /* Attach the pastboard object */
  EveSRP.ui.clipboardClient = new ZeroClipboard($('.copy-btn'));
}

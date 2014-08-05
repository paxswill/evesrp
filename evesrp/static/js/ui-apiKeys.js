var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

if (! ('ui' in EveSRP)) {
  EveSRP.ui = {}
}

EveSRP.ui.apiKeys = {

  render: function renderAPIKeys(data) {
    var $table = $('#apikeys'),
    $heading = $table.find('tr:first'),
        $oldRows = $table.find('tr').not(':first').not(':last'),
        $copyButtons = $oldRows.find('.copy-btn'),
        $newRows;
    // Remove tooltips and detach clipboard events
    EveSRP.ui.clipboardClient.unclip($copyButtons);
    $copyButtons.find('.copy-btn').each(function(i, btn) {
      $(btn).tooltip('destroy');
    });
    // Attach event listeners and tooltips
    $newRows = $(Handlebars.templates.api_keys(data));
    $copyButtons = $newRows.find('.copy-btn');
    EveSRP.ui.clipboardClient.clip($copyButtons);
    $copyButtons.tooltip({
      placement: 'bottom',
      title: 'Copy to clipboard',
      trigger: 'manual focus'
    });
    // Out with the old, in with the new
    $oldRows.remove();
    $heading.after($newRows);
  },

  modifyKey: function modifyKey(ev) {
    var $target = $(ev.target),
        $form = $target.closest('form');
    $.ajax( {
      type: 'POST',
      url: window.location.pathname,
      data: $form.serialize(),
      complete: function addModifierComplete(jqxhr) {
        EveSRP.ui.apiKeys.render(jqxhr.responseJSON);
      }
    });
    return false;
  },

  setupEvents: function setupAPIKeyEvents() {
    EveSRP.ui.setupClipboard();
    $('#apikeys').on('submit', EveSRP.ui.apiKeys.modifyKey);
    $('#ckreateKey').on('submit', EveSRP.ui.apiKeys.modifyKey);
  }
};
EveSRP.ui.apiKeys.setupEvents();

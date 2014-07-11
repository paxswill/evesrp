var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

if (! ('ui' in EveSRP)) {
  EveSRP.ui = {}
}

EveSRP.ui.division = {
  render: function render(entities) {
    var perms = ['submit', 'review', 'pay', 'admin'], i;
    for (i = 0; i < perms.length; ++i) {
      var perm = perms[i],
          $table = $('#' + perm).find('table'),
          $newTable = Handlebars.templates.entity_table({
            entities:entities[perm],
            name: perm
          });
      $table.replaceWith($newTable);
    }
  },

  selectAttribute: function selectAttribute() {
    var $attr = $(this).find('option:selected').val();
    if (attr !== '') {
      $(this).find('option[value=""]').remove();
    }
    $.ajax( {
      type: 'GET',
      url: window.location.pathname + 'transformers/' + attr + '/',
      success: function(data) {
        var $transformerSelect = $('select#transformer'),
            choices;
        $transformerSelect.empty();
        choices = data[attr];
        if (choices.length === 1) {
          $transformerSelect.prop('disabled', true);
        } else {
          $transformerSelect.prop('disabled', false);
        }
        $.each(choices, function(i, choice) {
          var $option = $('<option></option>');
          option.append(choice[1]);
          option.attr('value', choice[0]);
          if (choice[2] === true) {
            option.prop('selected', true);
          }
          $transformerSelect.append(option);
        });
      }
    });
    return true;
  },

  selectTransformer: function selectTransformer() {
    var $this = $(this),
        $attrName = $('select#attribute option:selected').text(),
        $transformerName = $this.find('option:selected').text(),
        $form = $this.parents('form');
    $.ajax( {
      type: 'POST',
      url: window.location.pathname,
      data: form.serialize()
    });
    return true;
  },

  changePermission: function changePermission(ev) {
    var $form;
    if ('originalEvent' in ev) {
      $form = $(ev.originalEvent.target);
    } else {
      $form = $(ev.target);
    }
    $.ajax({
      type: 'POST',
      url: window.location.pathname,
      data: $form.serialize(),
      success: function(data) {
        // Clear the now added value
        $form.find('.entity-typeahead').typeahead('val', '');
        $form.find('#id_').val('');
      },
      complete: function(jqxhr) {
        var data = jqxhr.responseJSON;
        renderEntities(data['entities']);
      }
    });
    return false;
  },

  setupEvents: function setupDivisionEvents() {
    $("select#attribute").change(EveSRP.ui.division.selectAttribute);
    $("select#transformer").change(EveSRP.ui.division.selectTransformer);
    $(".permission").submit(EveSRP.ui.division.changePermission);
  }
};
EveSRP.ui.division.setupEvents();

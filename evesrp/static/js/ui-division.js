var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

if (! ('ui' in EveSRP)) {
  EveSRP.ui = {}
}

EveSRP.ui.division = {
  render: function render(entities) {
    var perms = ['submit', 'review', 'pay', 'audit', 'admin'], i;
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

  setEntityID: function setEntityID(ev, datum, dataset) {
    // set the entity ID for the appropriate input box
    $(this)
      .closest('form')
      .find("input[name='id_']")
      .attr('value', datum['id']);
  },

  createEntitySource: function createEntitySource() {
    var entitySource = new Bloodhound({
      datumTokenizer: Bloodhound.tokenizers.obj.nonword('name'),
      queryTokenizer: Bloodhound.tokenizers.nonword,
      prefetch: {
        url: $SCRIPT_ROOT + '/api/entities/',
        ttl: 1800000,
        filter: function(list) {
          return list['entities'];
        }
      }
    });
    entitySource.initialize();
    return entitySource;
  },

  createTypeahead: function createTypeahead(selector, source) {
    var $typeahead = $(selector).typeahead(
      {
        hint: true,
        highlight: true
      },
      {
        displayKey: 'name',
        source: source.ttAdapter(),
        templates: {
          suggestion: Handlebars.templates.typeahead_suggestion,
          empty: Handlebars.templates.typeahead_empty
        }
      }
    );
    return $typeahead;
  },

  selectAttribute: function selectAttribute() {
    var $this = $(this),
        attr = $this.find('option:selected').val();
    if (attr !== '') {
      $this.find('option[value=""]').remove();
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
          $option.append(choice[1]);
          $option.attr('value', choice[0]);
          if (choice[2] === true) {
            $option.prop('selected', true);
          }
          $transformerSelect.append($option);
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
      data: $form.serialize()
    });
    return true;
  },

  changePermission: function changePermission(ev, datum, dataset) {
    var $form = $(ev.target);
    if (datum !== undefined) {
      EveSRP.ui.division.setEntityID(ev, datum, dataset);
      $form = $form.closest('form')
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
        EveSRP.ui.division.render(data['entities']);
      }
    });
    return false;
  },

  setupEvents: function setupDivisionEvents() {
    // Setup the typeaheads
    var entitySource = EveSRP.ui.division.createEntitySource();
    EveSRP.ui.division.createTypeahead('.entity-typeahead', entitySource)
      .on('typeahead:autocompleted', EveSRP.ui.division.setEntityID)
      .on('typeahead:cursorchanged', EveSRP.ui.division.setEntityID)
      .on('typeahead:selected', EveSRP.ui.division.changePermission);

    $("select#attribute").change(EveSRP.ui.division.selectAttribute);
    $("select#transformer").change(EveSRP.ui.division.selectTransformer);
    $(".permission").submit(EveSRP.ui.division.changePermission);
  }
};
EveSRP.ui.division.setupEvents();

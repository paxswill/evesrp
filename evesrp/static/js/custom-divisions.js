$("select#attribute").change( function() {
  var attr = $(this).find("option:selected").val()
  if (attr !== '') {
    $(this).find("option[value='']").remove();
  }
  $.getJSON(
    window.location.pathname + "transformers/" + attr + "/",
    function(data) {
      var transform_select = $("select#transformer");
      transform_select.empty();
      var choices = data[attr];
      if (choices.length === 1) {
        transform_select.prop('disabled', true);
      } else {
        transform_select.prop('disabled', false);
      }
      $.each(choices, function(i, choice) {
        var option = $("<option></option>");
        option.append(choice[1]);
        option.attr("value", choice[0]);
        if (choice[2] === true) {
          option.prop('selected', true);
        }
        transform_select.append(option);
      });
    }
  );
});

$("select#transformer").change( function() {
  var attr_name = $("select#attribute option:selected").text();
  var transformer_name = $(this).find("option:selected").text();
  var form = $(this).parents("form");
  $.post(
    window.location.pathname,
    form.serialize(),
    function() {
      flash(
        '"' + attr_name + '" transformer set to "' + transformer_name + '".',
        'info'
      );
    }
  );
});

function renderEntities(entities) {
  var perms = ['submit', 'review', 'pay', 'admin'];
  for (var i = 0; i < perms.length; ++i) {
    var perm = perms[i],
        $table = $('#' + perm).find('table'),
        $newTable = Handlebars.templates.entity_table({
          entities:entities[perm],
          name: perm
        });
    $table.replaceWith($newTable);
  }
}

$(".permission").submit( function(e) {
  var $form;
  if ('originalEvent' in e) {
    $form = $(e.originalEvent.target);
  } else {
    $form = $(e.target);
  }
  $.ajax({
    type: 'POST',
    url: window.location.pathname,
    data: $form.serialize(),
    success: function(data) {
      // Clear the now added value
      $form.find('.entity-typeahead').typeahead('val', '');
    },
    complete: function(jqxhr) {
      var data = jqxhr.responseJSON;
      renderEntities(data['entities']);
      renderFlashes(data);
    }
  });
  return false;
});

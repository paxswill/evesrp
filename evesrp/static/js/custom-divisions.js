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

function flash(message, category){
  var flashed = $("<div></div>");
  flashed.addClass("alert alert-dismissable");
  flashed.addClass("alert-" + category);
  var close_button = $("<button>&times;</button>");
  close_button.attr('type', 'button');
  close_button.attr('data-dismiss', 'alert');
  close_button.addClass('close');
  flashed.append(close_button);
  flashed.append(message);
  $("#content").prepend(flashed);
}

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

function rebuild_entities(permission) {
  $.getJSON(
    '/api' + window.location.pathname + permission + '/',
    function(data) {
      var table = $("#" + permission).find("table");
	  var new_table = Handlebars.templates.entity_table(data);
	  table.replaceWith(new_table);
    }
  );
}

$(".permission").submit( function(e) {
  var form = $(e.originalEvent.target);
  var permission = $(this).attr("id");
  var permission_title = $(this).children("h2").text().slice(0, -1);
  var entity_name = form.find("input[name='name']").val();
  if (entity_name === undefined) {
    entity_name = form.closest("tr").find("td").first().text();
  }
  $.post(
    window.location.pathname,
    form.serialize(),
    function() {
      var status_string;
      var action = form.find("input[name='action']").val();
      if (action === "add") {
        status_string = "' is now a ";
      } else if (action === "delete") {
        status_string = "' is no longer a ";
      }
      flash(
        "'" + entity_name + status_string + permission_title.toLowerCase(),
        'info'
      );
      rebuild_entities(permission)
    }
  );
  return false;
});

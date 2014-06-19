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

function form_data(form){
  
}

$("select#transformer").change( function() {
  var attr_name = $("select#attribute option:selected").text();
  var transformer_name = $(this).find("option:selected").text();
  var form = $(this).parents("form");
  $.post(
    window.location.pathname,
    form.serialize(),
    function() {
      var flashed = $("<div></div>");
      flashed.addClass("alert alert-info");
      flashed.append('"' + attr_name + '" transformer set to "' + transformer_name + '".');
      $("#content").prepend(flashed);
    }
  );
});

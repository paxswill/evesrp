$("ul#action-type li a").click( function (e) {
  var form = $(this).closest("form");
  form.find("input[name='type_']").attr("value", $(this).attr("id"));
  form.submit();
  return false;
});
$("ul#modifier-type li a").click( function(e) {
  var form = $(this).closest("form");
  form.find("input[name='type_']").attr("value", $(this).attr("id"));
  form.submit();
  return false;
});

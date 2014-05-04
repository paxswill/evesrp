/*
 * Make the link in button dropdowns submit the form
 */

$("ul#request-action-type li a").click( function (e) {
  var form = $(this).closest("form");
  form.find("input[name='type_']").attr("value", $(this).attr("id"));
  form.submit();
  return false;
});

$("ul#request-modifier-type li a").click( function(e) {
  var form = $(this).closest("form");
  form.find("input[name='type_']").attr("value", $(this).attr("id"));
  form.submit();
  return false;
});

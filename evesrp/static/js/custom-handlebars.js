Handlebars.registerHelper('csrf', function() {
  return $("meta[name='csrf_token']").attr("content");
});

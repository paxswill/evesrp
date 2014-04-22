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

var users = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.nonword('name'),
  queryTokenizer: Bloodhound.tokenizers.nonword,
  prefetch: {
    url: $SCRIPT_ROOT + '/api/user/',
    filter: function(list) {
      return list['users'];
    }
  }
});

var groups = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.nonword('name'),
  queryTokenizer: Bloodhound.tokenizers.nonword,
  prefetch: {
    url: $SCRIPT_ROOT + '/api/group/',
    filter: function(list) {
      return list['groups'];
    }
  }
});

groups.initialize();
users.initialize();

$('.entity-typeahead').typeahead({
  hint: true,
  highlight: true
},
{
  name: 'users',
  displayKey: 'name',
  source: users.ttAdapter(),
  templates: {
    suggestion: function(obj) {
      return '<p>' + obj['name'] + ' <small class="text-muted">User</small></p>';
    }
  }
},
{
  name: 'groups',
  displayKey: 'name',
  source: groups.ttAdapter(),
  templates: {
    suggestion: function(obj) {
      return '<p>' + obj['name'] + ' <small class="text-muted">Group</small></p>';
    }
  }
});

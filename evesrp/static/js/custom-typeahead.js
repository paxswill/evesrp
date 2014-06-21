/*
 * Autocomplete for divisions detail
 */

if ($('.entity-typeahead').length) {
  /* seth the entity ID for the appropriate input box */
  function setEntityID(ev, datum, dataset) {
    $(this).closest('form').find("input[name='id_']").attr('value', datum['id']);
  }
  /* Setup the data sources */
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

  /* Create the typeahead */
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
  })
  .on('typeahead:autocompleted', setEntityID)
  .on('typeahead:cursorchanged', setEntityID)
  .on('typeahead:selected', function(ev, datum, dataset) {
    setEntityID(ev, datum, dataset);
    $(this).closest('form').submit();
  });
}

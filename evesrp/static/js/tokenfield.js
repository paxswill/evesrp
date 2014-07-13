var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

EveSRP.tokenfield = {

  addedToken: function addedToken(ev) {
    /* Apply the filter */
    function _add(item) {
      var requests = EveSRP.ui.requestList.requests;
      if (item.attr === 'details') {
        requests.filters.details.unionQuery(item.real_value);
      } else {
        requests.filters[item.attr].unionQuery(item.real_value);
      }
    }
    if (ev.attrs instanceof Array) {
      for (var i = 0; i < ev.attrs.length; ++i) {
        _add(ev.attrs[i]);
      }
    } else {
      _add(ev.attrs);
    }
  },

  modifyToken: function modifyToken(ev) {
    /* format the value and label */
    function _modify(item) {
      if (item.attr === undefined) {
        var data = item.label.split(':');
        if (data.length === 1) {
          item.attr = 'details';
          item.real_value = data[0];
          item.value = 'details:' + data[0];
        } else {
          item.attr = data[0];
          if (item.attr === 'status') {
            item.real_value = data.slice(1).join(':').toLowerCase();
          } else {
            item.real_value = data.slice(1).join(':');
          }
        }
      }
      item.label = item.value;
    }
    if (ev.attrs instanceof Array) {
      for (var i = 0; i < ev.attrs.length; ++i) {
        _modify(ev.attrs[i]);
      }
    } else {
      _modify(ev.attrs)
    }
  },

  removedToken: function removedToken(ev) {
    /* Remove the filter */
    function _remove(item) {
      var requests = EveSRP.ui.requestList.requests;
      requests.filters[item.attr].removeSingleQuery(item.real_value);
    }
    if (ev.attrs instanceof Array) {
      for (var i = 0; i < ev.attrs.length; ++i) {
        _remove(ev.attrs[i]);
      }
    } else {
      _remove(ev.attrs);
    }
  },

  createBloodhound: function createTokenFieldBloodhound(attribute, values) {
    var source, bloodhound;
    source = $.map(values, function(v) {
      return {
        real_value: v,
        attr: attribute
      };
    });
    bloodhound = new Bloodhound({
      name: attribute,
      datumTokenizer: function(datum) {
        var tokens = datum.real_value.split(/\s+/);
        tokens.push(datum.attr + ':' + tokens[0]);
        return tokens;
      },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      local: source
    });
    bloodhound.initialize();
    return bloodhound;
  },

  attachTokenfield: function attachTokenfield($input, bloodhounds) {
    /* Create the typeahead arguments */
    var typeahead_args = [],
        tokenfield;
    typeahead_args.push({
      hint: true,
      highlight: true
    });
    function superBloodhound(query, cb) {
      var category_query = query.split(':');
      attribute = category_query[0];
      real_query = category_query.slice(1).join(':');
      if (real_query === '') {
        real_query = attribute;
        attribute = '';
      }
      if (bloodhounds[attribute] !== undefined) {
        bloodhounds[attribute].get(real_query, cb);
      } else {
        var results = new Object;
        for (attr in bloodhounds) {
          bloodhounds[attr].get(real_query, function(matches) {
            results[attr] = matches;
            var all_back = true;
            for (attr2 in bloodhounds) {
              if (results[attr2] === undefined) {
                all_back = false;
                break;
              }
            }
            if (all_back) {
              var all_matches = [];
              $.each(results, function(key) {
                Array.prototype.push.apply(all_matches, results[key]);
              });
              cb(all_matches);
            }
          });
        }
      }
    }
    typeahead_args.push({
      name: 'all_args',
      displayKey: function(value) {
        if (value.attr === 'status') {
          var capitalized = value.real_value.substr(0, 1).toUpperCase();
          capitalized = capitalized + value.real_value.slice(1);
          return value.attr + ':' + capitalized;
        } else {
          return value.attr + ':' + value.real_value;
        }
      },
      source: superBloodhound
    });
    /* Create the tokenfield and listeners */
    tokenfield = $input.tokenfield({
      typeahead: typeahead_args
    })
    .on('tokenfield:createtoken', EveSRP.tokenfield.modifyToken)
    .on('tokenfield:createdtoken', EveSRP.tokenfield.addedToken)
    .on('tokenfield:removetoken', EveSRP.tokenfield.removedToken);
    return tokenfield;
  }
}

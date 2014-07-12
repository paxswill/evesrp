var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

EveSRP.tokenfield = {

  addedToken: function addedToken(ev) {
    /* Apply the filter */
    function _add(attr) {
      var requests = EveSRP.ui.requestList.requests;
      requests.filters[attr.attr].unionQuery(attr.real_value);
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
    function _modify(attr) {
      if (attr.attr === undefined) {
        var data = attr.label.split(':');
        attr.attr = data[0];
        if (attr.attr === 'status') {
          attr.real_value = data.slice(1).join(':').toLowerCase();
        } else {
          attr.real_value = data.slice(1).join(':');
        }
      }
      attr.label = attr.value;
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
    function _remove(attr) {
      var requests = EveSRP.ui.requestList.requests;
      requests.filters[attr.attr].removeSingleQuery(attr.real_value);
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
    var typeahead_args = [];
    typeahead_args.push({
      hint: false,
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
    return $input.tokenfield({
      typeahead: typeahead_args
    })
    .on('tokenfield:createtoken', EveSRP.tokenfield.modifyToken)
    .on('tokenfield:createdtoken', EveSRP.tokenfield.addedToken)
    .on('tokenfield:removetoken', EveSRP.tokenfield.removedToken);
  }
}

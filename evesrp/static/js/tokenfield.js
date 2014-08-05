var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

EveSRP.tokenfield = {

  addedToken: function addedToken(ev) {
    /* Apply the filter */
    var fullPath = EveSRP.util.splitFilterString(window.location.pathname),
        filters = EveSRP.util.parseFilterString(fullPath[1]),
        state = History.getState(),
        diffKeys;
    function _add(item) {
      var fullValue;
      // Ensure there's a place to put new queries
      if (! (item.attr in filters)) {
        filters[item.attr] = [];
      }
      if (item.sign !== '=') {
        fullValue = item.sign + item.real_value;
      } else {
        fullValue = item.real_value;
      }
      filters[item.attr] = _(filters[item.attr]).union([fullValue]);
    }
    if (ev.attrs instanceof Array) {
      for (var i = 0; i < ev.attrs.length; ++i) {
        _add(ev.attrs[i]);
      }
    } else {
      _add(ev.attrs);
    }
    // Double check that the default 'filters' are present
    _.defaults(state.data, {page: 1, sort: '-submit_timestamp'});
    _.defaults(filters, {page: 1, sort: '-submit_timestamp'});
    // Only push a new state if there's actually new filters
    if (! _.isEqual(state.data, filters)) {
      // Compare the existing filters to the new filters
      diffKeys = EveSRP.util.keyDifference(state.data, filters);
      // Go to page 1 when changing filters
      if (! _.contains(diffKeys, 'page')) {
        filters.page = 1;
      }
      fullPath[1] = EveSRP.util.unparseFilters(filters);
      History.pushState(filters, null, '/' + fullPath.join('/'));
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
          item.sign = '=';
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
    var fullPath = EveSRP.util.splitFilterString(window.location.pathname),
        filters = EveSRP.util.parseFilterString(fullPath[1]);
    /* Remove the filter */
    function _remove(item) {
      var fullValue;
      if (item.sign !== '=') {
        fullValue = item.sign + item.real_value;
      } else {
        fullValue = item.real_value;
      }
      filters[item.attr] = _(filters[item.attr]).without(fullValue);
      if (_.isEmpty(filters[item.attr])) {
        delete filters[item.attr];
      }
    }
    if (ev.attrs instanceof Array) {
      for (var i = 0; i < ev.attrs.length; ++i) {
        _remove(ev.attrs[i]);
      }
    } else {
      _remove(ev.attrs);
    }
    fullPath[1] = EveSRP.util.unparseFilters(filters);
    History.pushState(filters, null, '/' + fullPath.join('/'));
  },

  attachTokenfield: function attachTokenfield($input, bloodhound) {
    /* Create the typeahead arguments */
    var typeahead_args = [],
        tokenfield, state, fullPath, filter, tokens;
    typeahead_args.push({
      hint: false,
      highlight: true
    });
    typeahead_args.push({
      name: 'all_args',
      displayKey: function(value) {
        var capitalized;
        if (value.attr === 'status') {
          capitalized = value.real_value.substr(0, 1).toUpperCase();
          capitalized = capitalized + value.real_value.slice(1);
          return value.attr + ':' + capitalized;
        } else {
          if (value.sign === '=') {
            return value.attr + ':' + value.real_value;
          } else {
            return value.attr + ':' + value.sign + value.real_value;
          }
        }
      },
      source: bloodhound.ttAdapter(),
      // Use a Handlebars template here for the autoescaping
      templates: {
        suggestion: Handlebars.templates.filter_suggestion
      }
    });
    // Get the initial set of tokens
    state = History.getState();
    if (! _.isEmpty(state.data)) {
      filter = state.data;
    } else {
      fullPath = EveSRP.util.splitFilterString(window.location.pathname);
      filter = EveSRP.util.parseFilterString(fullPath[1]);
    }
    tokens = this.tokensFromFilter(filter);
    /* Create the tokenfield and listeners */
    tokenfield = $input.tokenfield({
      typeahead: typeahead_args,
      tokens: tokens
    })
    .on('tokenfield:createtoken', EveSRP.tokenfield.modifyToken)
    .on('tokenfield:createdtoken', EveSRP.tokenfield.addedToken)
    .on('tokenfield:removetoken', EveSRP.tokenfield.removedToken);
    $(window).on('statechange', function() {
      var state = History.getState(),
          tokens;
      tokens = EveSRP.tokenfield.tokensFromFilter(state.data);
      $(tokenfield).tokenfield('setTokens', tokens);
    });
    return tokenfield;
  },

  tokensFromFilter: function tokensFromFilter(filter) {
    var tokens = [];
    $.each(Object.keys(filter), function(i, attr) {
      if (attr !== 'sort' && attr !== 'page') {
        $.each(filter[attr], function (i2, value) {
          var label = attr + ':' + value,
              sign, realValue;
          if (_.contains('=-<>', value.slice(0, 1))) {
            sign = value.slice(0, 1);
            realValue = value.slice(1);
          } else {
            sign = '=';
            realValue = value;
          }
          tokens.push( {
            label: label,
            value: label,
            attr: attr,
            real_value: realValue,
            sign: sign
          });
        });
      }
    });
    return tokens;
  }
}

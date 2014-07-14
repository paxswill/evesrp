var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

if (! ('ui' in EveSRP)) {
  EveSRP.ui = {}
}

EveSRP.ui.requestList = {

  createPourOver: function createPourOver() {
  },

  markPaid: function markPaid(ev) {
    var $form = $(this).closest('form');
    $.ajax( {
      type: 'POST',
      url: $form.attr('action'),
      data: $form.serialize(),
      success: function() {
        var $row = $form.closest('tr'),
            itemID, item;
        itemID = $row.find('.col-id').last().text();
        itemID = parseInt(itemID, 10);
        item = ev.data.requests.getBy('id', itemID)[0];
        ev.data.requests.updateItem(item.cid, 'status', 'paid');
        $row.find('button').prop('disabled', true);
      }
    });
    return false;
  },

  changePage: function changePage(ev) {
    var requestView = ev.data.requestView,
        currentFilters;
    /* Set the view to the new page */
    if ($(this).attr('id') === 'prev_page') {
      requestView.page(-1);
    } else if ($(this).attr('id') == 'next_page') {
      requestView.page(1);
    } else {
      var pageNum = parseInt($(this).contents()[0].data, 10);
      // zero indexed pages
      pageNum = pageNum - 1;
      requestView.setPage(pageNum);
    }
    /* Fiddle with the browser history to keep the URL in sync */
    currentFilters = EveSRP.util.getFilterString(window.location.pathname);
    currentFilters = EveSRP.util.parseFilterString(currentFilters);
    History.pushState(currentFilters, null,
      EveSRP.util.unparseFilters(currentFilters));
    return false;
  },

  getColumns: function getColumns($rows) {
    var $headerRow;
    if ($rows === undefined) {
      $rows = $('table#requests tr').not($('.popover tr'));
    }
    $headerRow = $rows.first();
    return $headerRow.find('th').map(function(index, value) {
      return $(value).attr('id').substring(4);
    });
  },

  getRequests: function getRequests() {
    $.ajax(
      $SCRIPT_ROOT + '/api/filter' + window.location.pathname,
      {
        dataType: 'json',
        success: function(data) {
          var requests;
          requests = $.map(data['requests'],
            function (value) {
              /* Convert the dates into JS Dates */
              value['kill_timestamp'] = new Date(value['kill_timestamp']);
              value['submit_timestamp'] = new Date(value['submit_timestamp']);
              return value;
            });
          requests = new PourOver.Collection(requests);
          EveSRP.ui.requestList.requests = requests;
          EveSRP.ui.requestList.getAttributes();
        }
      }
    );
  },

  getAttributes: function getAttributes() {
    var deferredRequests, deferred,  attributes;
    // Filter out unsupported attributes
    attributes = [
      'pilot',
      'corporation',
      'alliance',
      'system',
      'constellation',
      'region',
      'ship',
      'status',
      'division',
      'details'
    ];
    // Get a promises for all the requests
    deferredRequests = $.map(attributes, function(column) {
      return EveSRP.util.getAttributeChoices(column);
    });
    // And wait for them all to complete
    deferred = $.when.apply($, deferredRequests);
    deferred.done(function() {
        var requests = EveSRP.ui.requestList.requests,
            requestView;
        // Create PourOver filters
        $.each(arguments, function(i, data) {
          var filter, key, value;
          if ($.isArray(data)) {
            data = data[0];
          }
          key = data.key;
          value = data[data.key];
          if (value !== null) {
            filter = PourOver.makeExactFilter(key, value);
          } else {
            filter = EveSRP.pourover.makeBufferedFilter(key);
          }
          requests.addFilters(filter);
        });
        // Create the PourOver View
        EveSRP.pourover.addRequestSorts(requests);
        requestView = new EveSRP.pourover.RequestsView('requests', requests)
        requestView.on('update', requestView.render);
        EveSRP.ui.requestList.requestView = requestView
        $('ul.pagination > li > a').on('click', {requestView: requestView},
          EveSRP.ui.requestList.changePage);
      })
      .done(function(responses) {
        // Create Bloodhounds
        var bloodhounds = [],
            tokenfield, state;
        $.each(arguments, function(i, data) {
          var key, value;
          if ($.isArray(data)) {
            data = data[0];
          }
          key = data.key;
          value = data[data.key];
          if (value !== null) {
            bloodhounds.push(EveSRP.tokenfield.createBloodhound(
                key, value));
          }
        });
        tokenfield = EveSRP.tokenfield.attachTokenfield($('.filter-tokenfield'),
          bloodhounds);
        // If there's a state already there, sync everything with it
        state = History.getState();
        if (state.data !== undefined && '_keys' in state.data) {
          EveSRP.ui.requestList.updateTokens(state.data);
        }
      });
  },

  setupEvent: function setupRequestListEvents() {
    // Setup ZeroClipboard
    ZeroClipboard.config({
      moviePath: $SCRIPT_ROOT + '/static/ZeroClipboard.swf'
    })
    /* Attach the pastboard object */
    EveSRP.ui.clipboardClient = new ZeroClipboard($('.copy-btn'));
    /* Initialize tooltips */
    $('.copy-btn').tooltip({trigger: 'manual'});
    EveSRP.ui.clipboardClient.on('mouseover', function (ev) {
      $(this).tooltip('show');
    }).on('mouseout', function(ev) {
      $(this).tooltip('hide');
    });
    /* Add paid button events */
    $('.paid-btn').click(EveSRP.ui.requestList.markPaid);
    // Attach column sort listeners
    $('th a.heading').click( function (e) {
      var $this = $(this),
          $heading = $this.parent('th'),
          colName = $heading.attr('id').substring(4),
          currentSort = EveSRP.ui.requestList.requestView.getSort(),
          newSort = '',
          direction;
      if (currentSort !== false) {
        if (currentSort.slice(0, -4) === colName) {
          /* swap the direction of the existing sort */
          direction = currentSort.slice(-3);
          if (direction === 'asc') {
            newSort = colName + '_dsc';
          } else if (direction === 'dsc') {
            newsort = colName + '_asc';
          }
        }
        /* remove the old direction arrow */
        $heading.siblings('th').find('i.fa').removeClass();
      }
      if (newSort === '') {
        newSort = colName + '_asc';
      }
      /* Set the direction arrows */
      direction = newSort.slice(-3);
      if (direction === 'asc') {
        $this.children('i').attr('class', 'fa fa-chevron-down');
      } else if (direction === 'dsc') {
        $this.children('i').attr('class', 'fa fa-chevron-up');
      }
      EveSRP.ui.requestList.requestView.setSort(newSort);
    });
    // Watch the history for state changes
    $(window).on('statechange', function(ev) {
      var requestView = EveSRP.ui.requestList.requestView,
          state = History.getState();
      EveSRP.ui.requestList.updateFilters(state.data);
      EveSRP.ui.requestList.updateTokens(state.data);
    });
  },

  updateFilters: function updateFilters(filters) {
    var _this = this,
        isCompound = function(c) {
          return _.isString(c) && c.match(/^(or|and|not)$/);
        };
    $.each(filters._keys, function(i, attr) {
      var values = filters[attr],
          currentValues = [],
          filter, removed, added;
      if (attr === 'page') {
        if (value !== _this.requestView.current_page) {
          _this.requestView.setPage(value);
        }
      } else if (attr === 'sort') {
        // TODO
      } else {
        filter = _this.requests.filters[attr];
        if ('current_query' in filter) {
          $.each(filter.current_query.stack, function(i, query) {
            if (isCompound(query[0])) {
              currentValues.push(query[1][0][1]);
            } else {
              currentValues.push(query[1]);
            }
          });
        }
        added = _(values).difference(currentValues);
        removed = _(currentValues).difference(values);
        $.each(added, function(i, v) {
          filter.unionQuery(v);
        });
        $.each(removed, function(i, v) {
          filter.removeSingleQuery(v);
        });
      }
    });
  },

  updateTokens: function updateTokens(filters_) {
    var $tokenfield = $('.filter-tokenfield'),
        tokens = $tokenfield.tokenfield('getTokens'),
        filters = $.extend(true, {}, filters_),
        index, attr, value, valIndex;
    // Remove tokens not in the filter
    for (index = 0; index < tokens.length; index++) {
      attr = tokens[index].attr;
      value = tokens[index].real_value;
      if ($.inArray(attr, filters._keys) !== -1) {
        valIndex = $.inArray(value, filters[attr]);
        if (valIndex === -1) {
          tokens.splice(index, 1);
          index--;
        } else {
          filters[attr].splice(valIndex, 1);
        }
      } else {
        tokens.splice(index, 1);
      }
    }
    // Add tokens for things still in the filter
    $.each(filters._keys, function(i, attr) {
      var values = filters[attr];
      if (attr !== 'page' && attr !== 'sort') {
        $.each(values, function(i, value) {
          var label = [attr, value].join(':');
          tokens.push( {
            attr: attr,
            real_value: value,
            label: label,
            value: label
          });
        });
      }
    });
    $tokenfield.tokenfield('setTokens', tokens);
  }
};
EveSRP.ui.requestList.getRequests();
EveSRP.ui.requestList.setupEvent()

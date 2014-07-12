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
      'division'
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
          var filter;
          if ($.isArray(data)) {
            data = data[0];
          }
          filter = PourOver.makeExactFilter(data.key, data[data.key]);
          requests.addFilters(filter);
        });
        // Create the PourOver View
        EveSRP.pourover.addRequestSorts(requests);
        requestView = new EveSRP.pourover.RequestsView('requests', requests)
        requestView.on('update', requestView.render);
        EveSRP.ui.requestList.requestView = requestView
        $('ul.pagination > li > a').on('click', {requestView: requestView},
          EveSRP.pourover.changePage);
      })
      .done(function(responses) {
        // Create Bloodhounds
        var bloodhounds;
        bloodhounds = $.map(arguments, function(data) {
          if ($.isArray(data)) {
            data = data[0];
          }
          return EveSRP.tokenfield.createBloodhound(data.key, data[data.key]);
        });
        var tokenfield = EveSRP.tokenfield.attachTokenfield($('.filter-tokenfield'),
          bloodhounds);
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
      if (state.data.page !== request_view.current_page) {
        requestView.setPage(state.data.page);
      }
      if (state.data.sort !== request_view.getSort()) {
        requestView.setSort(state.data.sort);
      }
    });
  }
};
EveSRP.ui.requestList.getRequests();
EveSRP.ui.requestList.setupEvent()

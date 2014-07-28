var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

if (! ('ui' in EveSRP)) {
  EveSRP.ui = {}
}

EveSRP.ui.requestList = {

  markPaid: function markPaid(ev) {
    var $form = $(ev.target).closest('form');
    $.ajax( {
      type: 'POST',
      url: $form.attr('action'),
      data: $form.serialize(),
      success: function() {
        var $row = $form.closest('tr');
        $row.removeClass();
        $row.addClass('success');
        $row.find('button').prop('disabled', true);
      }
    });
    return false;
  },

  setupTokenField: function setupTokenfield() {
    var deferredRequests, deferred, attributes;
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
    // Get promises for all the requests
    deferredRequests = $.map(attributes, function(column) {
      return EveSRP.util.getAttributeChoices(column);
    });
    // And wait for them all to complete
    deferred = $.when.apply($, deferredRequests);
    deferred.done(function(responses) {
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
    });
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

  pageSize: 15,

  render: function renderRequests(data, filters) {
    var $rows = $('table#requests tr').not($('.popover tr')),
        $rowsParent = $rows.parent(),
        $headers = $rows.first().find('th'),
        $oldRows = $rows.not(':first'),
        columns = this.getColumns($rows),
        isPayout = false,
        $pager = $('ul.pagination'),
        requests = data.requests,
        $summary = $('#requestsSummary'),
        $copyButtons, $newRows;
    if ($oldRows.length != 0) {
      /* Remove the tooltips and unattach the clipboard client from any
       * buttons
       * */
      $copyButtons = $oldRows.find('.copy-btn');
      if ($copyButtons.length != 0) {
        isPayout = true;
        EveSRP.ui.clipboardClient.unclip($copyButtons);
        $copyButtons.each(function (i, element) {
          $(element).tooltip('destroy');
        });
      }
      $oldRows.remove();
    }
    /* Rebuild the table */
    if (isPayout) {
      $newRows = $(Handlebars.templates.payout_rows(requests));
      $copyButtons = $newRows.find('.copy-btn');
      EveSRP.ui.clipboardClient.clip($copyButtons);
      $copyButtons.tooltip({trigger: 'manual focus'});
    } else {
      $newRows = Handlebars.templates.request_rows(requests);
    }
    $rowsParent.append($newRows);
    // Update the summary
    $summary.text(data['request_count'] + ' requests • ' +
                  data['total_payouts'] + ' ISK');
    // Render the pager
    this.renderPager(data.request_count, filters.page - 1);
  },

  renderPager: function renderPager(numRequests, currentPage) {
    var $pager = $('ul.pagination'),
        numPages = Math.ceil(numRequests/this.pageSize - 1) + 1;
    $pager.empty();
    if (numPages > 1) {
      $pager.removeClass('hidden');
      /* prev arrow */
      if (currentPage === 0) {
        $pager.append('<li class="disabled"><span>&laquo;</span></li>');
      } else {
        $pager.append('<li><a id="prev_page" href="#">&laquo;</a></li>');
      }
      /* Page numbers */
      pageNums = EveSRP.util.pageNumbers(numPages, currentPage);
      for (var i = 0; i < pageNums.length; ++i) {
        if (pageNums[i] !== null) {
          if (pageNums[i] !== currentPage) {
            $pager.append('<li><a href="#">' + (pageNums[i] + 1) + '</a></li>');
          } else {
            $pager.append('<li class="active"><a href="#">' + (pageNums[i] + 1) + '<span class="sr-only"> (current)</span></a></li>');
          }
        } else {
          $pager.append('<li class="disabled"><span>&hellip;</span></li>');
        }
      }
      /* next arrow */
      if (currentPage === numPages - 1) {
        $pager.append('<li class="disabled"><span>&raquo;</span></li>');
      } else {
        $pager.append('<li><a id="next_page" href="#">&raquo;</a></li>');
      }
    } else {
      $pager.addClass('hidden');
    }
  },

  getRequests: function getRequests() {
    var state = History.getState();
    $.ajax( {
      type: 'GET',
      url: state.url,
      success: function(data) {
        var filters, fullPath;
        if ('_keys' in state.data) {
          filters = state.data;
        } else {
          fullPath = EveSRP.util.splitFilterString(window.location.pathname);
          filters = EveSRP.util.parseFilterString(fullPath[1]);
        }
        EveSRP.ui.requestList.render(data, filters);
      }
    });
  },

  changeSort: function changeSort() {
    var $this = $(this),
        $heading = $this.parent('th'),
        $headings = $heading.parent().children('th'),
        colName = $heading.attr('id').substring(4),
        state = History.getState(),
        fullPath = EveSRP.util.splitFilterString(window.location.pathname),
        filters;
    // Fail fast for non-sortable columns
    if (colName === 'None') {
      return false;
    }
    // Check for a history state object first, fallback to parsing the URL
    if ('data' in state && '_keys' in state.data) {
      filters = state.data;
    } else {
      filters = EveSRP.util.parseFilterString(fullPath[1]);
    }
    // Determine new sort
    if (filters.sort.slice(1) === colName || filters.sort === colName) {
      if (filters.sort.charAt(0) === '-') {
        filters.sort = colName;
      } else {
        filters.sort = '-' + colName;
      }
    } else {
      filters.sort = colName;
    }
    // Update the arrows
    $headings.find('i.fa').removeClass();
    if (filters.sort.charAt(0) === '-') {
      $this.find('i').addClass('fa fa-chevron-down');
    } else {
      $this.find('i').addClass('fa fa-chevron-up');
    }
    // Push a new history state to trigger a refresh of the requests
    fullPath[1] = EveSRP.util.unparseFilters(filters);
    History.pushState(filters, null, '/' + fullPath.join('/'));
    return false;
  },

  changePage: function changePage(ev) {
    var fullPath = EveSRP.util.splitFilterString(window.location.pathname),
        filters = EveSRP.util.parseFilterString(fullPath[1]),
        $target = $(ev.target),
        pageNum;
    if ($target.attr('id') === 'prev_page') {
      filters.page = filters.page - 1;
    } else if ($target.attr('id') == 'next_page') {
      filters.page = filters.page + 1;
    } else {
      pageNum = parseInt($target.contents()[0].data, 10);
      filters.page = pageNum;
    }
    // trigger a redraw by updating the URL
    fullPath[1] = EveSRP.util.unparseFilters(filters);
    History.pushState(filters, null, '/' + fullPath.join('/'));
    return false;
  },

  setupEvents: function setupRequestListEvents() {
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
    $('#requests').on('submit', EveSRP.ui.requestList.markPaid);
    // Attach column sort listeners
    $('th a.heading').on('click', this.changeSort);
    // Attach page number change listeners
    $('ul.pagination').on('click', EveSRP.ui.requestList.changePage);
    // Watch the history for state changes
    $(window).on('statechange', this.getRequests);
  }
};
EveSRP.ui.requestList.setupEvents();
EveSRP.ui.requestList.setupTokenField();

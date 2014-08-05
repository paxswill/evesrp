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
    var attributes, bloodhound, bhDeferred;
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
    // Create the bloodhound
    bloodhound = new Bloodhound({
      name: 'tokens',
      local: [],
      datumTokenizer: function(datum) {
        var base_tokens, tokens = [];
        base_tokens = datum.real_value.split(/\s+/);
        // Push each whitespace split of real_value with the sign
        $.each(base_tokens, function(index, token) {
          if (datum.sign === '=') {
            // Push just the attribute name for scoped queries
            tokens.push(datum.attr)
            // Push the bare value for exact queries
            tokens.push(token);
          }
          tokens.push(datum.sign + token);
        });
        return tokens;
      },
      queryTokenizer: function(query) {
        var tokens = [],
            sign, attribute, attributeQuery, valueQuery, tempTokens;
        // Add the attribute if this query is scoped (in the form of attr:value)
        attributeQuery = query.split(':');
        attribute = attributeQuery[0];
        valueQuery = attributeQuery.slice(1).join(':');
        if (valueQuery === '') {
          valueQuery = attribute;
        } else {
          tokens.push(attribute);
        }
        // Add search tokens for the value
        if (_.contains(['-', '=', '<', '>'], valueQuery.slice(0, 1))) {
          sign = valueQuery.slice(0, 1);
          tempTokens = valueQuery.slice(1).split(/\s+/);
          tempTokens = _.map(tokens, function(value) {
            return sign + tokens;
          });
        } else {
          tempTokens = valueQuery.split(/\s+/);
        }
        Array.prototype.push.apply(tokens, tempTokens);
        return tokens;
      },
    });
    bhDeferred = bloodhound.initialize();
    // Add the values for each attribute to the bloodhound
    $.each(attributes, function(i, attr) {
      var ajax = EveSRP.util.getAttributeChoices(attr);
      $.when(ajax, bhDeferred).done(function(data, bhDeferred) {
        var source = [],
            key, values;
        if ($.isArray(data)) {
          data = data[0];
        }
        key = data.key;
        values = data[data.key];
        if (values !== null) {
          $.each(values, function(i, value) {
            if (! _.contains(['details', 'status'], key)) {
              $.each(['=', '-', '<', '>'], function(i, sign) {
                source.push({
                  real_value: value,
                  attr: key,
                  sign: sign
                });
              });
            } else {
              source.push({
                real_value: value,
                attr: key,
                sign: '='
              });
            }
          });
          bloodhound.add(source);
        }
      });
    });
    // Attach the tokenfield
    tokenfield = EveSRP.tokenfield.attachTokenfield($('.filter-tokenfield'),
      bloodhound);
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
      // Remove the tooltips and unattach the clipboard client from any buttons
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
    $rowsParent.find('.filterable a')
      .on('click', EveSRP.ui.requestList.addQuickFilter);
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
        if (! _.isEmpty(state.data)) {
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
    if (! _.isEmpty(state.data)) {
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

  addQuickFilter: function addQuickFilter(ev) {
    var $cell = $(ev.target).closest('td'),
        token = {sign: '='};
    token.attr = $cell.data('attribute');
    token.real_value = $cell.text();
    if (token.attr === 'status') {
      token.real_value = token.real_value.toLowerCase();
    }
    token.value = token.label = token.attr + ':' + token.real_value;
    $('.filter-tokenfield').tokenfield('createToken', token);
    return false;
  },

  setupEvents: function setupRequestListEvents() {
    EveSRP.ui.setupClipboard();
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
    // Attach quick filtering listeners
    $('.filterable a').on('click', EveSRP.ui.requestList.addQuickFilter);
    // Watch the history for state changes
    $(window).on('statechange', this.getRequests);
  }
};
if ($('.filter-tokenfield').length !== 0) {
  EveSRP.ui.requestList.setupEvents();
  EveSRP.ui.requestList.setupTokenField();
}

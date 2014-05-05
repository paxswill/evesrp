/*
 * Filterable lists with PourOver
 */

/* Map month integers to month abbreviations */
function month(month_int) {
  switch (month_int) {
    case 0:
      return 'Jan';
    case 1:
      return 'Feb';
    case 2:
      return 'Mar';
    case 3:
      return 'Apr';
    case 4:
      return 'May';
    case 5:
      return 'Jun';
    case 6:
      return 'Jul';
    case 7:
      return 'Aug';
    case 8:
      return 'Sep';
    case 9:
      return 'Oct';
    case 10:
      return 'Nov';
    case 11:
      return 'Dec';
  }
};

/* Pad num to width with 0s */
function padNum (num, width) {
  /* coerce to a string */
  num = num + '';
  while (num.length < width) {
    num = 0 + num;
  }
  return num;
}

/* return an array of page numbers, skipping some of them as configured by the
 * options argument. This function should be functionally identical to
 * Flask-SQLAlchemy's
 * :py:method:`Pagination.iter_pages <flask.ext.sqlalchemy.Pagination.iter_pages>`
 * method (including in default arguments). One deviation is that this function
 * uses 0-indexed page numbers instead of 1-indexed, to ease compatibility with
 * PourOver.
 */
function pageNumbers(num_pages, current_page, options) {
  /* default values */
  if (options === undefined) {
    options = {
      left_edge: 2,
      left_current: 2,
      right_current: 5,
      right_edge: 2
    };
  }
  var pages = [];
  for (var i = 0; i < num_pages; ++i) {
    if (i < options.left_edge){
      pages.push(i);
    } else if ((current_page - options.left_current - 1) < i &&
        i < (current_page + options.right_current)) {
      pages.push(i);
    } else if ((num_pages - options.right_edge - 1) < i) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== null) {
      pages.push(null);
    }
  }
  return pages;
}

/* Add sorts for request attributes */
function addRequestSorts(collection) {
  /* Sort statuses in a specific order */
  var statusSort = PourOver.makeExplicitSort(
    'status_asc',
    collection,
    'status',
    ['evaluating', 'incomplete', 'approved', 'rejected', 'paid']
  );
  var sorts = [ statusSort ];
  /* Create basic sorts for alphabetical attributes */
  var AlphabeticalSort = PourOver.Sort.extend({
    fn: function (a, b) {
      var a_ = a[this['attr']];
      var b_ = b[this['attr']];
      return a_.localeCompare(b_);
    }
  });
  sorts = sorts.concat($.map(
    ['alliance', 'corporation', 'pilot', 'ship', 'division', 'system'],
    function (value) {
      return new AlphabeticalSort(value + '_asc', { attr: value });
    }
  ));
  /* create timestamp sorts */
  var TimestampSort = PourOver.Sort.extend({
    fn: function (a, b) {
      var a_ = a[this['attr']].getTime();
      var b_ = b[this['attr']].getTime();
      if (a_ < b_) {
        return -1;
      } else if (a_ > b_) {
        return 1;
      } else {
        return 0;
      }
    }
  });
  sorts = sorts.concat($.map(
    ['kill_timestamp', 'submit_timestamp'],
    function (value) {
      return new TimestampSort(value + '_asc', { attr: value });
    }
  ));
  /* Numerical Sorts */
  var NumericalSort = PourOver.Sort.extend({
    fn: function (a, b) {
      var a_ = a[this['attr']];
      var b_ = b[this['attr']];
      return a_ - b_;
    }
  });
  sorts = sorts.concat($.map(
    ['payout', 'id'],
    function (value) {
      return new NumericalSort(value + '_asc', { attr: value });
    }
  ));
  /* Reversed Sorts */
  var ReversedSort = PourOver.Sort.extend({
    fn: function(a, b) {
      return -1 * this['base_sort']['fn'](a, b);
    }
  });
  sorts = sorts.concat($.map(
    sorts,
    function (value) {
      name = value['attr'] + '_dsc';
      return new ReversedSort(name, { base_sort: value } );
    }
  ));
  collection.addSorts(sorts);
}

/* Add filters for each request attribute */
function addRequestFilters(collection) {
  $.map(
    ['ships', 'pilots', 'corporations', 'alliances', 'divisions', 'systems'],
    function (filterSource) {
      $.ajax(
        $SCRIPT_ROOT + '/api/filter/' + filterSource + '/',
        {
          dataType: 'json',
          success: function(data, status, jqXHR) {
            var filter = PourOver.makeExactFilter(
              filterSource.slice(0, -1),
              data[filterSource]
            );
            collection.addFilters(filter);
          }
        })
    }
  );
}

if ($('div#request-list').length) {
  /* Event callback for pager links */
  function pager_a_click(ev) {
    /* Set the view to the new page */
    if ($(this).attr('id') === 'prev_page') {
      request_view.page(-1);
    } else if ($(this).attr('id') == 'next_page') {
      request_view.page(1);
    } else {
      var page_num = parseInt($(this).contents()[0].data, 10);
      // zero indexed pages
      page_num = page_num - 1;
      request_view.setPage(page_num);
    }
    /* Fiddle with the browser history to keep the URL in sync */
    var new_path = window.location.pathname.replace(/\/?(?:\d+\/?)?$/, '');
    new_path = new_path + '/' + (request_view.current_page + 1) + '/';
    History.pushState(
      {
        page: request_view.current_page,
        sort: request_view.getSort()
      },
      null,
      new_path
    );
    ev.preventDefault();
  }
  /* PourOver.View extension that renders into a table */
  var RequestsView = PourOver.View.extend({
    page_size: 20,
    render: function () {
      /* Start with a clean slate (keep header separate from data rows) */
      var rows = $('table tr').not($('.popover tr'));
      var rowsParent = rows.parent();
      var headerRow = rows.first();
      var columns = headerRow.find('th').map(function (index, value) {
        return $(value).attr('id').substring(4);
      });
      var oldRows = rows.not(':first');
      if (oldRows.length != 0) {
        oldRows.remove();
      }
      /* Rebuild the table */
      $.each(
        this.getCurrentItems(),
        function (index, request) {
          var row = $('<tr></tr>');
          /* Color the rows based on status */
          if (request['status'] === 'evaluating') {
            row.addClass("warning");
          } else if (request['status'] === 'approved') {
            row.addClass("info");
          } else if (request['status'] === 'paid') {
            row.addClass("success");
          } else if (request['status'] === 'incomplete' || request['status'] === 'rejected') {
            row.addClass("danger");
          }
          $.each(
            columns,
            function (index, key) {
              var content;
              if (key === 'id') {
                content = $('<a></a>', { href: request['href'] }).append(request['id']);
              } else if (key === 'submit_timestamp') {
                var date = request[key];
                content = date.getUTCDate() + ' ' + month(date.getUTCMonth());
                content = content + ' ' + date.getUTCFullYear() + ' @ ';
                content = content + date.getUTCHours() + ':';
                content = content + padNum(date.getUTCMinutes(), 2);
              } else if (key === 'status') {
                content = request[key].substr(0, 1).toUpperCase();
                content = content + request[key].slice(1);
              } else {
                content = request[key];
              }
              $('<td></td>').append(content).appendTo(row);
            }
          );
          row.appendTo(rowsParent);
        }
      );
      /* rebuild the pager */
      var num_pages = Math.ceil(this.match_set.length()/this.page_size - 1) + 1;
      var pager = $('ul.pagination')
      pager.empty();
      if (num_pages === 1) {
        /* don't show the pager when there's only one page */
        pager.attr('style', 'display: none;');
      } else {
        /* prev arrow */
        if (this.current_page === 0) {
          pager.append('<li class="disabled"><span>&laquo;</span></li>');
        } else {
          pager.append('<li><a id="prev_page" href="#">&laquo;</a></li>');
        }
        /* Page numbers */
        var page_nums = pageNumbers(num_pages, this.current_page);
        for (var i = 0; i < page_nums.length; ++i) {
          if (page_nums[i] !== null) {
            if (page_nums[i] !== this.current_page) {
              pager.append('<li><a href="#">' + (page_nums[i] + 1) + '</a></li>');
            } else {
              pager.append('<li class="active"><a href="#">' + (page_nums[i] + 1) + '<span class="sr-only"> (current)</span></a></li>');
            }
          } else {
            pager.append('<li class="disabled"><span>&hellip;</span></li>');
          }
        }
        /* next arrow */
        if (this.current_page === num_pages - 1) {
          pager.append('<li class="disabled"><span>&raquo;</span></li>');
        } else {
          pager.append('<li><a id="next_page" href="#">&raquo;</a></li>');
        }
      }
      pager.find('li > a').click(pager_a_click);
    }
  });
  /* Set up the PourOver.Collection and PourOver.View for requests */
  $.ajax(
    $SCRIPT_ROOT + '/api/filter' + window.location.pathname,
    {
      dataType: 'json',
      success: function(data) {
        var filteredRequests = $.map(data['requests'],
          function (value) {
            value['kill_timestamp'] = new Date(value['kill_timestamp']);
            value['submit_timestamp'] = new Date(value['submit_timestamp']);
            return value;
          });
        requests = new PourOver.Collection(filteredRequests);
        var statusFilter = PourOver.makeExactFilter('status', ['evaluating',
                                                               'approved',
                                                               'rejected',
                                                               'incomplete',
                                                               'paid'])
        requests.addFilters(statusFilter)
        addRequestFilters(requests);
        addRequestSorts(requests);
        request_view = new RequestsView('requests', requests);
        request_view.on('update', request_view.render);
        /* Hijack the pager links */
        $('ul.pagination > li > a').click(pager_a_click);
        /* Watch the history for state changes */
        $(window).on('statechange', function(ev) {
          var state = History.getState();
          if (state.data.page !== request_view.current_page) {
            request_view.setPage(state.data.page);
          }
          if (state.data.sort !== request_view.getSort()) {
            request_view.setSort(state.data.sort);
          }
        });
      }
    }
  );
  /* Attach event listeners to column headers */
  $('th a.heading').click( function (e) {
    var colName = $(this).parent('th').attr('id').substring(4);
    var currentSort = request_view.getSort();
    var newSort = '';
    if (currentSort !== false) {
      if (currentSort.slice(0, -4) === colName) {
        /* swap the direction of the existing sort */
        var direction = currentSort.slice(-3);
        if (direction === 'asc') {
          newSort = colName + '_dsc';
        } else if (direction === 'dsc') {
          newsort = colName + '_asc';
        }
      }
      /* remove the old direction arrow */
      $(this).parent('th').siblings('th').find('i.fa').removeClass();
    }
    if (newSort === '') {
      newSort = colName + '_asc';
    }
    /* Set the direction arrows */
    var direction = newSort.slice(-3);
    if (direction === 'asc') {
      $(this).children('i').attr('class', 'fa fa-chevron-down');
    } else if (direction === 'dsc') {
      $(this).children('i').attr('class', 'fa fa-chevron-up');
    }
    request_view.setSort(newSort);
  });
  /* Make popovers for the filters */
  function renderQueries(filter) {
    /* List the queries on the current filter */
    filter_selection = [];
    if (filter.current_query !== false && filter.current_query !== undefined) {
      var stack = filter.current_query.stack;
      for (var i = 0; i < stack.length; ++i) {
        if (i === 0) {
          filter_selection.push(stack[i][1]);
        } else {
          // Magic path through the arrays for unioned queries
          filter_selection.push(stack[i][1][0][1]);
        }
      }
    }
    var current_table = $('<table class="table table-condensed"></table>');
    for (var i = 0; i < filter_selection.length; ++i) {
      var row = $('<tr></tr>');
      var row_name = $('<td></td>').append(filter_selection[i]);
      var delete_button = $('<button class="close">&times;</button>');
      var row_delete = $('<td></td>').append(delete_button);
      /* Remove this query from the filter */
      delete_button.click(function () {
        var row = $(this).parents('.popover tr');
        var value = row.find('td').contents()[0].data;
        filter.removeSingleQuery(value);
        row.remove();
      });
      row.append(row_name);
      row.append(row_delete);
      current_table.append(row);
    }
    return current_table;
  }
  $('th a.filter').popover({
    placement: 'bottom',
    html: true,
    content: function () {
      var attr = $(this).parent('th').attr('id').substring(4);
      var filter = requests.filters[attr];
      var wrapper = $('<div></div>');
      /* create the search box */
      var input = $('<div class="input-group"></div>');
      input.append('<input type="text" class="form-control">');
      var button_span = $('<span class="input-group-btn"></span>');
      var input_button = $('<button class="btn btn-default"><i class="fa fa-search"></i></button>');
      button_span.append(input_button);
      input.append(button_span);
      /* Add a table after the text box for the current queries */
      var query_table = renderQueries(filter);
      input_button.click(function() {
        var popover = $(this).parents('.popover-content');
        var text_box = popover.find('input');
        var attr = $(this).parents('th').attr('id').substring(4);
        var filter = requests.filters[attr];
        filter.unionQuery(text_box.val());
        var table = renderQueries(filter);
        var old_table = popover.find('table');
        if (old_table.length === 0) {
          popover.append(table);
        } else {
          old_table.replaceWith(table);
        }
      });
      wrapper.append(input);
      wrapper.append(query_table);
      return wrapper;
    }
  }).on('show.bs.popover', function(e) {
    /* hide any other popovers */
    $(this).parent('th').siblings('th').find('a.filter').popover('hide');
    /* set up the buttons and table on the popover */
    var attr = $(this).parents('th').attr('id').substring(4);
    var filter = requests.filters[attr];
    var popover = $(this).find('popover');
    var textbox = $(this).find('input');
    var button = popover.find('button');
  });
}

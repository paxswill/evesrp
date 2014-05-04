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

function pager_a_click(ev) {
  /* Set the view to the new page */
  if ($(this).attr('id') === 'prev_page') {
    requestView.page(-1);
  } else if ($(this).attr('id') == 'next_page') {
    requestView.page(1);
  } else {
    var page_num = parseInt($(this).contents()[0].data, 10);
    // zero indexed pages
    page_num = page_num - 1;
    requestView.setPage(page_num);
  }
  /* Fiddle with the browser history to keep the URL in sync */
  var new_path = window.location.pathname.replace(/\/?(?:\d+\/?)?$/, '');
  new_path = new_path + '/' + (requestView.current_page + 1) + '/';
  History.pushState(
    {
      page: requestView.current_page,
      sort: requestView.getSort()
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
    var rows = $('table tr');
    var rowsParent = rows.parent();
    var headerRow = rows[0];
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
        var idColumn = $('<td></td>');
        idColumn.append(
            $('<a></a>', { href: request['href'] }).append(request['id']));
        idColumn.appendTo(row);
        $.each(
          ['pilot', 'ship', 'system', 'status', 'payout_str',
           'submit_timestamp', 'division'],
          function (index, key) {
            var content;
            if (key === 'submit_timestamp') {
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
      requestView = new RequestsView('requests', requests);
      requestView.on('update', requestView.render);
      /* Hijack the pager links */
      $('ul.pagination > li > a').click(pager_a_click);
      /* Watch the history for state changes */
      $(window).on('statechange', function(ev) {
        var state = History.getState();
        if (state.data.page !== requestView.current_page) {
          requestView.setPage(state.data.page);
        }
        if (state.data.sort !== requestView.getSort()) {
          requestView.setSort(state.data.sort);
        }
      });
    }
  }
);

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

/* Attach event listeners to column headers */
$('th a').click( function (e) {
  var colName = $(this).attr('id').substring(4);
  var currentSort = requestView.getSort();
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
  requestView.setSort(newSort);
});

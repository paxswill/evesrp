/*
 * Filterable lists with PourOver
 */

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

function modifyToken(ev) {
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
}

function addedToken(ev) {
  /* Apply the filter */
  function _add(attr) {
    requests.filters[attr.attr].unionQuery(attr.real_value);
  }
  if (ev.attrs instanceof Array) {
    for (var i = 0; i < ev.attrs.length; ++i) {
      _add(ev.attrs[i]);
    }
  } else {
    _add(ev.attrs);
  }
}

function removedToken(ev) {
  /* Remove the filter */
  function _remove(attr) {
    requests.filters[attr.attr].removeSingleQuery(attr.real_value);
  }
  if (ev.attrs instanceof Array) {
    for (var i = 0; i < ev.attrs.length; ++i) {
      _remove(ev.attrs[i]);
    }
  } else {
    _remove(ev.attrs);
  }
}

function attachTokenfield(bloodhounds) {
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
  $('.filter-tokenfield').tokenfield({
    typeahead: typeahead_args
  })
  .on('tokenfield:createtoken', modifyToken)
  .on('tokenfield:createdtoken', addedToken)
  .on('tokenfield:removetoken', removedToken);
}

/* Add filters for each request attribute */
function addRequestFilters(columns, collection, bloodhound_collection) {
  var supported_columns = [
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
  var filtered_columns;
  if (collection.items.length) {
    filtered_columns = supported_columns.filter(function (val, i){
      return (collection.items[0][val] !== undefined);
    });
  } else {
    filtered_columns = supported_columns;
  }
  var column_checkin = new Object;
  for (var i = 0; i < filtered_columns.length; ++i) {
    column_checkin[filtered_columns[i]] = false;
  }
  /* Create Bloodhound sources for Typeahead */
  function addBloodhound(attribute, values) {
    var source = $.map(values, function(v) {
      return {
        real_value: v,
        attr: attribute
      };
    });
    bloodhound_collection[attribute] = new Bloodhound({
      name: attribute,
      datumTokenizer: function(datum) {
        var tokens = datum.real_value.split(/\s+/);
        tokens.push(datum.attr + ':' + tokens[0]);
        return tokens;
      },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      local: source
    });
    bloodhound_collection[attribute].initialize();
    column_checkin[attribute] = true;
    var all_true = true;
    for (var i = 0; i < filtered_columns.length; ++i) {
      if (!column_checkin[filtered_columns[i]]) {
        all_true = false;
        break;
      }
    }
    if (all_true) {
      attachTokenfield(bloodhound_collection);
    }
  }
  /* Create filters (and Bloodhounds) for each column */
  $.map(
    filtered_columns,
    function (attribute) {
      if (attribute === 'status') {
        var statusFilter = PourOver.makeExactFilter('status', ['evaluating',
                                                               'approved',
                                                               'rejected',
                                                               'incomplete',
                                                               'paid'])
        requests.addFilters(statusFilter)
        addBloodhound(attribute, statusFilter.values);
      } else {
        $.ajax(
          $SCRIPT_ROOT + '/api/filter/' + attribute + '/',
          {
            dataType: 'json',
            success: function(data, status, jqXHR) {
              var filter = PourOver.makeExactFilter(
                attribute,
                data[attribute]
              );
              collection.addFilters(filter);
              addBloodhound(attribute, data[attribute]);
            }
          });
      }
    }
  );
}

function payoutButton(ev){
  var form = $(this).closest('form');
  $.post(
    form.attr('action'),
    {
      id_: form.find('#id_').val(),
      type_: form.find('#type_').val(),
      csrf_token: form.find('#csrf_token').val()
    },
    function() {
      var row = form.parents('tr');
      var item_id = row.find('.col-id').last().text();
      item_id = parseInt(item_id, 10);
      var item = requests.getBy('id', item_id)[0];
      requests.updateItem(item.cid, 'status', 'paid');
      row.find('button').attr('disabled', 'disabled');
    }
  );
  return false;
}

;(function(){
  ZeroClipboard.config({
    moviePath: $SCRIPT_ROOT + '/static/ZeroClipboard.swf'
  })
  /* Attach the pastboard object */
  clipboard_client = new ZeroClipboard($('.copy-btn'));
  /* Initialize tooltips */
  $('.copy-btn').tooltip({trigger: 'manual'});
  /* Add paid button events */
  $('.paid-btn').click(payoutButton);
  clipboard_client.on('mouseover', function (ev) {
    $(this).tooltip('show');
  })
  .on('mouseout', function(ev) {
    $(this).tooltip('hide');
  });
}());

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
  function get_columns(rows) {
    var header_row = rows.first();
    return header_row.find('th').map(function(index, value) {
      return $(value).attr('id').substring(4);
    });
  }
  /* PourOver.View extension that renders into a table */
  var RequestsView = PourOver.View.extend({
    page_size: 20,
    render: function () {
      /* Start with a clean slate (keep header separate from data rows) */
      var rows = $('table#requests tr').not($('.popover tr'));
      var rowsParent = rows.parent();
      var headers = rows.first().find('th');
      var columns = get_columns(rows);
      var oldRows = rows.not(':first');
      var isPayout = false;
      if (oldRows.length != 0) {
        /* Remove the tooltips and unattach the clipboard client from any
         * buttons
         * */
        old_copy_buttons = oldRows.find('.copy-btn');
        if (old_copy_buttons.length != 0) {
          isPayout = true;
          clipboard_client.unclip(old_copy_buttons);
          old_copy_buttons.each(function (i, element) {
            $(element).tooltip('destroy');
          });
        }
        oldRows.remove();
      }
      /* Rebuild the table */
      var newRows;
      if (isPayout) {
        newRows = $(Handlebars.templates.payout_rows(this.getCurrentItems()));
        var $copyButtons = newRows.find('.copy-btn');
        clipboard_client.clip($copyButtons);
        $copyButtons.tooltip({trigger: 'manual focus'});
      } else {
        newRows = Handlebars.templates.request_rows(this.getCurrentItems());
      }
      rowsParent.append(newRows);
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
            /* Convert the dates into JS Dates */
            value['kill_timestamp'] = new Date(value['kill_timestamp']);
            value['submit_timestamp'] = new Date(value['submit_timestamp']);
            return value;
          });
        requests = new PourOver.Collection(filteredRequests);
        column_bloodhounds = new Object;
        /* Create filters and sorts for columns */
        addRequestFilters(
          get_columns($('table#requests tr')),
          requests,
          column_bloodhounds
        );
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
}

$('#apikeys').submit(function(e) {
  var $form = $(e.target),
      $table = $(this);
  $.post(
    window.location.pathname,
    $form.serialize(),
    function(data) {
      // Update table
      var $rows = $table.find('tr').slice(1, -1),
          $lastRow = $table.find('tr').slice(-1),
          $newRows = $(Handlebars.templates.api_keys(data)),
          $copyButtons = $newRows.find('.copy-btn');
      clipboard_client.clip($copyButtons);
      $copyButtons.tooltip({
        placement: 'bottom',
        title: 'Copy to clipboard',
        trigger: 'manual focus'
      });
      $rows.remove();
      $lastRow.before($newRows);
    }
  );
  return false;
})

var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

EveSRP.pourover = {

  addRequestSorts: function addRequestSorts(collection) {
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
    return collection;
  },

  changePage: function changePage(ev) {
    var requestView = ev.data.requestView,
        newPath, pageNum;
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
    newPath = window.location.pathname.replace(/\/?(?:\d+\/?)?$/, '');
    newPath = newPath + '/' + (requestView.current_page + 1) + '/';
    History.pushState( {
        page: requestView.current_page,
        sort: requestView.getSort()
      }, null, newPath);
    return false;
  },

  BufferedFilter: PourOver.manualFilter.extend( {
    _getFn: this.getFn,

    processQuery: function processQuery(query) {
      var _this = this;
      if (! ('cachedQueries' in this)) {
        this.cachedQueries = {};
      }
      if (query in this.cachedQueries) {
        this.addItems(this.cachedQueries[query]);
      } else {
        $.ajax( {
          async: false,
          type: 'GET',
          url: $SCRIPT_ROOT + '/api/filter/' + this.attr + '/' + query,
          success: function(data) {
            var ids = data.ids,
                items = _this.getCollection().getBy('id', ids),
                cids = _(items).map(function(i) {return i.cid});
            _this.cachedQueries[query] = cids;
          }
        });
      }
    },

    getFn: function(query) {
      var cids;
      if (! ('cachedQueries' in this)) {
        this.cachedQueries = {};
      }
      if (query in this.cachedQueries) {
        cids = this.cachedQueries[query];
      } else {
        this.processQuery(query);
        cids = this.cachedQueries[query];
      }
      return this.makeQueryMatchSet(cids, query);
    }
  }),

  makeBufferedFilter: function makeBufferedFilter(name) {
    return new EveSRP.pourover.BufferedFilter(name, [], {attr: name});
  },

  RequestsView: PourOver.View.extend( {
    page_size: 20,
    render: function () {
      /* Start with a clean slate (keep header separate from data rows) */
      var $rows = $('table#requests tr').not($('.popover tr')),
          $rowsParent = $rows.parent(),
          $headers = $rows.first().find('th'),
          $oldRows = $rows.not(':first'),
          columns = EveSRP.ui.requestList.getColumns($rows),
          isPayout = false,
          $copyButtons, $newRows, $pager, numPages, pageNums;
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
        $newRows = $(Handlebars.templates.payout_rows(this.getCurrentItems()));
        $copyButtons = $newRows.find('.copy-btn');
        EveSRP.ui.clipboardClient.clip($copyButtons);
        $copyButtons.tooltip({trigger: 'manual focus'});
      } else {
        $newRows = Handlebars.templates.request_rows(this.getCurrentItems());
      }
      $rowsParent.append($newRows);
      /* rebuild the pager */
      numPages = Math.ceil(this.match_set.length()/this.page_size - 1) + 1;
      $pager = $('ul.pagination')
      $pager.empty();
      if (numPages === 1) {
        /* don't show the pager when there's only one page */
        $pager.attr('style', 'display: none;');
      } else {
        /* prev arrow */
        if (this.current_page === 0) {
          $pager.append('<li class="disabled"><span>&laquo;</span></li>');
        } else {
          $pager.append('<li><a id="prev_page" href="#">&laquo;</a></li>');
        }
        /* Page numbers */
        pageNums = EveSRP.util.pageNumbers(numPages, this.current_page);
        for (var i = 0; i < pageNums.length; ++i) {
          if (pageNums[i] !== null) {
            if (pageNums[i] !== this.current_page) {
              $pager.append('<li><a href="#">' + (pageNums[i] + 1) + '</a></li>');
            } else {
              $pager.append('<li class="active"><a href="#">' + (pageNums[i] + 1) + '<span class="sr-only"> (current)</span></a></li>');
            }
          } else {
            $pager.append('<li class="disabled"><span>&hellip;</span></li>');
          }
        }
        /* next arrow */
        if (this.current_page === numPages - 1) {
          $pager.append('<li class="disabled"><span>&raquo;</span></li>');
        } else {
          $pager.append('<li><a id="next_page" href="#">&raquo;</a></li>');
        }
      }
      $pager.find('li > a').on('click', {requestView: this},
          EveSRP.pourover.changePage);
    }
  }),
}

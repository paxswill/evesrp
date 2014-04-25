/*
 * Filterable lists with PourOver
 */
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

function padNum (num, width) {
  /* coerce to a string */
  num = num + '';
  while (num.length < width) {
    num = 0 + num;
  }
  return num;
}

var RequestsView = PourOver.View.extend({
  page_size: 15,
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
        if (request['status'] == 'evaluating') {
          row.addClass("warning");
        } else if (request['status'] == 'approved') {
          row.addClass("info");
        } else if (request['status'] == 'paid') {
          row.addClass("success");
        } else if (request['status'] == 'incomplete' || request['status'] == 'rejected') {
          row.addClass("danger");
        }
        var idColumn = $('<td></td>');
        idColumn.append(
            $('<a></a>', { href: request['href'] }).append(request['id']));
        idColumn.appendTo(row);
        $.each(
          ['pilot', 'ship', 'status', 'payout_str', 'submit_timestamp',
           'division'],
          function (index, key) {
            var content;
            if (key == 'submit_timestamp') {
              var date = request[key];
              content = date.getUTCDate() + ' ' + month(date.getUTCMonth());
              content = content + ' ' + date.getUTCFullYear() + ' @ ';
              content = content + date.getUTCHours() + ':';
              content = content + padNum(date.getUTCMinutes(), 2);
            } else if (key == 'status') {
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
  }
});

$.ajax(
  $SCRIPT_ROOT + '/api/filter/requests/',
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
      getFilters();
      requestView = new RequestsView('requests', requests);
      requestView.on('update', requestView.render);
    }
  }
);

function getFilters() {
  $.map(
    ['ships', 'pilots', 'corporations', 'alliances', 'divisions'],
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
            requests.addFilters(filter);
          }
        })
    }
  );
}

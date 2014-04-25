/*
 * Filterable lists with PourOver
 */

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
            $('<td>' + request[key] + '</td>').appendTo(row);
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
      requestsCollection = new PourOver.Collection(data['requests']);
      var statusFilter = PourOver.makeExactFilter('status', ['evaluating',
                                                             'approved',
                                                             'rejected',
                                                             'incomplete',
                                                             'paid'])
      requestsCollection.addFilters(statusFilter)
      getFilters();
      requestView = new RequestsView('requests', requestsCollection);
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
            requestsCollection.addFilters(filter);
          }
        })
    }
  );
}

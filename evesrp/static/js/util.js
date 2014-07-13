var EveSRP;

if (!EveSRP) {
  EveSRP = {}
}

EveSRP.util = {

  capitalize: function capitalize(str) {
    var content = str.substr(0, 1).toUpperCase();
    content = content + str.slice(1);
    return content;
  },

  // Map month integers to month abbreviations
  monthAbbr: function month(month_int) {
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
  },

  // Pad num to width with 0s
  padNum: function padNum (num, width) {
    /* coerce to a string */
    num = num + '';
    while (num.length < width) {
      num = 0 + num;
    }
    return num;
  },

  statusColor: function statusColor(statusString) {
    switch (statusString) {
      case 'evaluating':
        return 'warning';
      case 'approved':
        return 'info';
      case 'paid':
        return 'success';
      case 'incomplete':
      case 'rejected':
        return 'danger';
      default:
        return '';
    }
  },

  pageNumbers: function pageNumbers(num_pages, current_page, options) {
    /* return an array of page numbers, skipping some of them as configured by
     * the options argument. This function should be functionally identical to
     * Flask-SQLAlchemy's
     * :py:method:`Pagination.iter_pages <flask.ext.sqlalchemy.Pagination.iter_pages>`
     * method (including in default arguments). One deviation is that this
     * function uses 0-indexed page numbers instead of 1-indexed, to ease
     * compatibility with PourOver.
     */
    // default values
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
  },

  getAttributeChoices: function getAttributeChoices(attribute) {
    if (attribute === 'status') {
      var statuses = ['evaluating', 'approved', 'rejected', 'incomplete',
        'paid'];
      return $.Deferred().resolve( {
        key: 'status',
        'status': statuses
      });
    }
    if (attribute === 'details') {
      return $.Deferred().resolve( {
        key: 'details',
        'details': null
      });
    }
    return $.ajax( {
      type: 'GET',
      url: $SCRIPT_ROOT + '/api/filter/' + attribute + '/'
    });
  }
};

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
  },

  trimEmpty: function trimEmpty(arr) {
    var newArr = arr.slice(0);
    if (newArr[0] === '') {
      newArr = newArr.slice(1);
    }
    if (newArr.slice(-1)[0] === '') {
      newArr = newArr.slice(0, -1);
    }
    return newArr;
  },

  splitFilterString: function splitFilterString(pathname) {
    var filterPath = pathname.split('/'),
        known_attrs = ['page', 'division', 'alliance', 'corporation', 'pilot',
                       'system', 'constellation', 'region', 'ship', 'status',
                       'details', 'sort'],
        basePath = [];
    filterPath = this.trimEmpty(filterPath);
    filterPath.reverse();
    while (filterPath.length > 0 &&
        $.inArray(filterPath.slice(-1)[0], known_attrs) === -1) {
      basePath.push(filterPath.pop());
    }
    filterPath.reverse();
    return [basePath.join('/'), filterPath.join('/')]
  },

  parseFilterString: function parseFilterString(filterString) {
    /* This is a straight port of the
     * evesrp.views.requests.RequestListing.parseFilterString function from
     * Python to Javascript.
     */
    var filters = {},
        splitString, i, attr, values;
    _.defaults(filters, {page: 1, sort: '-submit_timestamp'});
    // Fail early for empty filters
    if (filterString === undefined || filterString === '') {
      return filters;
    }
    splitString = filterString.split('/');
    // Trim empty beginnings and/or ends
    splitString = this.trimEmpty(splitString);
    // Check for unpaired filters
    if (splitString.length % 2 !== 0) {
      return filters;
    }
    for (i = 0; i < splitString.length; i += 2) {
      attr = splitString[i].toLowerCase();
      values = decodeURIComponent(splitString[i + 1]);
      if (! (attr in filters)) {
        filters[attr] = [];
      }
      if (attr === 'details') {
        filters.details = _(filters[attr]).union(values);
      } else if (attr === 'page') {
        filters.page = parseInt(values, 10);
      } else if (attr === 'sort') {
        filters.sort = values;
      } else if (values.indexOf(',') !== -1) {
        values = values.split(',');
        filters[attr] = _(filters[attr]).union(values);
      } else {
        filters[attr] = _(filters[attr]).union([values]);
      }
    }
    return filters;
  },

  unparseFilters: function unparseFilters(filters) {
    /* Like parseFilterString, this is a straight port of the
     * evesrp.views.requests.RequestListing.unparseFilters function from
     * Python to Javascript.
     */
    var filterStrings = [], keys;
    keys = Object.keys(filters);
    keys.sort()
    $.each(keys, function(index, attr) {
      var values = filters[attr];
      if (attr === 'details') {
        $.each(values, function(i, details) {
          filterStrings.push('details/' + details);
        });
      } else if (attr === 'page') {
        if (values !== 1) {
          filterStrings.push('page/' + values);
        }
      } else if (attr === 'sort') {
        if (values !== '-submit_timestamp') {
          filterStrings.push('sort/' + values);
        }
      } else if (values.length > 0) {
        values.sort();
        filterStrings.push(attr + '/' + values.join(','));
      }
    });
    return filterStrings.join('/');
  },

  keyDifference: function keyDifference(obj1, obj2) {
    var allKeys = _.union(_.keys(obj1), _.keys(obj2)),
        results = [],
        i, key;
    for (i = 0; i < allKeys.length; i++) {
      key = allKeys[i];
      // Skip old '_keys' properties that might be lingering around
      if (key === '_keys') {
        continue;
      }
      // Prune empty properties
      if (key !== 'page') {
        if (key in obj1 && _.isEmpty(obj1[key])) {
          delete obj1[key];
          if (! (key in obj2)) {
            allKeys.splice(i--, 1);
          }
        }
        if (key in obj2 && _.isEmpty(obj2[key])) {
          delete obj2[key];
          if (! (key in obj1)) {
            allKeys.splice(i--, 1);
          }
        }
      }
      // Actual checking
      if (! (key in obj1) || ! (key in obj2)) {
        results.push(key);
      } else if (! _.isEqual(obj1[key], obj2[key])) {
        results.push(key)
      }
    };
    return results;
  }
};

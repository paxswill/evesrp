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
};

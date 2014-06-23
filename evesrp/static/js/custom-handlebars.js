Handlebars.registerHelper('csrf', function() {
  return $("meta[name='csrf_token']").attr("content");
});

function capitalize(str) {
  var content = str.substr(0, 1).toUpperCase();
  content = content + str.slice(1);
  return content;
}

Handlebars.registerHelper('capitalize', function(str) {
  return capitalize(str);
});

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

Handlebars.registerHelper('timefmt', function(date) {
  if (typeof date === 'string') {
    date = new Date(date);
  }
  return date.getUTCDate() + ' ' + month(date.getUTCMonth()) +
    ' ' + date.getUTCFullYear();
});

Handlebars.registerHelper('datefmt', function(date) {
  if (typeof date === 'string') {
    date = new Date(date);
  }
  return date.getUTCHours() + ':' + padNum(date.getUTCMinutes(), 2);
});

function statusColor(statusString) {
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
}

Handlebars.registerHelper('status_color', function(stat) {
  return statusColor(stat);
});

Handlebars.registerHelper('compare', function(left, right, options) {
  var op = options.hash.operator || "===";
  var ops = {
    '==': function(l, r) { return l == r;},
    '!=': function(l, r) { return l != r;},
    '===': function(l, r) { return l === r;},
    '!==': function(l, r) { return l !== r;},
    '<': function(l, r) { return l < r;},
    '>': function(l, r) { return l > r;},
    '<=': function(l, r) { return l <= r;},
    '>=': function(l, r) { return l >= r;},
    'in': function(l, r) { return l in r;}
  };
  var result = ops[op](left, right);
  if (result) {
    return options.fn(this);
  } else {
    return options.inverse(this);
  }
});


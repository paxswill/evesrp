Handlebars.registerHelper('csrf', function() {
  return $("meta[name='csrf_token']").attr("content");
});

Handlebars.registerHelper('capitalize', function(str) {
  var content = str.substr(0, 1).toUpperCase();
  content = content + str.slice(1);
  return content;
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
  var content = date.getUTCDate() + ' ' + month(date.getUTCMonth());
  content = content + ' ' + date.getUTCFullYear() + ' @ ';
  content = content + date.getUTCHours() + ':';
  content = content + padNum(date.getUTCMinutes(), 2);
  return content;
});

Handlebars.registerHelper('status_color', function(stat) {
    if (stat === 'evaluating') {
      return "warning";
    } else if (stat === 'approved') {
      return "info";
    } else if (stat === 'paid') {
      return "success";
    } else if (stat === 'incomplete' || stat === 'rejected') {
      return "danger";
    }
});

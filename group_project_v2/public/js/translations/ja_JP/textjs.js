
            (function(global){
                var GroupProjectV2XBlockI18N = {
                  init: function() {
                    

(function(globals) {

  var django = globals.django || (globals.django = {});

  
  django.pluralidx = function(count) { return (count == 1) ? 0 : 1; };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  var newcatalog = {
    " Technical details: 403 error.": "\u6280\u8853\u7684\u306a\u8a73\u7d30\uff1a403\u30a8\u30e9\u30fc\u3002", 
    " Technical details: CSRF verification failed.": "\u6280\u8853\u7684\u306a\u8a73\u7d30\uff1aCSRF\u691c\u8a3c\u306b\u5931\u6557\u3057\u307e\u3057\u305f\u3002", 
    " on ": " \u30aa\u30f3 ", 
    "An error occurred while uploading your file. Please refresh the page and try again. If it still does not upload, please contact your Course TA.": "\u30d5\u30a1\u30a4\u30eb\u306e\u30a2\u30c3\u30d7\u30ed\u30fc\u30c9\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f\u3002\u30da\u30fc\u30b8\u3092\u66f4\u65b0\u3057\u3066\u518d\u5ea6\u304a\u8a66\u3057\u304f\u3060\u3055\u3044\u3002\u518d\u8a66\u884c\u3057\u3066\u3082\u30a2\u30c3\u30d7\u30ed\u30fc\u30c9\u3067\u304d\u306a\u3044\u5834\u5408\u306f\u3001\u30b3\u30fc\u30b9TA\u306b\u304a\u554f\u3044\u5408\u308f\u305b\u304f\u3060\u3055\u3044\u3002", 
    "Error": "\u30a8\u30e9\u30fc", 
    "Error refreshing statuses": "\u30a8\u30e9\u30fc\u66f4\u65b0\u30b9\u30c6\u30fc\u30bf\u30b9", 
    "Notification": "\u901a\u77e5", 
    "Please select Group to review": "\u78ba\u8a8d\u3059\u308b\u30b0\u30eb\u30fc\u30d7\u3092\u9078\u629e\u3057\u3066\u304f\u3060\u3055\u3044\u3002", 
    "Please select Teammate to review": "\u78ba\u8a8d\u3059\u308b\u30c1\u30fc\u30e0\u30e1\u30f3\u30d0\u30fc\u3092\u9078\u629e\u3057\u3066\u304f\u3060\u3055\u3044", 
    "Resubmit": "\u518d\u63d0\u51fa", 
    "Submit": "\u9001\u4fe1\u3059\u308b", 
    "Thanks for your feedback!": "\u30d5\u30a3\u30fc\u30c9\u30d0\u30c3\u30af\u3092\u9001\u4fe1\u3044\u305f\u3060\u304d\u3042\u308a\u304c\u3068\u3046\u3054\u3056\u3044\u307e\u3059\u3002", 
    "This task has been marked as complete.": "\u3053\u306e\u30bf\u30b9\u30af\u306f\u5b8c\u4e86\u6e08\u3068\u3057\u3066\u30de\u30fc\u30af\u3055\u308c\u307e\u3057\u305f\u3002", 
    "Upload cancelled by user.": "\u30e6\u30fc\u30b6\u30fc\u306b\u3088\u3063\u3066\u30a2\u30c3\u30d7\u30ed\u30fc\u30c9\u304c\u30ad\u30e3\u30f3\u30bb\u30eb\u3055\u308c\u307e\u3057\u305f\u3002", 
    "Upload cancelled.": "\u30a2\u30c3\u30d7\u30ed\u30fc\u30c9\u304c\u30ad\u30e3\u30f3\u30bb\u30eb\u3055\u308c\u307e\u3057\u305f\u3002", 
    "Uploaded by ": "\u30a2\u30c3\u30d7\u30ed\u30fc\u30c9\u8005: ", 
    "We encountered an error loading your feedback.": "\u30d5\u30a3\u30fc\u30c9\u30d0\u30c3\u30af\u306e\u8aad\u307f\u8fbc\u307f\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f\u3002", 
    "We encountered an error saving your feedback.": "\u30d5\u30a3\u30fc\u30c9\u30d0\u30c3\u30af\u306e\u4fdd\u5b58\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f\u3002", 
    "We encountered an error saving your progress.": "\u9032\u5ea6\u306e\u4fdd\u5b58\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f\u3002", 
    "We encountered an error.": "\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f\u3002"
  };
  for (var key in newcatalog) {
    django.catalog[key] = newcatalog[key];
  }
  

  if (!django.jsi18n_initialized) {
    django.gettext = function(msgid) {
      var value = django.catalog[msgid];
      if (typeof(value) == 'undefined') {
        return msgid;
      } else {
        return (typeof(value) == 'string') ? value : value[0];
      }
    };

    django.ngettext = function(singular, plural, count) {
      var value = django.catalog[singular];
      if (typeof(value) == 'undefined') {
        return (count == 1) ? singular : plural;
      } else {
        return value[django.pluralidx(count)];
      }
    };

    django.gettext_noop = function(msgid) { return msgid; };

    django.pgettext = function(context, msgid) {
      var value = django.gettext(context + '\x04' + msgid);
      if (value.indexOf('\x04') != -1) {
        value = msgid;
      }
      return value;
    };

    django.npgettext = function(context, singular, plural, count) {
      var value = django.ngettext(context + '\x04' + singular, context + '\x04' + plural, count);
      if (value.indexOf('\x04') != -1) {
        value = django.ngettext(singular, plural, count);
      }
      return value;
    };

    django.interpolate = function(fmt, obj, named) {
      if (named) {
        return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
      } else {
        return fmt.replace(/%s/g, function(match){return String(obj.shift())});
      }
    };


    /* formatting library */

    django.formats = {
    "DATETIME_FORMAT": "Y\u5e74n\u6708j\u65e5G:i", 
    "DATETIME_INPUT_FORMATS": [
      "%Y-%m-%d %H:%M:%S", 
      "%Y-%m-%d %H:%M:%S.%f", 
      "%Y-%m-%d %H:%M", 
      "%Y-%m-%d", 
      "%m/%d/%Y %H:%M:%S", 
      "%m/%d/%Y %H:%M:%S.%f", 
      "%m/%d/%Y %H:%M", 
      "%m/%d/%Y", 
      "%m/%d/%y %H:%M:%S", 
      "%m/%d/%y %H:%M:%S.%f", 
      "%m/%d/%y %H:%M", 
      "%m/%d/%y"
    ], 
    "DATE_FORMAT": "Y\u5e74n\u6708j\u65e5", 
    "DATE_INPUT_FORMATS": [
      "%Y-%m-%d", 
      "%m/%d/%Y", 
      "%m/%d/%y", 
      "%b %d %Y", 
      "%b %d, %Y", 
      "%d %b %Y", 
      "%d %b, %Y", 
      "%B %d %Y", 
      "%B %d, %Y", 
      "%d %B %Y", 
      "%d %B, %Y"
    ], 
    "DECIMAL_SEPARATOR": ".", 
    "FIRST_DAY_OF_WEEK": "0", 
    "MONTH_DAY_FORMAT": "n\u6708j\u65e5", 
    "NUMBER_GROUPING": "0", 
    "SHORT_DATETIME_FORMAT": "Y/m/d G:i", 
    "SHORT_DATE_FORMAT": "Y/m/d", 
    "THOUSAND_SEPARATOR": ",", 
    "TIME_FORMAT": "G:i", 
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S", 
      "%H:%M:%S.%f", 
      "%H:%M"
    ], 
    "YEAR_MONTH_FORMAT": "Y\u5e74n\u6708"
  };

    django.get_format = function(format_type) {
      var value = django.formats[format_type];
      if (typeof(value) == 'undefined') {
        return format_type;
      } else {
        return value;
      }
    };

    /* add to global namespace */
    globals.pluralidx = django.pluralidx;
    globals.gettext = django.gettext;
    globals.ngettext = django.ngettext;
    globals.gettext_noop = django.gettext_noop;
    globals.pgettext = django.pgettext;
    globals.npgettext = django.npgettext;
    globals.interpolate = django.interpolate;
    globals.get_format = django.get_format;

    django.jsi18n_initialized = true;
  }

}(this));


                  }
                };
                GroupProjectV2XBlockI18N.init();
                global.GroupProjectV2XBlockI18N = GroupProjectV2XBlockI18N;
            }(this));
        

            (function(global){
                var GroupProjectV2XBlockI18N = {
                  init: function() {
                    

(function(globals) {

  var django = globals.django || (globals.django = {});

  
  django.pluralidx = function(n) {
    var v=(n != 1);
    if (typeof(v) == 'boolean') {
      return v ? 1 : 0;
    } else {
      return v;
    }
  };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  var newcatalog = {
    " Technical details: 403 error.": " T\u00e9\u00e7hn\u00ef\u00e7\u00e4l d\u00e9t\u00e4\u00efls: 403 \u00e9rr\u00f6r. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455\u0454\u00a2\u0442#", 
    " Technical details: CSRF verification failed.": " T\u00e9\u00e7hn\u00ef\u00e7\u00e4l d\u00e9t\u00e4\u00efls: \u00c7SRF v\u00e9r\u00eff\u00ef\u00e7\u00e4t\u00ef\u00f6n f\u00e4\u00efl\u00e9d. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455\u0454\u00a2\u0442\u0454\u0442\u03c5\u044f #", 
    "An error occurred while uploading your file. Please refresh the page and try again. If it still does not upload, please contact your Course TA.": "\u00c0n \u00e9rr\u00f6r \u00f6\u00e7\u00e7\u00fcrr\u00e9d wh\u00efl\u00e9 \u00fcpl\u00f6\u00e4d\u00efng \u00fd\u00f6\u00fcr f\u00efl\u00e9. Pl\u00e9\u00e4s\u00e9 r\u00e9fr\u00e9sh th\u00e9 p\u00e4g\u00e9 \u00e4nd tr\u00fd \u00e4g\u00e4\u00efn. \u00ccf \u00eft st\u00efll d\u00f6\u00e9s n\u00f6t \u00fcpl\u00f6\u00e4d, pl\u00e9\u00e4s\u00e9 \u00e7\u00f6nt\u00e4\u00e7t \u00fd\u00f6\u00fcr \u00c7\u00f6\u00fcrs\u00e9 T\u00c0. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455\u0454\u00a2\u0442\u0454\u0442\u03c5\u044f \u03b1\u2202\u03b9\u03c1\u03b9\u0455\u03b9\u00a2\u03b9\u03b7g \u0454\u0142\u03b9\u0442, \u0455\u0454\u2202 \u2202\u03c3 \u0454\u03b9\u03c5\u0455\u043c\u03c3\u2202 \u0442\u0454\u043c\u03c1\u03c3\u044f \u03b9\u03b7\u00a2\u03b9\u2202\u03b9\u2202\u03c5\u03b7\u0442 \u03c5\u0442 \u0142\u03b1\u0432\u03c3\u044f\u0454 \u0454\u0442 \u2202\u03c3\u0142\u03c3\u044f\u0454 \u043c\u03b1g\u03b7\u03b1 \u03b1\u0142\u03b9q\u03c5\u03b1. \u03c5\u0442 \u0454\u03b7\u03b9\u043c \u03b1\u2202 \u043c\u03b9\u03b7\u03b9\u043c \u03bd\u0454\u03b7\u03b9\u03b1\u043c, q\u03c5\u03b9\u0455 \u03b7\u03c3\u0455\u0442\u044f\u03c5\u2202 \u0454\u03c7\u0454\u044f\u00a2\u03b9\u0442\u03b1\u0442\u03b9\u03c3\u03b7 \u03c5\u0142\u0142\u03b1\u043c\u00a2\u03c3 \u0142\u03b1\u0432\u03c3\u044f\u03b9\u0455 \u03b7\u03b9\u0455\u03b9 \u03c5\u0442 \u03b1\u0142\u03b9q\u03c5\u03b9\u03c1 \u0454\u03c7 \u0454\u03b1 \u00a2\u03c3\u043c\u043c\u03c3\u2202\u03c3 \u00a2\u03c3\u03b7\u0455\u0454q\u03c5\u03b1\u0442. \u2202\u03c5\u03b9\u0455 \u03b1\u03c5\u0442\u0454 \u03b9\u044f\u03c5\u044f\u0454 \u2202\u03c3\u0142\u03c3\u044f \u03b9\u03b7 \u044f\u0454\u03c1\u044f\u0454\u043d\u0454\u03b7\u2202\u0454\u044f\u03b9\u0442 \u03b9\u03b7 \u03bd\u03c3\u0142\u03c5\u03c1\u0442\u03b1\u0442\u0454 \u03bd\u0454\u0142\u03b9\u0442 \u0454\u0455\u0455\u0454 \u00a2\u03b9\u0142\u0142\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f\u0454 \u0454\u03c5 \u0192\u03c5g\u03b9\u03b1\u0442 \u03b7\u03c5\u0142\u0142\u03b1 \u03c1\u03b1\u044f\u03b9\u03b1\u0442\u03c5\u044f. \u0454\u03c7\u00a2\u0454\u03c1\u0442\u0454\u03c5\u044f \u0455\u03b9\u03b7\u0442 \u03c3\u00a2\u00a2\u03b1\u0454\u00a2\u03b1\u0442 \u00a2\u03c5\u03c1\u03b9\u2202\u03b1\u0442\u03b1\u0442 \u03b7\u03c3\u03b7 \u03c1\u044f\u03c3\u03b9\u2202\u0454\u03b7\u0442, \u0455\u03c5\u03b7\u0442 \u03b9\u03b7 \u00a2\u03c5\u0142\u03c1\u03b1 q\u03c5\u03b9 \u03c3\u0192\u0192\u03b9\u00a2\u03b9\u03b1 \u2202\u0454\u0455\u0454\u044f\u03c5\u03b7\u0442 \u043c\u03c3\u0142\u0142\u03b9\u0442 \u03b1\u03b7\u03b9\u043c \u03b9\u2202 \u0454\u0455#", 
    "Error": "\u00c9rr\u00f6r \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455#", 
    "Error refreshing statuses": "\u00c9rr\u00f6r r\u00e9fr\u00e9sh\u00efng st\u00e4t\u00fcs\u00e9s \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455#", 
    "Please select Group to review": "Pl\u00e9\u00e4s\u00e9 s\u00e9l\u00e9\u00e7t Gr\u00f6\u00fcp t\u00f6 r\u00e9v\u00ef\u00e9w \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455\u0454\u00a2#", 
    "Please select Teammate to review": "Pl\u00e9\u00e4s\u00e9 s\u00e9l\u00e9\u00e7t T\u00e9\u00e4mm\u00e4t\u00e9 t\u00f6 r\u00e9v\u00ef\u00e9w \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455\u0454\u00a2\u0442\u0454#", 
    "Resubmit": "R\u00e9s\u00fc\u00dfm\u00eft \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202#", 
    "Submit": "S\u00fc\u00dfm\u00eft \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5#", 
    "Thanks for your feedback!": "Th\u00e4nks f\u00f6r \u00fd\u00f6\u00fcr f\u00e9\u00e9d\u00df\u00e4\u00e7k! \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455#", 
    "This task has been marked as complete.": "Th\u00efs t\u00e4sk h\u00e4s \u00df\u00e9\u00e9n m\u00e4rk\u00e9d \u00e4s \u00e7\u00f6mpl\u00e9t\u00e9. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455\u0454\u00a2\u0442\u0454\u0442\u03c5\u044f#", 
    "Upload cancelled by user.": "\u00dbpl\u00f6\u00e4d \u00e7\u00e4n\u00e7\u00e9ll\u00e9d \u00df\u00fd \u00fcs\u00e9r. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455#", 
    "Upload cancelled.": "\u00dbpl\u00f6\u00e4d \u00e7\u00e4n\u00e7\u00e9ll\u00e9d. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454#", 
    "We encountered an error loading your feedback.": "W\u00e9 \u00e9n\u00e7\u00f6\u00fcnt\u00e9r\u00e9d \u00e4n \u00e9rr\u00f6r l\u00f6\u00e4d\u00efng \u00fd\u00f6\u00fcr f\u00e9\u00e9d\u00df\u00e4\u00e7k. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455\u0454\u00a2\u0442\u0454\u0442\u03c5\u044f \u03b1#", 
    "We encountered an error saving your feedback.": "W\u00e9 \u00e9n\u00e7\u00f6\u00fcnt\u00e9r\u00e9d \u00e4n \u00e9rr\u00f6r s\u00e4v\u00efng \u00fd\u00f6\u00fcr f\u00e9\u00e9d\u00df\u00e4\u00e7k. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455\u0454\u00a2\u0442\u0454\u0442\u03c5\u044f #", 
    "We encountered an error saving your progress.": "W\u00e9 \u00e9n\u00e7\u00f6\u00fcnt\u00e9r\u00e9d \u00e4n \u00e9rr\u00f6r s\u00e4v\u00efng \u00fd\u00f6\u00fcr pr\u00f6gr\u00e9ss. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7\u0455\u0454\u00a2\u0442\u0454\u0442\u03c5\u044f #", 
    "We encountered an error.": "W\u00e9 \u00e9n\u00e7\u00f6\u00fcnt\u00e9r\u00e9d \u00e4n \u00e9rr\u00f6r. \u2c60'\u03c3\u044f\u0454\u043c \u03b9\u03c1\u0455\u03c5\u043c \u2202\u03c3\u0142\u03c3\u044f \u0455\u03b9\u0442 \u03b1\u043c\u0454\u0442, \u00a2\u03c3\u03b7#"
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
    "DATETIME_FORMAT": "j\\-\\a \\d\\e F Y\\, \\j\\e H:i", 
    "DATETIME_INPUT_FORMATS": [
      "%Y-%m-%d %H:%M:%S", 
      "%Y-%m-%d %H:%M", 
      "%Y-%m-%d", 
      "%Y.%m.%d %H:%M:%S", 
      "%Y.%m.%d %H:%M", 
      "%Y.%m.%d", 
      "%d/%m/%Y %H:%M:%S", 
      "%d/%m/%Y %H:%M", 
      "%d/%m/%Y", 
      "%y-%m-%d %H:%M:%S", 
      "%y-%m-%d %H:%M", 
      "%y-%m-%d", 
      "%Y-%m-%d %H:%M:%S.%f"
    ], 
    "DATE_FORMAT": "j\\-\\a \\d\\e F Y", 
    "DATE_INPUT_FORMATS": [
      "%Y-%m-%d", 
      "%y-%m-%d", 
      "%Y %m %d", 
      "%d-a de %b %Y", 
      "%d %b %Y", 
      "%d-a de %B %Y", 
      "%d %B %Y", 
      "%d %m %Y"
    ], 
    "DECIMAL_SEPARATOR": ",", 
    "FIRST_DAY_OF_WEEK": "1", 
    "MONTH_DAY_FORMAT": "j\\-\\a \\d\\e F", 
    "NUMBER_GROUPING": "3", 
    "SHORT_DATETIME_FORMAT": "Y-m-d H:i", 
    "SHORT_DATE_FORMAT": "Y-m-d", 
    "THOUSAND_SEPARATOR": "\u00a0", 
    "TIME_FORMAT": "H:i", 
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S", 
      "%H:%M", 
      "%H:%M:%S.%f"
    ], 
    "YEAR_MONTH_FORMAT": "F \\d\\e Y"
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
        
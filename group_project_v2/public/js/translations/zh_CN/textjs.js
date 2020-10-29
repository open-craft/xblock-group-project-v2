
            (function(global){
                var GroupProjectV2XBlockI18N = {
                  init: function() {
                    

(function(globals) {

  var django = globals.django || (globals.django = {});

  
  django.pluralidx = function(count) { return (count == 1) ? 0 : 1; };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  var newcatalog = {
    " Technical details: 403 error.": " \u6280\u672f\u8be6\u7ec6\u4fe1\u606f\uff1a403 \u9519\u8bef\u3002", 
    " Technical details: CSRF verification failed.": " \u6280\u672f\u8be6\u7ec6\u4fe1\u606f\uff1aCSRF \u9a8c\u8bc1\u5931\u8d25\u3002", 
    "An error occurred while uploading your file. Please refresh the page and try again. If it still does not upload, please contact your Course TA.": "\u4e0a\u4f20\u60a8\u7684\u6587\u4ef6\u65f6\u51fa\u9519\u3002\u8bf7\u5237\u65b0\u9875\u9762\u5e76\u91cd\u8bd5\u3002\u5982\u679c\u4ecd\u7136\u65e0\u6cd5\u4e0a\u4f20\uff0c\u8bf7\u8054\u7cfb\u60a8\u7684\u8bfe\u7a0b\u52a9\u6559\u3002", 
    "Error": "\u9519\u8bef", 
    "Error refreshing statuses": "\u5237\u65b0\u72b6\u6001\u65f6\u51fa\u9519", 
    "Please select Group to review": "\u8bf7\u9009\u62e9\u5c0f\u7ec4\u4ee5\u8fdb\u884c\u5ba1\u67e5", 
    "Please select Teammate to review": "\u8bf7\u9009\u62e9\u7ec4\u5458\u4ee5\u8fdb\u884c\u5ba1\u67e5", 
    "Resubmit": "\u91cd\u65b0\u63d0\u4ea4", 
    "Submit": "\u63d0\u4ea4", 
    "Thanks for your feedback!": "\u611f\u8c22\u60a8\u7684\u53cd\u9988\uff01", 
    "This task has been marked as complete.": "\u6b64\u4efb\u52a1\u5df2\u6807\u8bb0\u4e3a\u5b8c\u6210\u3002", 
    "Upload cancelled by user.": "\u7528\u6237\u5df2\u53d6\u6d88\u4e0a\u4f20\u3002", 
    "Upload cancelled.": "\u4e0a\u4f20\u5df2\u53d6\u6d88\u3002", 
    "We encountered an error loading your feedback.": "\u52a0\u8f7d\u60a8\u7684\u53cd\u9988\u65f6\u9047\u5230\u9519\u8bef\u3002", 
    "We encountered an error saving your feedback.": "\u4fdd\u5b58\u60a8\u7684\u53cd\u9988\u65f6\u9047\u5230\u9519\u8bef\u3002", 
    "We encountered an error saving your progress.": "\u4fdd\u5b58\u60a8\u7684\u8fdb\u5ea6\u65f6\u9047\u5230\u9519\u8bef\u3002", 
    "We encountered an error.": "\u6211\u4eec\u9047\u5230\u4e86\u9519\u8bef\u3002"
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
    "DATETIME_FORMAT": "N j, Y, P", 
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
    "DATE_FORMAT": "N j, Y", 
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
    "MONTH_DAY_FORMAT": "F j", 
    "NUMBER_GROUPING": "0", 
    "SHORT_DATETIME_FORMAT": "m/d/Y P", 
    "SHORT_DATE_FORMAT": "m/d/Y", 
    "THOUSAND_SEPARATOR": ",", 
    "TIME_FORMAT": "P", 
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S", 
      "%H:%M:%S.%f", 
      "%H:%M"
    ], 
    "YEAR_MONTH_FORMAT": "F Y"
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
        
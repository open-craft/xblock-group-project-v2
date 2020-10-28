

(function(globals) {

  var django = globals.django || (globals.django = {});

  
  django.pluralidx = function(count) { return (count == 1) ? 0 : 1; };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  var newcatalog = {
    " Technical details: 403 error.": " \uae30\uc220\uc801 \uc138\ubd80\uc815\ubcf4: 403 \uc624\ub958.", 
    " Technical details: CSRF verification failed.": " \uae30\uc220\uc801 \uc138\ubd80\uc815\ubcf4: CSRF \uac80\uc99d\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.", 
    "An error occurred while uploading your file. Please refresh the page and try again. If it still does not upload, please contact your Course TA.": "\ud30c\uc77c\uc744 \uc5c5\ub85c\ub4dc\ud558\ub294 \ub3d9\uc548 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4. \ud398\uc774\uc9c0\ub97c \uc0c8\ub85c \uace0\uce68\ud558\uace0 \ub2e4\uc2dc \uc2dc\ub3c4\ud574 \ubcf4\uc2ed\uc2dc\uc624. \uadf8\ub798\ub3c4 \uc5c5\ub85c\ub4dc\ub418\uc9c0 \uc54a\uc73c\uba74 \uac15\uc758 \uc870\uad50\uc5d0\uac8c \ubb38\uc758\ud558\uc2ed\uc2dc\uc624.", 
    "Error": "\uc624\ub958", 
    "Error refreshing statuses": "\uc0c1\ud0dc\ub97c \uc0c8\ub85c \uace0\uce58\ub294 \uc911\uc5d0 \uc624\ub958 \ubc1c\uc0dd", 
    "Please select Group to review": "\uac80\ud1a0\ud560 \uadf8\ub8f9\uc744 \uc120\ud0dd\ud558\uc2ed\uc2dc\uc624.", 
    "Please select Teammate to review": "\uac80\ud1a0\ud560 \ud300\uc6d0\uc744 \uc120\ud0dd\ud558\uc2ed\uc2dc\uc624.", 
    "Resubmit": "\ub2e4\uc2dc \uc81c\ucd9c", 
    "Submit": "\uc81c\ucd9c", 
    "Thanks for your feedback!": "\ud53c\ub4dc\ubc31\uc744 \ubcf4\ub0b4 \uc8fc\uc154\uc11c \uac10\uc0ac\ud569\ub2c8\ub2e4!", 
    "This task has been marked as complete.": "\uc774 \ud0dc\uc2a4\ud06c\ub294 \uc644\ub8cc\ub41c \uac83\uc73c\ub85c \ud45c\uc2dc\ub418\uc5c8\uc2b5\ub2c8\ub2e4.", 
    "Upload cancelled by user.": "\uc0ac\uc6a9\uc790\uac00 \uc5c5\ub85c\ub4dc\ub97c \ucde8\uc18c\ud588\uc2b5\ub2c8\ub2e4.", 
    "Upload cancelled.": "\uc5c5\ub85c\ub4dc\uac00 \ucde8\uc18c\ub418\uc5c8\uc2b5\ub2c8\ub2e4.", 
    "We encountered an error loading your feedback.": "\ud53c\ub4dc\ubc31\uc744 \ub85c\ub4dc\ud558\ub294 \uc911\uc5d0 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.", 
    "We encountered an error saving your feedback.": "\ud53c\ub4dc\ubc31\uc744 \uc800\uc7a5\ud558\ub294 \uc911\uc5d0 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.", 
    "We encountered an error saving your progress.": "\uc9c4\ub3c4\uc728\uc744 \uc800\uc7a5\ud558\ub294 \uc911\uc5d0 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.", 
    "We encountered an error.": "\uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4."
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
    "DATETIME_FORMAT": "Y\ub144 n\uc6d4 j\uc77c g:i A", 
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
      "%m/%d/%y", 
      "%Y\ub144 %m\uc6d4 %d\uc77c %H\uc2dc %M\ubd84 %S\ucd08", 
      "%Y\ub144 %m\uc6d4 %d\uc77c %H\uc2dc %M\ubd84"
    ], 
    "DATE_FORMAT": "Y\ub144 n\uc6d4 j\uc77c", 
    "DATE_INPUT_FORMATS": [
      "%Y-%m-%d", 
      "%m/%d/%Y", 
      "%m/%d/%y", 
      "%Y\ub144 %m\uc6d4 %d\uc77c"
    ], 
    "DECIMAL_SEPARATOR": ".", 
    "FIRST_DAY_OF_WEEK": "0", 
    "MONTH_DAY_FORMAT": "n\uc6d4 j\uc77c", 
    "NUMBER_GROUPING": "3", 
    "SHORT_DATETIME_FORMAT": "Y-n-j H:i", 
    "SHORT_DATE_FORMAT": "Y-n-j.", 
    "THOUSAND_SEPARATOR": ",", 
    "TIME_FORMAT": "A g:i", 
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S", 
      "%H:%M:%S.%f", 
      "%H:%M", 
      "%H\uc2dc %M\ubd84 %S\ucd08", 
      "%H\uc2dc %M\ubd84"
    ], 
    "YEAR_MONTH_FORMAT": "Y\ub144 n\uc6d4"
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


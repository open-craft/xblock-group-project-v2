
            (function(global){
                var GroupProjectV2XBlockI18N = {
                  init: function() {
                    

(function(globals) {

  var django = globals.django || (globals.django = {});

  
  django.pluralidx = function(count) { return (count == 1) ? 0 : 1; };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  var newcatalog = {
    " Technical details: 403 error.": "Szczeg\u00f3\u0142y techniczne: B\u0142\u0105d 403.", 
    " Technical details: CSRF verification failed.": "Szczeg\u00f3\u0142y techniczne: B\u0142\u0105d weryfikacji CSRF.", 
    "An error occurred while uploading your file. Please refresh the page and try again. If it still does not upload, please contact your Course TA.": "Podczas przesy\u0142ania pliku wyst\u0105pi\u0142 b\u0142\u0105d. Od\u015bwie\u017c stron\u0119 i spr\u00f3buj ponownie. Je\u015bli przesy\u0142anie si\u0119 nie uda, skontaktuj si\u0119 z Asystentem Kursu.", 
    "Error": "B\u0142\u0105d", 
    "Error refreshing statuses": "B\u0142\u0105d podczas od\u015bwie\u017cania status\u00f3w", 
    "Please select Group to review": "Wybierz grup\u0119, kt\u00f3r\u0105 chcesz oceni\u0107", 
    "Please select Teammate to review": "Wybierz Cz\u0142onka zespo\u0142u, kt\u00f3rego chcesz oceni\u0107", 
    "Resubmit": "Prze\u015blij ponownie", 
    "Submit": "Prze\u015blij", 
    "Thanks for your feedback!": "Dzi\u0119kujemy za przes\u0142anie opinii.", 
    "This task has been marked as complete.": "To zadanie oznaczono jako uko\u0144czone.", 
    "Upload cancelled by user.": "U\u017cytkownik przerwa\u0142 przesy\u0142anie.", 
    "Upload cancelled.": "Przerwano przesy\u0142anie", 
    "We encountered an error loading your feedback.": "Podczas wczytywania Twojej opinii wyst\u0105pi\u0142 b\u0142\u0105d.", 
    "We encountered an error saving your feedback.": "Podczas zapisywania Twojej opinii wyst\u0105pi\u0142 b\u0142\u0105d.", 
    "We encountered an error saving your progress.": "Podczas zapisywania Twojego stopnia uko\u0144czenia wyst\u0105pi\u0142 b\u0142\u0105d.", 
    "We encountered an error.": "Wyst\u0105pi\u0142 b\u0142\u0105d."
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
    "DATETIME_FORMAT": "j E Y H:i", 
    "DATETIME_INPUT_FORMATS": [
      "%d.%m.%Y %H:%M:%S", 
      "%d.%m.%Y %H:%M:%S.%f", 
      "%d.%m.%Y %H:%M", 
      "%d.%m.%Y", 
      "%Y-%m-%d %H:%M:%S", 
      "%Y-%m-%d %H:%M:%S.%f", 
      "%Y-%m-%d %H:%M", 
      "%Y-%m-%d"
    ], 
    "DATE_FORMAT": "j E Y", 
    "DATE_INPUT_FORMATS": [
      "%d.%m.%Y", 
      "%d.%m.%y", 
      "%y-%m-%d", 
      "%Y-%m-%d"
    ], 
    "DECIMAL_SEPARATOR": ",", 
    "FIRST_DAY_OF_WEEK": "1", 
    "MONTH_DAY_FORMAT": "j F", 
    "NUMBER_GROUPING": "3", 
    "SHORT_DATETIME_FORMAT": "d-m-Y  H:i", 
    "SHORT_DATE_FORMAT": "d-m-Y", 
    "THOUSAND_SEPARATOR": "\u00a0", 
    "TIME_FORMAT": "H:i", 
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
        
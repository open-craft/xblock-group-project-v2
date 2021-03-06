
            (function(global){
                var GroupProjectV2XBlockI18N = {
                  init: function() {


(function(globals) {

  var django = globals.django || (globals.django = {});


  django.pluralidx = function(count) { return (count == 1) ? 0 : 1; };


  /* gettext library */

  django.catalog = django.catalog || {};

  var newcatalog = {
    " Technical details: 403 error.": " Detalles t\u00e9cnicos:\u00a0Error\u00a0403.",
    " Technical details: CSRF verification failed.": " Detalles t\u00e9cnicos:\u00a0Error en la comprobaci\u00f3n del CSRF.",
    " on ": " Activado ",
    "An error occurred while uploading your file. Please refresh the page and try again. If it still does not upload, please contact your Course TA.": "Se produjo un error durante la carga del archivo. Actualice la p\u00e1gina y vuelva a intentarlo. Si se produce otro error al cargar el archivo, p\u00f3ngase en contacto con su TA del curso.",
    "Error": "Error",
    "Error refreshing statuses": "Se produjo un error al actualizar los estados.",
    "Notification": "Notificaci\u00f3n",
    "Please select Group to review": "Seleccione un grupo para la revisi\u00f3n",
    "Please select Teammate to review": "Seleccione un compa\u00f1ero de equipo para la revisi\u00f3n",
    "Resubmit": "Volver a enviar",
    "Submit": "Enviar",
    "Thanks for your feedback!": "Gracias por compartir su comentario.",
    "This task has been marked as complete.": "Esta tarea se marc\u00f3 como Finalizada.",
    "Upload cancelled by user.": "El usuario cancel\u00f3 la carga.",
    "Upload cancelled.": "Se cancel\u00f3 la carga.",
    "Uploaded by ": "Cargado por ",
    "We encountered an error loading your feedback.": "Se encontr\u00f3 un error al cargar su comentario.",
    "We encountered an error saving your feedback.": "Se encontr\u00f3 un error al guardar su comentario.",
    "We encountered an error saving your progress.": "Se encontr\u00f3 un error al guardar su progreso.",
    "We encountered an error.": "Se encontr\u00f3 un error."
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
    "DATETIME_FORMAT": "j \\d\\e F \\d\\e Y \\a \\l\\a\\s H:i",
    "DATETIME_INPUT_FORMATS": [
      "%d/%m/%Y %H:%M:%S",
      "%d/%m/%Y %H:%M:%S.%f",
      "%d/%m/%Y %H:%M",
      "%d/%m/%y %H:%M:%S",
      "%d/%m/%y %H:%M:%S.%f",
      "%d/%m/%y %H:%M",
      "%Y-%m-%d %H:%M:%S",
      "%Y-%m-%d %H:%M:%S.%f",
      "%Y-%m-%d %H:%M",
      "%Y-%m-%d"
    ],
    "DATE_FORMAT": "j \\d\\e F \\d\\e Y",
    "DATE_INPUT_FORMATS": [
      "%d/%m/%Y",
      "%d/%m/%y",
      "%Y-%m-%d"
    ],
    "DECIMAL_SEPARATOR": ",",
    "FIRST_DAY_OF_WEEK": "1",
    "MONTH_DAY_FORMAT": "j \\d\\e F",
    "NUMBER_GROUPING": "3",
    "SHORT_DATETIME_FORMAT": "d/m/Y H:i",
    "SHORT_DATE_FORMAT": "d/m/Y",
    "THOUSAND_SEPARATOR": ".",
    "TIME_FORMAT": "H:i",
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S",
      "%H:%M:%S.%f",
      "%H:%M"
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

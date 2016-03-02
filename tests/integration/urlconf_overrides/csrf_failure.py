# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.middleware.csrf import _get_failure_view


def view(*args, **kwargs):
    return _get_failure_view()(*args, **kwargs)


# pylint: disable=invalid-name
urlpatterns = [
    url(r'.*', view),
]

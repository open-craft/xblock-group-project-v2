# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.http import HttpResponse


# pylint: disable=unused-argument
def view(*args, **kwargs):
    return HttpResponse(status=403)


# pylint: disable=invalid-name
urlpatterns = [
    url(r'.*', view),
]

from django.urls import include, path
from django.contrib import admin
from app.api import api


urlpatterns = [
    path("admin/", admin.site.urls, name="admin"),
    path("dispatch/", include("dispatch.urls")),
    path("api/", api.urls, name="api"),
]

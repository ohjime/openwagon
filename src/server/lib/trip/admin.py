from django.contrib import admin

from unfold.admin import ModelAdmin

from trip.models import Trip


@admin.register(Trip)
class TripAdmin(ModelAdmin):
    pass

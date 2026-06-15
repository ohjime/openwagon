from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin

from .models import Account, Driver, Rider, Trip, User, Place


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    pass


@admin.register(Account)
class AccountAdmin(ModelAdmin):
    pass


@admin.register(Driver)
class DriverAdmin(ModelAdmin):
    pass


@admin.register(Rider)
class RiderAdmin(ModelAdmin):
    pass


@admin.register(Trip)
class TripAdmin(ModelAdmin):
    pass


@admin.register(Place)
class PlaceAdmin(ModelAdmin):
    pass

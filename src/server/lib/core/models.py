from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    pass


class Account(models.Model):
    uid = models.CharField(max_length=128, unique=True, db_index=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=255, blank=True, null=True)
    avatar = models.URLField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        # Normalize phone: convert empty string to None, strip whitespace if not None
        if self.phone is not None:
            self.phone = self.phone.strip()
            if self.phone == "":
                self.phone = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class Driver(models.Model):
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="driver",
    )

    def __str__(self):
        return self.account.first_name + " " + self.account.last_name


class Rider(models.Model):
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="rider",
    )

    def __str__(self):
        return self.account.first_name + " " + self.account.last_name

import random
import factory

from factory.declarations import LazyFunction, SubFactory
from factory.faker import Faker
from core.models import Account, Driver, Rider

from uuid import uuid4


def _unique_email() -> str:
    """Return an email not present in the DB, trying a few random candidates."""
    # Try a bunch of random numeric suffixes to avoid collisions with prior runs.
    for _ in range(1000):
        n = random.randint(0, 10**12)
        email = f"user{n}@example.com"
        if not Account.objects.filter(email=email).exists():
            return email
    # Absolute fallback using UUID to guarantee uniqueness
    return f"user-{uuid4()}@example.com"


def _unique_uid() -> str:
    """Return a UUID that's not already used in the DB (extremely unlikely collision)."""
    for _ in range(10):
        uid = str(uuid4())
        if not Account.objects.filter(uid=uid).exists():
            return uid
    return str(uuid4())


def _unique_phone() -> str:
    """Return a phone number not present in the DB (E.164 +1XXXXXXXXXX)."""
    for _ in range(1000):
        n = random.randint(0, 10**10 - 1)
        phone = "+1" + f"{n:010d}"
        if not Account.objects.filter(phone=phone).exists():
            return phone
    # Fallback with UUID-derived tail to guarantee uniqueness
    tail = str(uuid4().int % (10**10)).rjust(10, "0")
    return "+1" + tail


class AccountFactory(factory.django.DjangoModelFactory):
    """Base account used by Driver/Rider factories."""

    class Meta:  # type: ignore
        model = Account

    # Ensure UID doesn't collide with existing rows (super rare, but safe)
    uid = LazyFunction(_unique_uid)
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    # Ensure DB-unique emails across multiple runs
    email = LazyFunction(_unique_email)
    # Short E.164-style and DB-unique across runs
    phone = LazyFunction(_unique_phone)

    @factory.lazy_attribute  # type: ignore
    def avatar(self):
        return f"https://i.pravatar.cc/150?u={self.uid}"


class DriverFactory(factory.django.DjangoModelFactory):
    class Meta:  # type: ignore
        model = Driver

    account = SubFactory(AccountFactory)  # type: ignore


class RiderFactory(factory.django.DjangoModelFactory):
    class Meta:  # type: ignore
        model = Rider

    account = SubFactory(AccountFactory)  # type: ignore

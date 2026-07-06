from django.db import migrations

# Seed the one zone the app assumes while geometry wiring is still pending
# ("all trips are in-zone for now"), plus its open-to-everyone default plan —
# so the New Trip plan dropdown is never empty. Rates are placeholders the
# administration edits in admin; the shape (rate × measurement, 15% tax) is
# the canonical algorithm ServicePlan implements.


def seed_default_zone_and_plan(apps, schema_editor):
    Zone = apps.get_model("core", "Zone")
    ServicePlan = apps.get_model("core", "ServicePlan")
    zone, _ = Zone.objects.get_or_create(name="Default Zone")
    ServicePlan.objects.get_or_create(
        zone=zone,
        is_default=True,
        defaults={
            "name": "Zone Default",
            "base_fare": "3.50",
            "meter_rate": "1.75",
            "duration_rate": "0.50",
            "waiting_rate": "0.65",
            "tax_rate": "0.15",
        },
    )


def unseed_default_zone_and_plan(apps, schema_editor):
    # Remove only the exact seeded rows. A plan referenced by trips/invoices is
    # PROTECTed and will (correctly) block the reverse migration.
    Zone = apps.get_model("core", "Zone")
    ServicePlan = apps.get_model("core", "ServicePlan")
    ServicePlan.objects.filter(zone__name="Default Zone", name="Zone Default").delete()
    Zone.objects.filter(name="Default Zone", plans__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_zone_trip_distance_km_trip_duration_min_and_more"),
    ]

    operations = [
        migrations.RunPython(
            seed_default_zone_and_plan, unseed_default_zone_and_plan
        ),
    ]

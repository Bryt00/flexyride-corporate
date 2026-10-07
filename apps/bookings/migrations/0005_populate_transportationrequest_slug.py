import uuid

from django.db import migrations


def gen_uuid(apps, schema_editor):
    """Step 2/3: give every existing row its own distinct UUID."""
    Model = apps.get_model('bookings', 'TransportationRequest')
    for row in Model.objects.all().only('pk'):
        row.slug = uuid.uuid4()
        row.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_transportationrequest_slug'),
    ]

    operations = [
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
    ]

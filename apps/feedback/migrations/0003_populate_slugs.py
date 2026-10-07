import uuid

from django.db import migrations


def gen_uuid(apps, schema_editor):
    """Step 2/3: give every existing row its own distinct UUID."""
    for model_name in ('JourneyRating', 'SupportIssue'):
        Model = apps.get_model('feedback', model_name)
        for row in Model.objects.all().only('pk'):
            row.slug = uuid.uuid4()
            row.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0002_journeyrating_slug_supportissue_slug'),
    ]

    operations = [
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
    ]

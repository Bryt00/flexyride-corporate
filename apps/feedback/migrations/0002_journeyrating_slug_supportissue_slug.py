import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1/3: add slug as nullable, non-unique so existing rows don't collide."""

    dependencies = [
        ('feedback', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='journeyrating',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='supportissue',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
    ]

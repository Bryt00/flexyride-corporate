import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1/3: add slug as nullable, non-unique so existing rows don't collide."""

    dependencies = [
        ('bookings', '0003_widen_coordinate_precision'),
    ]

    operations = [
        migrations.AddField(
            model_name='transportationrequest',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
    ]

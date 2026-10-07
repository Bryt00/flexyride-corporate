import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3/3: enforce NOT NULL + UNIQUE now that every row has a distinct value."""

    dependencies = [
        ('bookings', '0005_populate_transportationrequest_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transportationrequest',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

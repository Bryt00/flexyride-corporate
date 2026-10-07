import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3/3: enforce NOT NULL + UNIQUE now that every row has a distinct value."""

    dependencies = [
        ('feedback', '0003_populate_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journeyrating',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='supportissue',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

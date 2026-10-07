import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3/3: enforce NOT NULL + UNIQUE now that every row has a distinct value."""

    dependencies = [
        ('payments', '0005_populate_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='paymenttransaction',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

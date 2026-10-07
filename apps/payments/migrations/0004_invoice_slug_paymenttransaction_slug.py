import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1/3: add slug as nullable, non-unique so existing rows don't collide."""

    dependencies = [
        ('payments', '0003_alter_invoice_currency_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='paymenttransaction',
            name='slug',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
    ]

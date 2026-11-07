from django.db import migrations, models


class Migration(migrations.Migration):
    """Swap WhatsApp for the Bale messenger (بله) as the shop's chat contact."""

    dependencies = [
        ("orders", "0003_shipping_payment_settings"),
    ]

    operations = [
        migrations.RenameField(model_name="shopsettings", old_name="whatsapp", new_name="bale"),
        migrations.AlterField(
            model_name="shopsettings",
            name="bale",
            field=models.CharField(
                blank=True, help_text="Bale messenger username without @ (or a full ble.ir link)", max_length=100
            ),
        ),
    ]

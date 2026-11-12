from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0006_seo_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="show_on_home",
            field=models.BooleanField(
                default=False, help_text="Show as a highlighted circle on the home page"
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_farmerprofile_is_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_verified',
            field=models.BooleanField(default=False, help_text='Email подтверждён'),
        ),
        # AlterField убрали — оставляем max_length=20 как было
    ]
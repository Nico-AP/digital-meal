# Generated by Django 4.2.10 on 2024-03-22 12:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('digital_meal', '0012_classroom_agb_agree'),
    ]

    operations = [
        migrations.AlterField(
            model_name='classroom',
            name='agb_agree',
            field=models.BooleanField(default=False, verbose_name='AGBs akzeptiert'),
        ),
    ]
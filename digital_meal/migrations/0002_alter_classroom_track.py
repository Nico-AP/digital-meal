# Generated by Django 3.2.19 on 2024-01-09 13:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('digital_meal', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='classroom',
            name='track',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='digital_meal.track', verbose_name='Track'),
        ),
    ]
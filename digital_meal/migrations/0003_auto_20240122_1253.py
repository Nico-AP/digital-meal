# Generated by Django 3.2.19 on 2024-01-22 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('digital_meal', '0002_alter_classroom_track'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='track',
            name='module',
        ),
        migrations.AddField(
            model_name='track',
            name='ddm_path',
            field=models.URLField(default='https://notset.com'),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='Module',
        ),
    ]
# Generated by Django 4.2.10 on 2024-03-04 20:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('digital_meal', '0009_rename_external_id_classroom_class_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='classroom',
            name='report_ref_end_date',
            field=models.DateTimeField(default=None, null=True),
        ),
    ]

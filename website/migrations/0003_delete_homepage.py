# Generated by Django 3.2.19 on 2024-02-20 12:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0089_log_entry_data_json_null_to_object'),
        ('wagtailforms', '0005_alter_formsubmission_form_data'),
        ('wagtailredirects', '0008_add_verbose_name_plural'),
        ('website', '0002_homepage'),
    ]

    operations = [
        migrations.DeleteModel(
            name='HomePage',
        ),
    ]
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tool', '0005_alter_classroom_url_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='MainTrack',
            name='data_endpoint',
        ),
        migrations.RemoveField(
            model_name='MainTrack',
            name='overview_endpoint',
        ),
        migrations.RemoveField(
            model_name='MainTrack',
            name='ddm_api_token',
        ),
        migrations.RemoveField(
            model_name='MainTrack',
            name='image',
        ),

        # Rename the models
        migrations.RenameModel(
            old_name='MainTrack',
            new_name='BaseModule',
        ),
        migrations.RenameModel(
            old_name='SubTrack',
            new_name='SubModule',
        ),

        # Rename fields within renamed models if necessary
        migrations.RenameField(
            model_name='submodule',
            old_name='main_track',
            new_name='base_module',
        ),

        # Rename the fields in Classroom model
        migrations.RenameField(
            model_name='classroom',
            old_name='track',
            new_name='base_module',
        ),
        migrations.RenameField(
            model_name='classroom',
            old_name='sub_tracks',
            new_name='sub_modules',
        ),
    ]

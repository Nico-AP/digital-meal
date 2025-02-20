import secrets
import string

import digital_meal.tool.models
from django.db import migrations, models


def generate_unique_url_id(apps, schema_editor):
    """Generate a unique 10-character URL-safe ID"""
    Classroom = apps.get_model('tool', 'Classroom')  # Get model dynamically
    existing_ids = set(Classroom.objects.values_list('url_id', flat=True))

    def get_new_id():
        while True:
            new_id = ''.join(secrets.choice(string.ascii_letters + string.digits + '-_') for _ in range(10))
            if new_id not in existing_ids:
                existing_ids.add(new_id)
                return new_id

    for classroom in Classroom.objects.filter(url_id__isnull=True).iterator():
        classroom.url_id = get_new_id()
        classroom.save(update_fields=['url_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('tool', '0004_classroom_url_id'),
    ]

    operations = [
        migrations.RunPython(generate_unique_url_id),
        migrations.AlterField(
            model_name='classroom',
            name='url_id',
            field=models.SlugField(default=digital_meal.tool.models.generate_unique_classroom_id, max_length=10, unique=True),
        ),
    ]

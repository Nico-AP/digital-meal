# Generated by Django 4.2.16 on 2025-06-26 11:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portability', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TikTokAccessToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=250)),
                ('token_expiration_date', models.DateTimeField(null=True)),
                ('refresh_token', models.CharField(max_length=250)),
                ('refresh_token_expiration_date', models.DateTimeField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('open_id', models.CharField(max_length=250, unique=True, verbose_name='ID of TikTok user')),
                ('scope', models.CharField(max_length=250)),
                ('token_type', models.CharField(max_length=50)),
            ],
        ),
    ]

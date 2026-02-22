"""
Migration: add ApiKey model.

Table is created by workflow.ddl.sql; initdb.sh runs this with --fake.
"""

## import django pkgs
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0002_devtoolrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApiKey',
            fields=[
                ('id',         models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',       models.CharField(max_length=128)),
                ('key_prefix', models.CharField(max_length=8)),
                ('key_hash',   models.CharField(max_length=64)),
                ('created_by', models.CharField(max_length=150)),
                ('last_used',  models.DateTimeField(blank=True, null=True)),
                ('enabled',    models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'system_api_key',
                'ordering': ['-created_at'],
            },
        ),
    ]

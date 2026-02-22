"""
Migration: update ApiKey id field to BigAutoField.

Table is created by workflow.ddl.sql; initdb.sh runs this with --fake.
"""

## import django pkgs
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0003_apikey'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apikey',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]

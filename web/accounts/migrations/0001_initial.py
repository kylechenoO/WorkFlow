# Consolidated migration for accounts app (v0.0.3)
# Tables are created by raw SQL (tools/workflow.ddl.sql); this migration
# is recorded via 'manage.py migrate accounts --fake' in initdb.sh.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        ## Role model (wf_role + M2M wf_user_role)
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('users', models.ManyToManyField(blank=True, db_table='wf_user_role', related_name='wf_roles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'wf_role',
                'ordering': ['name'],
            },
        ),
        ## Permission model (wf_permission, managed=False)
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page', models.CharField(max_length=64)),
                ('action', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'wf_permission',
                'ordering': ['page', 'action'],
                'managed': False,
            },
        ),
        ## GroupPermission model (wf_group_permission, managed=False)
        migrations.CreateModel(
            name='GroupPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'db_table': 'wf_group_permission',
                'managed': False,
            },
        ),
        ## Role.permissions M2M (wf_role_permission)
        migrations.AddField(
            model_name='role',
            name='permissions',
            field=models.ManyToManyField(blank=True, db_table='wf_role_permission', related_name='roles', to='accounts.permission'),
        ),
        ## UserProfile model (wf_user_profile)
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password_changed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wf_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'wf_user_profile',
            },
        ),
    ]

# Generated by Django 4.2.20 on 2025-05-08 06:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0013_notificationsettings_created_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('fulfilled', 'Fulfilled'), ('cancelled', 'Cancelled')], default='pending', max_length=20),
        ),
    ]

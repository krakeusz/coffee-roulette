# Generated by Django 3.0.3 on 2020-05-11 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matcher', '0005_penaltygroup_custom_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rouletteuser',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]

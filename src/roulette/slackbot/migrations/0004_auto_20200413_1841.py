# Generated by Django 3.0.3 on 2020-04-13 16:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('slackbot', '0003_auto_20200413_1839'),
    ]

    operations = [
        migrations.RenameField(
            model_name='slackuser',
            old_name='roulette_user',
            new_name='user',
        ),
    ]

# Generated by Django 3.0.3 on 2020-04-13 16:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('slackbot', '0002_slackadminuser'),
    ]

    operations = [
        migrations.AddField(
            model_name='slackadminuser',
            name='im_channel',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='slackuser',
            name='im_channel',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]

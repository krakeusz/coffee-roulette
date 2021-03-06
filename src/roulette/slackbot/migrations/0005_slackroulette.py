# Generated by Django 3.0.3 on 2020-05-11 09:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('matcher', '0005_penaltygroup_custom_name'),
        ('slackbot', '0004_auto_20200413_1841'),
    ]

    operations = [
        migrations.CreateModel(
            name='SlackRoulette',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('thread_timestamp', models.CharField(max_length=30)),
                ('latest_response_timestamp', models.CharField(default='0', max_length=30)),
                ('roulette', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='matcher.Roulette')),
            ],
        ),
    ]

# Generated by Django 3.2.8 on 2021-10-30 12:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0009_alter_securities_ticker'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Securities',
            new_name='Security',
        ),
    ]
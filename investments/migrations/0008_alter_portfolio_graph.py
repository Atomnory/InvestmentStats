# Generated by Django 3.2.8 on 2021-10-20 11:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0007_delete_piegraph'),
    ]

    operations = [
        migrations.AlterField(
            model_name='portfolio',
            name='graph',
            field=models.ImageField(null=True, upload_to='portfolio_graph', verbose_name='Portfolio pie graph'),
        ),
    ]

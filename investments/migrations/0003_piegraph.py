# Generated by Django 3.2.8 on 2021-10-16 08:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0002_alter_portfolio_sector'),
    ]

    operations = [
        migrations.CreateModel(
            name='PieGraph',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('graph', models.ImageField(upload_to='pie_graph', verbose_name='Pie Graph')),
            ],
        ),
    ]

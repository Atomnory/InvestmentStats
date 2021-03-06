# Generated by Django 3.2.8 on 2021-10-14 13:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='portfolio',
            name='sector',
            field=models.CharField(choices=[('BMAT', 'Basic Materials'), ('BOND', 'Bonds'), ('COM', 'Communication Services'), ('CYCL', 'Consumer Cyclical'), ('DEF', 'Consumer Defensive'), ('ENER', 'Energy'), ('ETF', 'ETF'), ('FIN', 'Financial Services'), ('GOLD', 'Gold'), ('HEAL', 'Healthcare'), ('IND', 'Industrials'), ('EST', 'Real Estate'), ('TECH', 'Technology'), ('UTIL', 'Utilities')], max_length=20, verbose_name='Sector'),
        ),
    ]

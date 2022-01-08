# Generated by Django 3.2.8 on 2021-10-14 13:28

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Portfolio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticker', models.CharField(max_length=10, verbose_name='Ticker')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('quantity', models.IntegerField(verbose_name='Quantity')),
                ('price', models.DecimalField(decimal_places=4, max_digits=12, verbose_name='Price')),
                ('currency', models.CharField(choices=[('EUR', 'EUR'), ('RUB', 'RUB'), ('USD', 'USD')], max_length=3, verbose_name='Currency')),
                ('sector', models.CharField(choices=[('EUR', 'EUR'), ('RUB', 'RUB'), ('USD', 'USD')], max_length=20, verbose_name='Sector')),
                ('country', models.CharField(max_length=20, verbose_name='Country')),
            ],
        ),
    ]
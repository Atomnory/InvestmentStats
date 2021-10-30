from config.settings import TINVEST_TOKEN
from tinvest import SyncClient
import time
from .models import Security
from tinvest.exceptions import TooManyRequestsError, UnexpectedError


def get_etfs():
    client = SyncClient(TINVEST_TOKEN)
    data = client.get_market_etfs()
    etfs = data.dict()
    instrs = etfs['payload']['instruments']
    save_securities(client, instrs)


# def get_stocks():
#     client = SyncClient(TINVEST_TOKEN)
#     data = client.get_market_stocks()
#     stocks = data.dict()
#     instrs = stocks['payload']['instruments']
#     print_secs(client, instrs)


def get_bonds():
    client = SyncClient(TINVEST_TOKEN)
    data = client.get_market_bonds()
    bonds = data.dict()
    instrs = bonds['payload']['instruments']
    save_securities(client, instrs)


def print_secs(client: SyncClient, instruments: list):
    count = 0
    for row in instruments:
        if count >= 1:
            break
        searcher = client.get_market_search_by_figi(row['figi'])
        price = client.get_market_orderbook(row['figi'], 1)
        print(searcher)
        print(price)
        count += 1
        # print('Security:',
        #       '$' + str(searcher.payload.ticker),
        #       searcher.payload.name,
        #       'price:',
        #       price.payload.close_price,
        #       searcher.payload.currency.value)
    return


def save_securities(client: SyncClient, instruments: list):
    count = 0
    len_instr = len(instruments)
    for row in instruments:
        if count % 100 == 0:
            time.sleep(60)
        try:
            orderbook = client.get_market_orderbook(row['figi'], 1)
        except TooManyRequestsError as e:
            print(e)
            time.sleep(60)
            orderbook = client.get_market_orderbook(row['figi'], 1)
        except UnexpectedError as e:
            count += 1
            print(row)
            print(count, '/', len_instr, '(' + str(row['ticker']) + ')', 'ERROR:', e)
            continue
        sec_sector = 'CASH'
        if row['type'].value == 'Etf':
            sec_sector = 'ETF'
        elif row['type'].value == 'Bond':
            sec_sector = 'BOND'
        elif row['type'].value == 'Stock':
            sec_sector = 'CASH'
        # TODO: add defining sector for Stocks
        # TODO: add defining Country
        try:
            sec = Security(
                ticker=row['ticker'],
                name=row['name'],
                price=orderbook.payload.close_price,
                currency=row['currency'].value,
                sector=sec_sector,
                country='?'
            )
            sec.save()
        except Exception as e:
            count += 1
            print(row)
            print(count, '/', len_instr, '(' + str(row['ticker']) + ')', 'ERROR:', e)
            continue
        count += 1
        print(count, '/', len_instr, '(' + str(row['ticker']) + ')')



# ticker
# name
# (price from orderbook)
# currency.value
# sector - type.value (Etf)
# country - ??

    # ticker = models.CharField('Ticker', max_length=10, unique=True)
    # name = models.CharField('Name', max_length=100)
    # price = models.DecimalField('Price', max_digits=12, decimal_places=4)
    # currency = models.CharField('Currency', max_length=3, choices=currency_choice)
    # sector = models.CharField('Sector', max_length=20, choices=sector_choice)
    # country = models.CharField('Country', max_length=20)
    # update_date = models.DateField('Last update', auto_now=True)


def get_error():
    client = SyncClient(TINVEST_TOKEN)
    searcher = client.get_market_search_by_figi('ISSUANCERESO')
    price = client.get_market_orderbook('ISSUANCERESO', 1)
    print(searcher)
    print(price)

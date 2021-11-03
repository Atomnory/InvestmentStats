from config.settings import TINVEST_TOKEN, YAHOO_API_KEY, MEDIA_ROOT
from tinvest import SyncClient
import time
import requests
from .models import Security
from tinvest.exceptions import TooManyRequestsError, UnexpectedError
from typing import Optional
from datetime import datetime
from dateutil.parser import parse


def get_etfs():
    client = SyncClient(TINVEST_TOKEN)
    data = client.get_market_etfs()
    etfs = data.dict()
    instrs = etfs['payload']['instruments']
    save_securities(client, instrs)


def get_stocks():
    client = SyncClient(TINVEST_TOKEN)
    data = client.get_market_stocks()
    stocks = data.dict()
    instrs = stocks['payload']['instruments']
    print_secs(client, instrs)


def get_bonds():
    client = SyncClient(TINVEST_TOKEN)
    data = client.get_market_bonds()
    bonds = data.dict()
    instrs = bonds['payload']['instruments']
    save_securities(client, instrs)


def print_secs(client: SyncClient, instruments: list):
    count = 0
    for row in instruments:
        if count >= 10:
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
            sec_sector = None
        # TODO: add sector and country filling by hand form
        try:
            sec = Security(
                ticker=row['ticker'],
                name=row['name'],
                price=orderbook.payload.close_price,
                currency=row['currency'].value,
                sector=sec_sector,
                country=None
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


class StockNotFound(Exception):
    pass


def define_stock_sector_and_country():
    if not can_fill_stock_info():
        return
    stocks = get_list_all_stocks_without_country_and_sector()
    if not stocks:
        return
    not_find = []
    for row in stocks:
        new_ticker = define_ticker_by_currency(row.ticker, row.currency)
        try:
            info = get_stock_info_or_error(ticker=new_ticker)
            country = info['country']
            sector = info['sector']
            print('Ticker:', '$' + str(row.ticker) + ',',
                  "'" + str(new_ticker) + "',",
                  'country:', country,
                  'sector:', sector)
        except requests.ConnectionError as e:
            print(e)
            break
        except requests.HTTPError as e:
            print(e)
            break
        except StockNotFound as e:
            print(e)
            not_find.append(row.ticker)
            continue
        except Exception as e:
            print(e)
            break
        new_sector = define_short_sector_name(sector)
        if row.currency == 'RUB':
            new_country = 'Russia'
        else:
            new_country = country
        row.sector = new_sector
        row.country = new_country
        row.save()

    update_fill_stock_date()
    if not_find:
        save_not_finded_stocks(not_find)


def get_stock_info_or_error(ticker: str) -> dict:
    url = f'https://yfapi.net/v11/finance/quoteSummary/{ticker}'
    options = {
        'modules': 'assetProfile'
    }
    headers = {
        'accept': 'application/json',
        'x-api-key': YAHOO_API_KEY
    }
    response = requests.get(url=url, params=options, headers=headers)
    response.raise_for_status()
    data = response.json()['quoteSummary']['result']
    if data is None:
        raise StockNotFound('Not found')
    asset_profile = data[0]['assetProfile']
    return {'country': asset_profile['country'], 'sector': asset_profile['sector']}


def get_list_all_stocks_without_country_and_sector() -> Optional[list[Security]]:
    return Security.objects.filter(country__isnull=True, sector__isnull=True)


def define_ticker_by_currency(ticker: str, currency: str) -> str:
    if currency == 'USD':
        return ticker
    elif currency == 'EUR':
        return str(ticker) + '.DE'
    elif currency == 'RUB':
        return str(ticker) + '.ME'


def define_short_sector_name(sector: str) -> Optional[str]:
    if sector == 'Basic Materials':
        return 'BMAT'
    elif sector == 'Communication Services':
        return 'COM'
    elif sector == 'Consumer Cyclical':
        return 'CYCL'
    elif sector == 'Consumer Defensive':
        return 'DEF'
    elif sector == 'Energy':
        return 'ENER'
    elif sector == 'Financial Services':
        return 'FIN'
    elif sector == 'Healthcare':
        return 'HEAL'
    elif sector == 'Industrials':
        return 'IND'
    elif sector == 'Real Estate':
        return 'EST'
    elif sector == 'Technology':
        return 'TECH'
    elif sector == 'Utilities':
        return 'UTIL'
    else:
        print('ERROR: Sector undefined:', sector)
        return None


def can_fill_stock_info() -> bool:
    try:
        with open(f'{MEDIA_ROOT}/fill_stock_date.txt', 'r') as f:
            text = f.readline()
    except FileNotFoundError:
        return True
    date = parse(text).date()
    today = datetime.utcnow().date()
    if date == today:
        return False
    else:
        return True


def update_fill_stock_date():
    today = datetime.utcnow().date()
    with open(f'{MEDIA_ROOT}/fill_stock_date.txt', 'w') as f:
        f.write(str(today))


def save_not_finded_stocks(stocks: list[str]):
    prevs = get_not_finded_stocks()
    with open(f'{MEDIA_ROOT}/not_finded_stocks.txt', 'w') as f:
        if prevs is None:
                print(len(stocks), file=f)
                for row in stocks:
                    print(row, file=f)
        else:
                print(len(stocks) + len(prevs), file=f)
                for row in prevs:
                    print(row, file=f)
                for row in stocks:
                    print(row, file=f)


def get_not_finded_stocks() -> Optional[list[str]]:
    try:
        stocks = []
        with open(f'{MEDIA_ROOT}/not_finded_stocks.txt', 'r') as f:
            f.readline()
            for line in f.read().splitlines():
                stocks.append(line)
        return stocks
    except FileNotFoundError:
        return None


def get_not_finded_quantity() -> int:
    try:
        with open(f'{MEDIA_ROOT}/not_finded_stocks.txt', 'r') as f:
            quantity = f.readline()
        return int(quantity)
    except FileNotFoundError:
        return 0

from config.settings import TINVEST_TOKEN, YAHOO_API_KEY, MEDIA_ROOT
from tinvest import SyncClient
import time
import requests
from .models import Security
from tinvest.exceptions import TooManyRequestsError, UnexpectedError
from typing import Optional
from datetime import datetime
from dateutil.parser import parse
from .forms import SecurityFillInformationForm
from django.http.request import QueryDict


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
    save_securities(client, instrs)


def get_bonds():
    client = SyncClient(TINVEST_TOKEN)
    data = client.get_market_bonds()
    bonds = data.dict()
    instrs = bonds['payload']['instruments']
    save_securities(client, instrs)


def get_not_found_stock_on_market() -> Optional[Security]:
    return Security.objects.filter(not_found_on_market__exact=True).first()


def get_empty_dashboard_form_or_none(not_found_security: Security) -> Optional[SecurityFillInformationForm]:
    if not_found_security:
        return SecurityFillInformationForm(not_found_security)
    return None


def save_not_found_stock_if_valid(not_found_stock: Security, post: QueryDict):
    form_filling = SecurityFillInformationForm(not_found_stock, post)
    if form_filling.is_valid():
        not_found_stock.sector = form_filling.cleaned_data['sector']
        not_found_stock.country = form_filling.cleaned_data['country']
        not_found_stock.not_found_on_market = False
        not_found_stock.save()


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
        new_ticker = get_normalized_ticker(row['ticker'], row['currency'].value)
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
            print(count, '/', len_instr, '(' + str(new_ticker) + ')', 'market error.')
            print('ERROR:', e)
            continue
        if row['type'].value == 'Etf':
            sec_sector = 'ETF'
            not_found = True
        elif row['type'].value == 'Bond':
            sec_sector = 'BOND'
            not_found = True
        elif row['type'].value == 'Stock':
            sec_sector = None
            not_found = False
        else:
            sec_sector = None
            not_found = True
        try:
            sec = Security(
                ticker=new_ticker,
                name=row['name'],
                price=orderbook.payload.close_price,
                currency=row['currency'].value,
                sector=sec_sector,
                country=None,
                not_found_on_market=not_found
            )
            sec.save()
        except Exception as e:
            count += 1
            print(row)
            print(count, '/', len_instr, '(' + str(new_ticker) + ')', 'saving error.')
            print('ERROR:', e)
            continue
        count += 1
        print(count, '/', len_instr, '(' + str(new_ticker) + ')')


# TODO: add update Security price
def get_normalized_ticker(ticker: str, currency: str) -> str:
    # BRK.B -> BRK-B
    # LKOD@GS -> LKOD.IL
    # PUMA@DE -> PUMA.DE
    # MOEX -> MOEX.ME
    # SPB@US -> SPB
    if currency == 'USD':
        if '.' in ticker:
            return ticker.replace('.', '-')
        elif '@GS' in ticker:
            return ticker.replace('@GS', '.IL')
        elif '@US' in ticker:
            return ticker.replace('@US', '')
        return ticker
    elif currency == 'EUR':
        return ticker.replace('@', '.')
    elif currency == 'RUB':
        return str(ticker) + '.ME'


class StockNotFound(Exception):
    pass


def define_stock_sector_and_country():
    if not can_fill_stock_info():
        print('YAHOO API is over-requested today')
        return
    stocks = get_list_all_stocks_without_country_and_sector_and_not_found()
    if not stocks:
        print('Securities without sector and country are not exist')
        return
    for row in stocks:
        try:
            info = get_stock_info_or_error(ticker=row.ticker)
            country = info['country']
            sector = info['sector']
        except requests.ConnectionError as e:
            print(e)
            break
        except requests.HTTPError as e:
            print(e)
            break
        except StockNotFound as e:
            print(e)
            row.not_found_on_market = True
            row.save()
            continue
        except Exception as e:
            print(e)
            break

        row.sector = define_short_sector_name(sector)
        if row.currency == 'RUB':
            row.country = 'Russia'
        else:
            row.country = country
        row.save()
        print('Ticker:', '$' + str(row.ticker) + ',', 'country:', row.country, 'sector:', row.sector)

    update_fill_stock_date()


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
        raise StockNotFound(f'Ticker: ${ticker} Not found')
    asset_profile = data[0]['assetProfile']
    return {'country': asset_profile['country'], 'sector': asset_profile['sector']}


def get_list_all_stocks_without_country_and_sector_and_not_found() -> Optional[list[Security]]:
    return Security.objects.filter(country__isnull=True, sector__isnull=True, not_found_on_market__exact=False)


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

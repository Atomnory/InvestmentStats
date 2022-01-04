import time
import requests
from typing import Optional, List
from datetime import datetime
from dateutil.parser import parse
from decimal import Decimal

from django.http.request import QueryDict
from tinvest import SyncClient
from tinvest.exceptions import TooManyRequestsError, UnexpectedError
from tinvest.clients import MarketInstrumentListResponse

from config.settings import TINVEST_TOKEN, YAHOO_API_KEY, MEDIA_ROOT
from .models import Security
from .forms import SecurityFillInformationForm

# TODO: add Model LastUpdate for monthly updating Securities and daily updating YAHOO API using


def update_security_price(security: Security):
    new_price = get_security_price(security.figi)
    security.price = new_price
    security.save()


def get_security_price(figi: str) -> Decimal:
    client = SyncClient(TINVEST_TOKEN)
    order_book = client.get_market_orderbook(figi, 1)
    return order_book.payload.close_price


def save_tinvest_etfs():
    client = SyncClient(TINVEST_TOKEN)
    data = client.get_market_etfs()
    process_securities(data)


def save_tinvest_bonds():
    client = SyncClient(TINVEST_TOKEN)
    data = client.get_market_bonds()
    process_securities(data)


def save_tinvest_stocks():
    client = SyncClient(TINVEST_TOKEN)
    data = client.get_market_stocks()
    process_securities(data)


def get_not_found_stock() -> Optional[Security]:
    return Security.objects.filter(not_found_on_market__exact=True).first()


def get_empty_fill_info_form_or_none(not_found_security: Security) -> Optional[SecurityFillInformationForm]:
    if not_found_security:
        return SecurityFillInformationForm(not_found_security)
    return None


def save_not_found_stock_info(not_found_stock: Security, post: QueryDict):
    form_filling = SecurityFillInformationForm(not_found_stock, post)
    if form_filling.is_valid():
        not_found_stock.sector = form_filling.cleaned_data['sector']
        not_found_stock.country = form_filling.cleaned_data['country']
        not_found_stock.not_found_on_market = False
        not_found_stock.save()


def delete_not_found_stock_and_add_to_stop_list(not_found_stock: Security):
    add_to_stock_stop_list(not_found_stock.ticker)
    not_found_stock.delete()


def process_securities(data: MarketInstrumentListResponse):
    instruments = data.dict()['payload']['instruments']
    length = len(instruments) - 1
    existing_tickers = get_all_tickers()
    for i, row in enumerate(instruments):
        if i > 0 and i % 100 == 0:
            wait_60()

        security_type = row['type'].value
        currency = row['currency'].value
        figi = row['figi']
        new_ticker = define_ticker(row['ticker'], security_type, currency)

        if is_in_stop_list(new_ticker, security_type):
            print_process_securities_in_stop_list(i, length, new_ticker)
            continue
        elif new_ticker in existing_tickers:
            print_process_securities_exist(i, length, new_ticker)
            continue

        new_sector = define_sector(security_type)
        not_found = define_not_found(security_type)

        try:
            price = get_security_price(figi)
        except TooManyRequestsError as e:
            print_process_securities_error(row, i, length, new_ticker, e)
            wait_60()
            price = get_security_price(figi)
        except UnexpectedError as e:
            print_process_securities_error(row, i, length, new_ticker, e)
            continue

        try:
            save_security(new_ticker, figi, row['name'], price, currency, new_sector, None, not_found)
        except Exception as e:
            print_process_securities_error(row, i, length, new_ticker, e)
        else:
            print_process_securities_success(i, length, new_ticker)


def wait_60():
    time.sleep(60)


def is_in_stop_list(ticker: str, security_type: str) -> bool:
    stock_stop_list = get_stock_stop_list()
    if not stock_stop_list:
        return False
    if security_type == 'Stock':
        if ticker in stock_stop_list:
            return True
    return False


def get_all_tickers() -> List[str]:
    securities = Security.objects.all()
    tickers = []
    for row in securities:
        tickers.append(row.ticker)
    return tickers


def define_ticker(ticker: str, security_type: str, currency: str) -> str:
    if security_type == 'Stock':
        return get_normalized_stock_ticker(ticker, currency)
    return ticker


def define_sector(security_type: str) -> Optional[str]:
    if security_type == 'Etf':
        return 'ETF'
    elif security_type == 'Bond':
        return 'BOND'
    elif security_type == 'Stock':
        return None
    else:
        print('ERROR: undefined security_type:', security_type)
        return None


def define_not_found(security_type: str) -> bool:
    if security_type == 'Etf':
        return True
    elif security_type == 'Bond':
        return False
    elif security_type == 'Stock':
        return False
    else:
        return True


def get_normalized_stock_ticker(ticker: str, currency: str) -> str:
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


def save_security(ticker: str, figi: str, name: str, price: Decimal, currency: str, sector: Optional[str],
                  country: Optional[str], not_found: bool):
    sec = Security(
        ticker=ticker,
        figi=figi,
        name=name,
        price=price,
        currency=currency,
        sector=sector,
        country=country,
        not_found_on_market=not_found
    )
    sec.save()


def print_process_securities_error(row: dict, i: int, length: int, ticker: str, e: Exception):
    print(row)
    print(i, '/', length, '(' + str(ticker) + ')')
    print('ERROR:', e)


def print_process_securities_success(i: int, length: int, ticker: str):
    print(i, '/', length, '(' + str(ticker) + ')')


def print_process_securities_in_stop_list(i: int, length: int, ticker: str):
    print(i, '/', length, '(' + str(ticker) + ')', '- is in stop list. It will not be added.')


def print_process_securities_exist(i: int, length: int, ticker: str):
    print(i, '/', length, '(' + str(ticker) + ')', '- has added already.')


class StockNotFound(Exception):
    pass


def auto_define_stock_info():
    if was_yahoo_api_used_today():
        return
    stocks = get_list_stocks_without_info()
    if not stocks:
        print('Securities without sector and country are not exist')
        return
    process_stock_info(stocks)
    update_yahoo_api_using_date()


def process_stock_info(stocks: list[Security]):
    for row in stocks:
        try:
            info = get_stock_info_or_error(row.ticker)
        except StockNotFound as e:
            mark_security_as_not_found(row)
            print(e)
        except (requests.ConnectionError, requests.HTTPError, Exception) as e:
            print(e)
            break
        else:
            save_stock_info(row, info['sector'], info['country'])


def auto_define_bonds_info():
    bonds = get_bonds_without_info()
    if not bonds:
        print('Securities without sector and country are not exist')
        return
    process_bonds_info(bonds)


def get_bonds_without_info() -> Optional[list[Security]]:
    return Security.objects.filter(country__isnull=True, sector__exact='BOND', not_found_on_market__exact=False)


def process_bonds_info(bonds: list[Security]):
    for row in bonds:
        if row.currency == 'USD' or row.currency == 'EUR':
            mark_security_as_not_found(row)
        else:
            if 'Казахстан' in row.name:
                row.country = 'Kazakhstan'
            elif 'Беларусь' in row.name:
                row.country = 'Belarus'
            else:
                row.country = 'Russia'
        row.save()
        print_save_bond_success(row.ticker, row.country)


def print_save_bond_success(ticker: str, country: str):
    print('Ticker:', '$' + str(ticker) + ',', 'country:', str(country))


def mark_security_as_not_found(row: Security):
    row.not_found_on_market = True
    row.save()


def save_stock_info(row: Security, sector: str, country: str):
    row.sector = define_short_sector_name(sector)
    if row.sector is None:
        mark_security_as_not_found(row)
    if row.currency == 'RUB':
        row.country = 'Russia'
    else:
        row.country = country
    row.save()
    print_save_stock_success(row.ticker, row.sector, row.country)


def print_save_stock_success(ticker: str, sector: str, country: str):
    print('Ticker:', '$' + str(ticker) + ',', 'sector:', sector, 'country:', country)


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
    return unpack_stock_info(response, ticker)


def unpack_stock_info(response: requests.Response, ticker: str) -> dict:
    data = response.json()['quoteSummary']['result']
    if data is None:
        raise StockNotFound(f'Ticker: ${ticker} Not found')
    asset_profile = data[0]['assetProfile']
    return {'country': asset_profile['country'], 'sector': asset_profile['sector']}


def get_list_stocks_without_info() -> Optional[list[Security]]:
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


def was_yahoo_api_used_today() -> bool:
    try:
        with open(f'{MEDIA_ROOT}/fill_stock_date.txt', 'r') as f:
            text = f.readline()
    except FileNotFoundError:
        return False
    date = parse(text).date()
    today = datetime.utcnow().date()
    if date == today:
        print('YAHOO API is over-requested today')
        return True
    else:
        return False


def update_yahoo_api_using_date():
    today = datetime.utcnow().date()
    with open(f'{MEDIA_ROOT}/fill_stock_date.txt', 'w') as f:
        f.write(str(today))


def get_stock_stop_list() -> Optional[list[str]]:
    try:
        stocks = []
        with open(f'{MEDIA_ROOT}/stock_stop_list.txt', 'r') as f:
            for line in f.read().splitlines():
                stocks.append(line)
        return stocks
    except FileNotFoundError:
        return None


def add_to_stock_stop_list(ticker: str):
    with open(f'{MEDIA_ROOT}/stock_stop_list.txt', 'a') as f:
        print(ticker, file=f)

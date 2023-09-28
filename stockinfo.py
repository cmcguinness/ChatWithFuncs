"""
    stockinfo.py

    This is a very simplistic module to retrieve ticker symbols for stocks
    and market data for tickers.

    It uses Twelvedata.com as a provider, and you can sign up for a free
    account with them at https://twelvedata.com/pricing (scroll down for free)
    Once you have an account, make sure to set your TWELVE_API_KEY environment
    variable with the api key they give you.

    Author: Charles McGuinness
    License: MIT License

"""
import os
import requests
import json

twelve_api_key = os.getenv('TWELVE_API_KEY')


#   Interface to their API.  Very easy to use
def _call_twelve(func:str, query: str, value: str) -> dict:
    headers = {'Authorization' : f'apikey {twelve_api_key}'}
    call_results = requests.get(f'https://api.twelvedata.com/{func}?{query}={value}', headers=headers)
    return json.loads(call_results.content)

#   Takes a dictionary (which is a row of data in a sense) and
#   do a simple converstion into a formatted string
def pretty_print(row:dict) -> str:
    results = []
    for key in row:
        results.append(f'{key}: {row[key]}')

    return ', '.join(results)


#   Given a ticker symbol, retrieve a quote
def get_quote(ticker: str, return_form='str'):
    data_json = _call_twelve('quote', 'symbol', ticker)

    if return_form == 'json':
        return data_json

    return pretty_print(data_json)


# Given a company name, find a matching ticker symbol.
# Note a complication: multiple exchanges will list a company,
# and we want the primary exchange.
def lookup_ticker(name, return_form='str'):
    search_json = _call_twelve('symbol_search', 'symbol', name)

    # This retrieves a bunch of exchanges, but for demo purposes we only are interested in these two
    exchanges = ['NYSE', 'NASDAQ']

    for exchange_listing in search_json['data']:
        if exchange_listing['exchange'] in exchanges:
            if return_form == 'json':
                return exchange_listing

            return pretty_print(exchange_listing)

    return None


#
#   This code is used as a standalone test of this module, and
#   is just validating that the two calls work but not stress testing them
#
if __name__ == '__main__':
    sfdc = lookup_ticker('Salesforce', return_form='json')
    if sfdc['symbol'] != 'CRM':
        print('Bad symbol retrieved for Salesforce!')

    crm = get_quote('CRM', return_form='json')
    if 'close' not in crm:
        print('Close not in data for CRM')

    print('Test finished.')
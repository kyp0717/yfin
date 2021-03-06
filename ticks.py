# -*- coding: utf-8 -*-
"""
* Pizza delivery prompt example
* run example by writing `python example/pizza.py` in your console
"""
from __future__ import print_function, unicode_literals

#long to wide using pivot

import regex
import common
from common import *

def SelectAction(actions):
    act_list = actions.keys()
    act_prompt = [
        {
            'type': 'list',
            'name': 'action',
            'message': 'Select Action?',
            'choices': act_list
        } ]
    answer = prompt(act_prompt)
    return actions[answer['action']]()

def SearchTickers(exchanges, company, sector=None, industry=None, tickers=None):
    """
    Find tickers for company in nasdaq, amex, or nyse\n
    """
    #print('searching for tickers in {}'.format(exchanges))
    dat = common.company_data.GetData(exchanges)

    if tickers:
        dat = dat[dat.Symbol.isin(tickers)]

    if sector:
        if type(sector) == str:
            dat = dat[dat['Sector'].str.contains(FilterToRegex(sector), na=False, case=False) ]
        else:
            dat = dat[dat['Sector'].isin(sector) ]

    if industry: # filter by string or list
        if type(industry) == str:
            dat = dat[dat['industry'].str.contains(FilterToRegex(industry), na=False, case=False) ]
        else:
            dat = dat[dat['industry'].isin(industry) ]

    dat = dat[dat['Name'].str.contains(FilterToRegex(company), na=False, case=False) ]
    if len(dat) < 1:
        print('No results for {} found'.format(company))
        return
    lines = dat.to_string(index=False).split('\n')

    ticker_lines = []
    ticker_list = []
    for line in lines[1:]:
        ticker_lines.append({'name': line})
        ticker_list.append(line.split()[0].strip())
    prompt_dict = {
        'type': 'checkbox',
        'qmark': '>',
        'message': 'Select Tickers',
        'name': 'tickers',
        'choices': ticker_lines }

    print('{} items containing "{}" found'.format(
            len(dat), company ))
    print(lines[0])
    results = prompt(prompt_dict)['tickers']
    tickers = [ r.split()[0].strip() for r in results ]
    inverse = prompt( {
        'type': 'list',
        'name': 'inverse',
        'message': 'Add Items',
        'choices': [
            'Add {} Selected'.format(len(results)),
            'Add {} Unselected'.format(len(ticker_list) - len(results)),
            'Add None']
        })['inverse']
    if 'Unselected' in inverse:
        tickers = [ t for t in ticker_list if t not in tickers]
    elif 'None' in inverse:
        tickers = []
    return tickers

def AddTickers():
    exchanges = exchange_source_dict 

    exchange_list = []
    for item in exchanges.keys():
        exchange_list.append({'name': item})

    questions = [
        {
            'type': 'checkbox',
            'qmark': '>',
            'message': 'Exchanges to search',
            'name': 'exchanges',
            'choices': exchange_list, },
        {
            'type': 'input',
            'name': 'company',
            'message': 'Company search string'},
        {
            'type': 'input',
            'name': 'sector',
            'message': 'Sector search string'},
        {
            'type': 'input',
            'name': 'industry',
            'message': 'Industry search string'} ]
    results = prompt(questions)

    if len(results['exchanges']) < 1:
        results['exchanges'] = exchanges # select all if none

    tickers = SearchTickers(
        results['exchanges'], results['company'],
        results['sector'], results['industry'])

    ticker_data.Add(tickers)
    return True

def GetCompanyList(tickers):
    ti.Add('getting company list')
    exchanges = exchange_source_dict
    dat = pd.concat(map(pd.read_csv, exchanges.values()))
    ti.Add('csv retrieved')
    dat = dat.filter(items=['Symbol', 'Name'])

    dat.set_index('Symbol', inplace=True)
    return dat.loc[tickers]

def RemoveTickers():
    choice = ticker_data.get_name(False)
    tickers = ticker_data[choice]
    df = company_data.GetNames(tickers)
    lines = df.to_string(index=True).split('\n')

    ticker_lines = []
    ticker_list = []
    for line in lines[2:]:
        ticker_lines.append({'name': line})
        ticker_list.append(line.split()[0].strip())
    prompt_dict = {
        'type': 'checkbox',
        'qmark': '>',
        'message': 'Select Tickers',
        'name': 'tickers',
        'choices': ticker_lines }
    results = prompt(prompt_dict)['tickers']
    tickers = [r.split()[0] for r in results]

    inverse = prompt( {
        'type': 'list',
        'name': 'inverse',
        'message': 'Remove Items',
        'choices': [
            'Remove {} Selected'.format(len(tickers)),
            'Remove {} Unselected'.format(len(ticker_list) - len(results)),
            'Remove None']
        })['inverse']
    if 'Unselected' in inverse:
        tickers = [ t for t in ticker_list if t not in tickers]
    elif 'None' in inverse:
        tickers = []
    ticker_data.Filter(choice, tickers)
    return True

def RemoveList():
    choice = ticker_data.get_name(False)
    confirmation = {
        'type': 'confirm',
        'message': 'Really remove {}?'.format(choice),
        'name': 'yes',
        'default': True }
    if prompt(confirmation)['yes']:
        del ticker_data.ticker_lists[choice]
    return True

def PickTickers(columns=None, times=None, limit=True):
    max_columns = term.width // 30
    max_rows = term.height - 5
    max_items = max_columns * max_rows
    wanted_rows = int(term.height * .66)

    tickers = ticker_data[ticker_data.get_name(False)]
    if times:
        tickers = tickers * times
    
    if not columns:
        if limit:
            tickers = tickers[:max_items]
        columns = min(max_columns, len(tickers) // wanted_rows + 1)
    return tickers, columns, max_items

def WatchTickers(tickers = None, columns=None, delay=60, times=None):
    'Watch multiple tickers updated regularly'
    import stock_info as yfs
    import time
    tickers, columns, max_fit = PickTickers(columns, times, limit=True)

    with term.fullscreen():
        while True:
            print('updating')
            start_time = time.time()
            results = yfs.get_all_prices(tickers)
            outp = []
            for ticker, price, volume in results:
                outp.append('{:6s}: {}'.format(ticker, price))
            ti = time.strftime("%H:%M:%S", time.gmtime())
            print(term.clear() + 'YFIN watching {} tickers: {}'.format(len(tickers), ti))
            print('Press CTRL-C to exit\n')
            print_wide_list(outp, columns)
            end_time = time.time()
            poll = end_time - start_time
            pause = delay - int(poll)
            print('polled in {:.3f}: sleeping {}'.format(
                poll * 1000, pause) )
            if pause > 0:
                try:
                    time.sleep(pause)
                except KeyboardInterrupt:
                    break
    return True

def BrowseIndustry():
    exchanges = exchange_source_dict 
    exchange_list = []
    for item in exchanges.keys():
        exchange_list.append({'name': item})

    question = [
        {
            'type': 'input',
            'name': 'industry',
            'message': 'Industry search string'} ]

    results = prompt(question)
    filt = FilterToRegex(results['industry'])

    df = company_data()
    df = df[df.industry.str.contains(filt, na=False, case=False) ]
    industries = sorted(df.industry.dropna().unique())

    industry_list = []
    for item in industries:
        industry_list.append({'name': item})

    question = [
        {
            'type': 'checkbox',
            'qmark': '>',
            'message': 'Industries to search',
            'name': 'industry',
            'choices': industry_list },
        {
            'type': 'checkbox',
            'qmark': '>',
            'message': 'Exchanges to search',
            'name': 'exchange',
            'choices': exchange_list },
        {
            'type': 'input',
            'name': 'company',
            'message': 'Company search string'} ]

    results = prompt(question)
    exchanges = results['exchange'] or exchanges.keys()
    companies = results['company']
    industries = results['industry']
    tickers = SearchTickers(exchanges, companies, '', industries )
    return True

def ProcessTickers(tickers = None, delay=60):
    'Watch multiple tickers updated regularly'
    import stock_info as yfs
    import time
    tickers, columns, max_fit = PickTickers(limit=False)
    df = pd.DataFrame(columns=[
            'timepoint',
            'ticker',
            'price',
            'volume' ] )
    first_time = None

    # display price data until user cancels
    with term.fullscreen():
        while True:
            print('updating')
            start_time = time.time()
            if not first_time:
                first_time = start_time
            results = yfs.get_all_prices(tickers)
            timepoint = int(start_time - first_time)

            ostr = []
            additions = []
            for ticker, price, volume in results:
                additions.append({
                    'timepoint': timepoint,
                    'ticker': ticker,
                    'price': price,
                    'volume': volume})
                ostr.append('{:6s}: {}'.format(ticker, price))

            df = df.append(additions)
            end_time = time.time()
            tstr = time.strftime("%H:%M:%S", time.gmtime(end_time))
            print(term.clear() + 'YFIN processing {} tickers: {}'.format(len(tickers), tstr))
            print('Press CTRL-C to exit\n')
            print_wide_list(ostr[:max_fit], columns)
            pause = delay - int(end_time - start_time)
            print('polled in {:.3f}: sleeping {}'.format(
                (end_time - start_time) * 1000, pause) )
            if pause > 0:
                try:
                    time.sleep(pause)
                except KeyboardInterrupt:
                    break
    df.to_pickle('dataframe')
    ProcessTickerData(df)
    return True
        
def ProcessTickerData(df):
    prices = Regress(df, 'price')
    volume = Regress(df, 'volume')

    # display summary
    print('\nPRICES')
    print(prices)
    print(f'Stat Average for {prices.shape[1]} tickers')
    averages = prices.iloc[-4:].mean(axis=1)
    print(averages.to_string(header=False))

    print()
    print('\nVOLUME')
    print(volume)
    print(f'Stat Average for {prices.shape[1]} tickers')
    averages = volume.iloc[-4:].mean(axis=1)
    print(averages.to_string(header=False))

    return prices, volume

def Regress(dataframe, pivotpoint):
    from numpy import float32
    df = dataframe.pivot(
        index = 'timepoint',
        columns = 'ticker',
        values = pivotpoint)

    timepoints = df.index.values
    changes = {}
    slopes = {}
    rvalues = {}
    pvalues = {}
    stderrs = {}

    for p in df:
        results = stats.linregress(timepoints, df[p].astype(float32))
        start = df.at[timepoints[0], p]
        end = df.at[timepoints[-1], p]

        changes[p] = end - start   
        slopes[p] = results.slope
        rvalues[p] = results.rvalue
        pvalues[p] = results.pvalue
        stderrs[p] = results.stderr
    df.loc['change'] = changes
    df.loc['slope'] = slopes
    df.loc['rval'] = rvalues
    df.loc['pval'] = pvalues
    df.loc['sterr'] = stderrs
    return df

def BrowseSector():
    exchanges = exchange_source_dict 
    exchange_list = []
    for item in exchanges.keys():
        exchange_list.append({'name': item})

    df = company_data()
    sectors = sorted(df.Sector.dropna().unique())

    sector_list = []
    for item in sectors:
        sector_list.append({'name': item})

    question = [
        {
            'type': 'checkbox',
            'qmark': '>',
            'message': 'Sectors to search',
            'name': 'sectors',
            'choices': sector_list },
        {
            'type': 'checkbox',
            'qmark': '>',
            'message': 'Exchanges to search',
            'name': 'exchange',
            'choices': exchange_list },
        {
            'type': 'input',
            'name': 'company',
            'message': 'Company search string'} ]

    results = prompt(question)
    exchanges = results['exchange'] or exchanges.keys()
    companies = results['company']
    sectors = results['sectors']
    tickers = SearchTickers(exchanges, companies, sectors, '' )
    return True

def BrowseIndex():
    import stock_info as yfs
    index = {
            'dow': yfs.tickers_dow,
            'nasdaq': yfs.tickers_nasdaq,
            'sp500': yfs.tickers_sp500 }

    question = [
        {
            'type': 'list',
            'qmark': '>',
            'message': 'Index to Search',
            'name': 'index',
            'choices': index.keys() },
        {
            'type': 'input',
            'name': 'company',
            'message': 'Company search string'},
        {
            'type': 'input',
            'name': 'sector',
            'message': 'Sector search string'},
        {
            'type': 'input',
            'name': 'industry',
            'message': 'Industry search string'} ]

    results = prompt(question)
    tickers = index[results['index']]()

    tickers = SearchTickers(
            None,
            results['company'],
            results['sector'],
            results['industry'],
            tickers)
    ticker_data.Add(tickers)
    return True


def FilterToRegex(filt):
    if filt:
        if filt.endswith('.'):
            filt = '^' + filt[:-1]
        elif filt.startswith('.'):
            filt = filt[1:] + '$'
    return filt

def print_wide_list(l, columns=3, pager=False):
    
    height = len(l) // columns
    width = term.width // columns
    if len(l) > height * columns:
        height += 1
        l += [''] * (height * columns - len(l))

    if pager:
        lines = ''
        for row in range(height):
            for col in range(columns):
                item = l[int(row + col * (height))]
                lines += item + ' ' * (width - len(item))
            lines += '\n'
        click.echo_via_pager(lines)
    else:
        for row in range(height):
            line = ''
            for col in range(columns):
                item = l[int(row + col * (height))]
                line += item + ' ' * (width - len(item))
            print(line)


def dummy():
    print('in dummy')
    return True
def exit():
    print('exiting')
    ticker_data.Save()
    return False

actions = {
    'Add Tickers': AddTickers,
    'Browse Index': BrowseIndex,
    'Browse Industry': BrowseIndustry,
    'Browse Sector': BrowseSector,
    'Process Tickers': ProcessTickers,
    'Remove List': RemoveList,
    'Remove Tickers': RemoveTickers,
    'Watch Tickers': WatchTickers,
    'Exit': exit }

def main():
    while SelectAction(actions):
        pass

if __name__ == '__main__':
    print('Stock Search and Query by Christopher M Palmieri')
    ticker_data = TickerData()
    company_data = CompanyData()
    ti = time_it()
    main()


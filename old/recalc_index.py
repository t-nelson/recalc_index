#!/usr/bin/env python

import coinmarketcap
import poloniex
import sys
import socket
import urllib2

polo_key            = ''
polo_secret         = ''
blacklist           = [u'BTC'] #u'BCH']
dont_trade          = [] #u'ZEC', u'STR']
market_count        = 10
debug               = (1 == 0)
web_query_timeout   = 3 # seconds
web_query_retries   = 3
minimum_trade       = 0.00010000 # BTC
rebalance_pct       = 2.5 # %
base_currency       = u'BTC'
symbol_remap        = {
    #   CMC         POLO
        u'XLM'  :   u'STR',
}

if debug:
    sys.stderr.write("DEBUG enabled. Using local data!\n")

class IndexEntry(object):
    def __init__(self, symbol, balance=None, index_pct=0.0):
        self._trade_btc
        self.symbol         = symbol
        self.index_pct      = index_pct
        self.balance        = 0.0
        self.balance_btc    = 0.0
        self.trade_btc      = 0.0
        if balance:
            self.balance        = balance.balance
            self.balance_btc    = balance.btc_value

socket.setdefaulttimeout(web_query_timeout)

cmc     = coinmarketcap.coinmarketcap(debug=debug)
polo    = poloniex.poloniex(polo_key, polo_secret, debug=debug)

# Make web queries
retries = web_query_retries
while retries > 0:
    try:
        print "Getting market caps (coinmarketcap.com)"
        mkt_caps    = cmc.getMarkets(250)
        print "Getting price ticker (poloniex.com)"
        mkts        = polo.getTicker()
        print "Getting balances (poloniex.com)"
        balances    = polo.getBalances()
        break
    except (socket.timeout, urllib2.URLError):
        print "Timeout!"
        retries -= 1

if retries == 0:
    print "Web queries failed!"
    sys.exit(1)

# Calculate total BTC value of balances
index_btc   = 0.0
for symbol, balance in balances.iteritems():
    if symbol in dont_trade:
        continue
    index_btc   += balance.btc_value

# Initialize index with balances
index = {}
for symbol, balance in balances.iteritems():
    index[symbol]               = {}
    index[symbol][u'cur_pct']   = balance.btc_value / index_btc
    index[symbol][u'cur_bal']   = balance
    index[symbol][u'new_pct']   = 0.0

# Determine top currencies by market capitalization
top_markets         = []
new_idx_mkt_cap_usd = 0.0
btc_mkts            = mkts[base_currency]
polo_pos            = 1
balance_mkts        = balances.keys()
n_mkt_balances      = len(balance_mkts)
n_top_markets       = 0
for mkt in mkt_caps:
    symbol = symbol_remap.get(mkt.symbol, mkt.symbol)
    if symbol in btc_mkts or symbol == base_currency:
        if not symbol in blacklist:
            #print symbol, len(top_markets), n_mkt_balances
            if not symbol in dont_trade:
                new_idx_mkt_cap_usd += mkt.mkt_cap_usd
            if len(top_markets) < market_count:
                top_markets.append((mkt, False))
            elif n_mkt_balances > 0:
                if symbol in balance_mkts:
                    top_markets.append((mkt, True))
            else:
                break
            if symbol in balance_mkts:
                n_mkt_balances -= 1

# Update index with current distribution, by market cap
for top_mkt in top_markets:
    mkt = top_mkt[0]
    sell_all = top_mkt[1]
    if mkt.symbol in dont_trade:
        continue
    while True:
        try:
            if sell_all:
                index[mkt.symbol][u'new_pct']   = 0.0
            else:
                index[mkt.symbol][u'new_pct']   = mkt.mkt_cap_usd / new_idx_mkt_cap_usd
            index[mkt.symbol][u'mkt_cap_pos']   = mkt.rank
            break
        except:
            # New currency enters the index
            index[mkt.symbol]               = {}
            index[mkt.symbol][u'cur_pct']   = 0.0
            index[mkt.symbol][u'cur_bal']   = poloniex.poloniex.balance()

# Calculate differences from balance to current market conditions
sells       = []
buys        = []
base_data    = None
total_trade_pct = 0.0
for sym, data in index.iteritems():
    if sym in dont_trade:
        continue
    cur_pct = data[u'cur_pct']
    new_pct = data[u'new_pct']
    delta   = new_pct - cur_pct
    data[u'delta_pct']  = delta
    total_trade_pct += abs(delta)
    if delta < 0.0:
        data[u'trade_pct']  = -delta
        trade_btc           = -round(delta * index_btc, 8)
        data[u'trade_btc']  = trade_btc
        data[u'trade_working_btc']  = data[u'trade_btc']
        if trade_btc >= minimum_trade:
            sells.append((sym, data))
    elif delta > 0.0:
        data[u'trade_pct']  = delta
        trade_btc           = round(delta * index_btc, 8)
        data[u'trade_btc']  = trade_btc
        data[u'trade_working_btc']  = data[u'trade_btc']
        if trade_btc >= minimum_trade:
            buys.append((sym, data))
    else:
        data[u'trade_pct']  = 0.0
        data[u'trade_btc']  = round(delta * index_btc, 8)
        data[u'trade_working_btc']  = data[u'trade_btc']

    if sym == base_currency:
        base_data    = data

# Sorting high to low ensures a minimal trade count
buys.sort(key=lambda b : -b[1][u'trade_working_btc'])
sells.sort(key=lambda s : -s[1][u'trade_working_btc'])

if 0 == 1:
    print "buys"
    for b in buys:
        print b
    print "sells"
    for s in sells:
        print s

if 0 == 0:
    ignore_headers  =   [
                            #u'trade_working_btc',
                            u'cur_bal'
                        ]
    headers = index[base_currency].keys()
    print "%11s  %5s  " % (u'Index', u'Coin'),
    for header in headers:
        if header in ignore_headers:
            continue
        print "%-11s  " % (header),
    print
    #sells.sort(key=lambda s : -s[1][u'trade_btc'])
    index_pos   = 1
    idx_list    = [(s, d) for s, d in index.iteritems()]
    idx_list.sort(key=lambda i : -i[1][u'new_pct'])
    for sym, data in idx_list:
        print "%11d  %5s  " % (index_pos, sym),
        index_pos   += 1
        keys = data.keys()
        for key in keys:
            if key in ignore_headers:
                continue
            #Coin cur_pct     new_pct     trade_btc   trade_pct   delta_pct
            if key.endswith(u'_pct'):
                print "%10.3f%%  " % (100.0 * data[key]),
            elif key.endswith(u'_btc'):
                print "%11.8f  " % (data[key]),
            elif key.endswith(u'_pos'):
                print "%11d  " % (data[key]),
            else:
                print "%11.8f  " % data[key] if isinstance(data[key], float) else data[key],

        print ''

# Determine necessary sell trades to synchronize balances to
# the market
trades  = []
for sell, sell_data in sells:
    if sell in dont_trade:
        continue
    sell_amount_btc = sell_data[u'trade_working_btc']
    while sell_amount_btc > 0.0:
        for buy, buy_data in buys:
            swap    = False
            # Find the appropriate market
            try:
                market  = mkts[sell][buy]
            except:
                # A market may exist with buy and sell swapped
                try:
                    #print "swap %s %s" % (buy, sell)
                    market      = mkts[buy][sell]
                    tmp         = buy
                    buy         = sell
                    sell        = tmp
                    tmp         = buy_data
                    buy_data    = sell_data
                    sell_data   = tmp
                    swap        = True
                except:
                    continue
            # Get the conversion rate from BTC to our market currency
            try:
                convert_from_btc    = mkts[base_currency][sell].last_price
            except:
                # The only currency that doesn't exist in in the BTC
                # market is BTC itself
                convert_from_btc    = 1.0

            # Calculate the amount to trade
            trade_btc               = min(sell_amount_btc, buy_data[u'trade_working_btc'])
            if trade_btc > 0.0:
                trade_amount            = round(trade_btc / convert_from_btc, 8)
                sell_amount_btc         -= trade_btc

                trade = (sell, buy, trade_amount, trade_btc, 'SELL' if swap else 'BUY')
                print trade, swap
                #print trade
                trades.append(trade)

                # Unswap our variables if necessary to ensure bookkeeping
                # is consistent
                if swap:
                    tmp         = sell
                    sell        = buy
                    buy         = tmp
                    tmp         = sell_data
                    sell_data   = buy_data
                    buy_data    = tmp

                buy_data[u'trade_working_btc']  -= trade_btc
                sell_data[u'trade_working_btc'] = sell_amount_btc

            if not sell_amount_btc > 0.0:
                break

        if sell_amount_btc > 0.0:
            if sell == base_currency:
                break
            trade_btc               = sell_amount_btc
            sell_amount_btc         -= trade_btc
            #print "fallback", base_currency, sell
            trade = (base_currency, sell, trade_btc, trade_btc, 'SELL')
            #print trade
            trades.append(trade)
            base_data[u'trade_working_btc']  -= trade_btc
            sell_data[u'trade_working_btc'] = sell_amount_btc


# Determine necessary buy trades to synchronize balances to
# the market.  There should only be BTC to sell at this point.
sell        = base_currency
sell_data   = base_data
for buy, buy_data in buys:
    if buy in dont_trade:
        continue
    try:
        market  = mkts[sell][buy]
        trade_btc               = buy_data[u'trade_working_btc']
        if trade_btc > 0.0:
            trade_amount            = trade_btc
            trade = (sell, buy, trade_amount, trade_btc, 'BUY')
            #print trade
            trades.append(trade)
            sell_data[u'trade_working_btc'] += trade_btc
            buy_data[u'trade_working_btc']  -= trade_btc
    except:
        # Don't trade BTC for BTC...
        continue

for trade in trades:
    #if trade[3] >= minimum_trade:
    print "%-9s  %-4s  %11.8f %-4s  %11.8f BTC" % ("%s_%s" % (trade[0], trade[1]), trade[4], trade[2], trade[0], trade[3])

usdt_price  = None
try:
    usdt        = mkts[u'USDT'][base_currency]
    usdt_price  = usdt.last_price
except:
    pass

btc_total       = 0.0
usd_total       = 0.0
if True:
    ignore_headers  =   [
                            #u'trade_working_btc',
                            u'cur_bal'
                        ]
    headers = index[base_currency].keys()
    print "%11s  %5s  " % (u'Index', u'Coin'),
    for header in headers:
        if header in ignore_headers:
            continue
        print "%-11s  " % (header),
    print
    #sells.sort(key=lambda s : -s[1][u'trade_btc'])
    index_pos   = 1
    idx_list    = [(s, d) for s, d in index.iteritems()]
    idx_list.sort(key=lambda i : -i[1][u'new_pct'])
    for sym, data in idx_list:
        print "%11d  %5s  " % (index_pos, sym),
        index_pos   += 1
        btc_total   += data[u'trade_btc']
        usd_total   += usdt_price * btc_total
        keys = data.keys()
        for key in keys:
            if key in ignore_headers:
                continue
            #Coin cur_pct     new_pct     trade_btc   trade_pct   delta_pct
            if key.endswith(u'_pct'):
                print "%10.3f%%  " % (100.0 * data[key]),
            elif key.endswith(u'_btc'):
                print "%11.8f  " % (data[key]),
            elif key.endswith(u'_pos'):
                print "%11d  " % (data[key]),
            else:
                print "%11.8f  " % data[key] if isinstance(data[key], float) else data[key],

        print ''

    print "%11s  %5s  " % (u'', u''),
    for key in data.keys():
        if key in ignore_headers:
            continue
        if (key == u'trade_btc'):
            print "%11.8f  (%.2f USDT)" % (btc_total, usd_total)
            break
        else:
            print "%11s  " % (u''),

trade_pct = 100.0 * total_trade_pct / 2.0
if (trade_pct > rebalance_pct):
    print "Time to rebalance"
else:
    print "Rebalance in %.3f%%" % (rebalance_pct - trade_pct)

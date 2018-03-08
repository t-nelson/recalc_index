#!/usr/bin/env python

import coinmarketcap
import poloniex
import sys
import socket
import urllib2
import copy

######## Config #########
polo_key            = ''
polo_secret         = ''
market_count        = 10
blacklist           = [] # u'BTC', u'XRP' ] 
debug               = (1 == 0)
web_query_timeout   = 3 # seconds
web_query_retries   = 3
base_currency       = u'BTC'
symbol_remap        = {
    #   CMC         Polo
        u'XLM'  :   u'STR',
}
###### Config end #######

class IndexBalance(object):
    def __init__(self, polo_bal):
        self.bal    = polo_bal.balance
        self.btc    = polo_bal.btc_value
        self.pct    = 0.0

    def __repr__(self):
        return "bal: %13.8f, btc: %.8f, pct: %6.3f%%" % (self.bal, self.btc, 100.0 * self.pct)

class Index(object):
    def __init__(self, polo_bals):
        self.assets     = {}
        self.btc_tot    = 0.0
        for c, bal in polo_bals.iteritems():
            self.assets[c]  =   IndexBalance(bal)
            self.btc_tot    +=  self.assets[c].btc
        for c, ib in self.assets.iteritems():
            ib.pct  = ib.btc / self.btc_tot

    def __repr__(self):
        s = ""
        for c, ib in sorted(self.assets.items(), key=lambda i : -i[1].pct):
            s += "%5s - %r\n" % (c, ib)
        return s + "Total: %.8f BTC" % (self.btc_tot)

    def __contains__(self, key):
        return key in self.assets

    def __len__(self):
        return len(self.assets)

    def items(self):
        return self.assets.items()

    def iteritems(self):
        return self.assets.iteritems()

    def get(self, sym):
        return self.assets.get(sym, None)

class TopMarket(object):
    def __init__(self, mkt_data):
        self.rank       =   mkt_data.rank
        self.cap        =   int(mkt_data.mkt_cap_usd)
        self.pct        =   0.0
        self.purge      =   False
    def __repr__(self):
        return "rank: %2d, cap: %13dUSD, pct: %6.3f%%, purge: %r" % (self.rank, self.cap, 100.0 * self.pct, self.purge)

class TopMarkets(object):
    def __init__(self, mkt_caps, base_currency, base_mkts, polo_mkts, idx):
        self.top_mkts       = {}
        self.top_mkts_tot   = 0.0

        nbals           = len(idx)
        top_mkts_tot    = 0.0
        purge_cnt       = 0
        for mkt_data in mkt_caps:
            sym = symbol_remap.get(mkt_data.symbol, mkt_data.symbol)
            if nbals > 0 or (len(self.top_mkts) - purge_cnt) < market_count:
                if sym in base_mkts or sym == base_currency:
                    purge               = False
                    add                 = False
                    blacklisted         = sym in blacklist

                    if sym in idx:
                        nbals   -=  1
                        add     =   True
                        if blacklisted:
                            purge = True
                        elif (len(self.top_mkts) - purge_cnt) >= market_count:
                            purge = True
                    elif not blacklisted and ((len(self.top_mkts) - purge_cnt) < market_count):
                        add = True

                    if add:
                        self.top_mkts[sym]  = TopMarket(mkt_data)
                        if purge:
                            self.top_mkts[sym].purge = True
                            purge_cnt += 1

                        if not self.top_mkts[sym].purge:
                            self.top_mkts_tot +=  mkt_data.mkt_cap_usd
            else:
                break
        for c, tm in self.top_mkts.iteritems():
            if not tm.purge:
                tm.pct  = tm.cap / self.top_mkts_tot

    def __repr__(self):
        s = ""
        i = 1
        for sym,data in sorted(self.top_mkts.items(), key=lambda tm : tm[1].rank):
            s += "%2s: %5s - %r\n" % ("--" if data.purge else "%2d" % (i), sym, data)
            if not data.purge:
                i += 1
        return s + "Total: %d USD" % (self.top_mkts_tot)

    def items(self):
        return self.top_mkts.items()

    def iteritems(self):
        return self.top_mkts.iteritems()

    def get(self, sym):
        return self.top_mkts.get(sym, None)

if debug:
    sys.stderr.write("DEBUG enabled. Using local data!\n")

socket.setdefaulttimeout(web_query_timeout)

cmc     = coinmarketcap.coinmarketcap(debug=debug)
polo    = poloniex.poloniex(polo_key, polo_secret, debug=debug)

# Make web queries
retries = web_query_retries
while retries > 0:
    try:
        print "Getting market caps (coinmarketcap.com)"
        mkt_caps    = cmc.getMarkets(max(20, market_count * 10))
        print "Getting price ticker (poloniex.com)"
        polo_mkts   = polo.getTicker()
        print "Getting balances (poloniex.com)"
        polo_bals   = polo.getBalances()
        break
    except (socket.timeout, urllib2.URLError, ssl.SSLError):
        print "Timeout!"
        retries -= 1

if retries == 0:
    print "Web queries failed!"
    sys.exit(1)

idx         = Index(polo_bals)
base_mkts   = polo_mkts[base_currency]
top_mkts    = TopMarkets(mkt_caps, base_currency, base_mkts, polo_mkts, idx)

#print idx
#print top_mkts

# Determine trades needed to balance the index
buy_trade_amts  = {}
sell_trade_amts = {}
buy_tot     = 0.0
sell_tot    = 0.0
buy_pct     = 0.0
sell_pct    = 0.0
for c, tm in top_mkts.iteritems():
    cur_pct = 0.0

    bal = idx.get(c)
    if not bal == None:
        cur_pct = bal.pct

    trade_pct       = (tm.pct - cur_pct)
    trade_amount    = round(trade_pct * idx.btc_tot, 8)

    if trade_amount < 0.0:
        sell_trade_amts[c]  = -trade_amount
        sell_tot -= trade_amount
        sell_pct -= trade_pct
    else:
        buy_trade_amts[c]   = trade_amount
        buy_tot += trade_amount
        buy_pct += trade_pct

#print "buy_pct(%6.3f) sell_pct(%6.3f)" % (buy_pct * 100.0, sell_pct * 100.0)

# Match trades
i           = 0
actions     = [ "BUY", "SELL" ]
did_trade   = True
trade_tot   = 0.0
while did_trade:
    did_trade = False
    new_sell_trade_amts = {}
    for sell, sell_amt in sorted(sell_trade_amts.items(), key=lambda k : -k[1]):
        sell_amt = sell_trade_amts.get(sell, 0.0)
        for buy, buy_amt in sorted(buy_trade_amts.items(), key=lambda k : -k[1]):
            if not sell == buy:
                buy_amt     = buy_trade_amts.get(buy, 0.0)
                trade_amt   = min(sell_amt, buy_amt)

                if trade_amt > 0.0:
                    sell_mkts   = polo_mkts.get(sell, None)
                    buy_mkts    = polo_mkts.get(buy, None)
                    mkts        = None
                    mkt_data    = None
                    if not sell_mkts == None:
                        mkt         = sell
                        mkts        = sell_mkts
                        mkt_data    = mkts.get(buy, None)
                        coin_pair   = "%s_%s" % (sell, buy)
                        action      = actions[i % 2]
                    elif not buy_mkts == None:
                        mkt         = buy
                        mkts        = buy_mkts
                        mkt_data    = mkts.get(sell, None)
                        coin_pair   = "%s_%s" % (buy, sell)
                        action      = actions[(i+1) % 2]

                    if not mkt_data == None:
                        sell_amt    =   round(sell_amt - trade_amt, 8)
                        buy_amt     =   round(buy_amt - trade_amt, 8)
                        base_conv   =   1.0
                        base_mkt    =   base_mkts.get(mkt, None)

                        if not base_mkt == None:
                            base_conv = base_mkt.last_price

                        trade   = round(trade_amt / base_conv, 8)

                        print "%-5s in %-11s %.8f %s  [%.8f %s]" % (action, coin_pair, trade, mkt, trade_amt, base_currency)
                        trade_tot += trade_amt if action == "BUY" else -trade_amt

                        did_trade = True

                        sell_trade_amts[sell] = sell_amt
                        
                        if buy_amt > 0.0:
                            buy_trade_amts[buy] = buy_amt
                        else:
                            if buy_amt < 0.0:
                                sell_val    =   sell_trade_amts.get(buy, 0.0)
                                sell_val    -=  buy_amt
                                sell_trade_amts[buy] = sell_val
                                buy_amt     = 0.0
                            del buy_trade_amts[buy]
                        
                        if not sell_amt > 0.0:
                            break

        # Trade remainder in base market
        if sell_amt > 0.0 and not sell == base_currency:
            buy         =   base_currency
            mkt         =   base_currency
            buy_amt     =   buy_trade_amts.get(buy, 0.0)
            trade_amt   =   sell_amt
            trade       =   trade_amt
            coin_pair   =   "%s_%s" % (base_currency, sell)
            sell_amt    =   round(sell_amt - trade_amt, 8)
            buy_amt     =   round(buy_amt - trade_amt, 8)
            action      =   actions[(i + 1) % 2]

            print "%-5s in %-11s %.8f %s  [%.8f %s]" % (action, coin_pair, trade, mkt, trade_amt, base_currency)
            trade_tot += trade_amt if action == "BUY" else -trade_amt
            did_trade = True
            sell_trade_amts[sell] = sell_amt

            if buy_amt > 0.0:
                buy_trade_amts[buy] = buy_amt
            else:
                if buy_amt < 0.0:
                    sell_val    =   sell_trade_amts.get(buy, 0.0)
                    sell_val    -=  buy_amt
                    sell_trade_amts[buy] = sell_val
                
        if sell_amt > 0.0: # To catch base currency overages
            sell_trade_amts[sell] = sell_amt
        else:
            if sell_amt < 0.0:
                buy_val =   buy_trade_amts.get(sell, 0.0)
                buy_val -=  sell_amt
                buy_trade_amts[sell]    = buy_val
            del sell_trade_amts[sell]

print "tot: %10.8f" % (trade_tot)

#print "buys:  ", buy_trade_amts
#print "sells: ", sell_trade_amts

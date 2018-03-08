#!/usr/bin/env python

import urllib
import urllib2
import hashlib
import hmac
import time
import json
import sys
import os.path

class poloniex(object):
    _trade_api_url      = 'https://poloniex.com/tradingApi'
    _public_api_url     = 'https://poloniex.com/public'
    _dump_file_prefix   = 'dump_polo_'

    def __init__(self, api_key, api_secret, debug=False):
        self.debug      = debug
        self.api_key    = api_key
        self.api_secret = api_secret

    def _trade_api_query(self, command, params={}):
        result          = None
        try:
            dump_filename   = poloniex._dump_file_prefix + command + '.json'
            if not self.debug or not os.path.exists(dump_filename):
                params['command']   = command
                params['nonce']     = int(time.time() * 1000.0)
                post_data           = urllib.urlencode(params)
                pd_signed           = hmac.new(self.api_secret, post_data, hashlib.sha512).hexdigest()
                headers             = {
                                        'Key'   : self.api_key,
                                        'Sign'  : pd_signed
                }

                req     = urllib2.Request(poloniex._trade_api_url, post_data, headers)
                doc     = urllib2.urlopen(req)
                doc_txt = doc.read()
                if (self.debug):
                    dump_file   = open(dump_filename, 'w')
                    dump_file.write(doc_txt)
            else:
                doc = open(dump_filename, 'r')
                doc_txt =   doc.read()
            result  = json.loads(doc_txt)
        except Exception as e:
            print e
        return result

    def _public_api_query(self, command, params={}):
        result  = None
        try:
            dump_filename   = poloniex._dump_file_prefix + command + '.json'
            if not self.debug or not os.path.exists(dump_filename):
                params['command']   = command
                param_str           = "?%s" % (urllib.urlencode(params))
                doc                 = urllib2.urlopen(poloniex._public_api_url + param_str)
                doc_txt             = doc.read()
                if (self.debug):
                    dump_file   = open(dump_filename, 'w')
                    dump_file.write(doc_txt)
            else:
                doc = open(dump_filename, 'r')
                doc_txt =   doc.read()
            result  = json.loads(doc_txt)
        except Exception as e:
            print e
        return result

#    {
#        "available":    "0.23710790",
#        "onOrders":     "0.00000000",
#        "btcValue":     "0.23710790"
#    }
    class balance(object):
        def __init__(self, balance_data=None):
            self.balance    = 0.0
            self.on_order   = 0.0
            self.btc_value  = 0.0
            if balance_data:
                self.balance    = float(balance_data[u'available'])
                self.on_order   = float(balance_data[u'onOrders'])
                self.btc_value  = float(balance_data[u'btcValue'])
        def __repr__(self):
            return "balance: %.8f, on_order: %.8f, btc_value: %.8f" % (self.balance, self.on_order, self.btc_value)

    def getBalances(self):
        balances        = None
        balance_data    = self._trade_api_query('returnCompleteBalances')
        if balance_data != None:
            balances    = {}
            for coin, data in balance_data.iteritems():
                try:
                    balance = poloniex.balance(data)
                    if balance.balance > 0 or balance.on_order > 0:
                        balances[coin]  = balance
                except Exception as e:
                    print e
        return balances

    def getFeeInfo(self):
        print self._trade_api_query('returnFeeInfo')

#   {
#       "id":               121,
#       "last":             "6956.95000023",
#       "lowestAsk":        "6959.00000000",
#       "highestBid":       "6956.95000026",
#       "percentChange":    "0.06212977",
#       "baseVolume":       "71544741.92528193",
#       "quoteVolume":      "10434.87960817",
#       "isFrozen":         "0",
#       "high24hr":         "7281.42800003",
#       "low24hr":          "6510.14948952"
#   }
    class market(object):
        def __init__(self, currency_pair, currency_data):
            self.id             = int(currency_data[u'id'])
            self.currency_pair  = currency_pair
            self.last_price     = float(currency_data[u'last'])

        def __repr__(self):
          return "id: %d, currency_pair: %s, last_price: %.8f" % (self.id, self.currency_pair, self.last_price)

    def getTicker(self):
        ticker  = None
        try:
            ticker_data = self._public_api_query('returnTicker')
            if ticker_data:
                ticker  = {}
            for curr_pair, curr_data in ticker_data.iteritems():
                try:
                    mkt, curr = curr_pair.split('_', 2)
                    mkt_data = poloniex.market(curr_pair, curr_data)
                    while True:
                        try:
                            ticker[mkt][curr] = mkt_data
                            break
                        except:
                            ticker[mkt] = {}

                except Exception as e:
                    print e
        except Exception as e:
            print "2", e

        return ticker

    class OrderBook(object):
        def __init__(self):
            self.bids   = []
            self.asks   = []

        def addAsk(self, price, amount):
            self.asks.append((round(float(price), 8), round(float(amount), 8)))

        def addBid(self, price, amount):
            self.bids.append((round(float(price), 8), round(float(amount), 8)))

        def getAsks(self):
            return self.asks

        def getBids(self):
            return self.bids

    def getOrderBook(self, currency_pair):
        order_book  = None
        params  = { u'currencyPair' : currency_pair }
        order_book_data = self._public_api_query('returnOrderBook', params)
        try:
            err_str = order_book_data['error']
            print err_str
        except:
            order_book  = poloniex.OrderBook()
            for ask in order_book_data[u'asks']:
                order_book.addAsk(ask[0], ask[1])
            for bid in order_book_data[u'bids']:
                order_book.addBid(bid[0], bid[1])
        return order_book

if __name__ == '__main__':
    polo_key    = ''
    polo_secret = ''

    coin_label  = "Coin"
    coin_len    = len(coin_label)
    bal_label   = "Balance"
    bal_len     = len(bal_label)
    order_label = "On Order"
    order_len   = len(order_label)
    btc_label   = "BTC Value"
    btc_len     = len(btc_label)
    pct_label   = "% Index"
    pct_len     = len(pct_label)

    polo        = poloniex(polo_key, polo_secret, debug=(1 == 0))

    if False:
        polo.getFeeInfo()

    if False:
        ob  = polo.getOrderBook("BTC_ETH")
        if ob:
            print "Asks"
            for price, amount in reversed(ob.getAsks()):
                print "%11.8f  %14.8f" % (price, amount)
            print "Bids"
            for price, amount in ob.getBids():
                print "%11.8f  %14.8f" % (price, amount)
            print "Spread: %11.8f" % (ob.getAsks()[0][0] - ob.getBids()[0][0])
        ob  = polo.getOrderBook("ETH_BTC")

    usdt_price  = None
    usdt_label  = "USDT Value"
    usdt_len    = len(usdt_label)
    try:
        ticker      = polo.getTicker()
        usdt        = ticker[u'USDT'][u'BTC']
        usdt_price  = usdt.last_price
        print usdt_price
    except Exception as e:
        print e
        pass

    if (0 == 1) and ticker:
        for mkt, currs in ticker.iteritems():
            for curr, curr_data in currs.iteritems():
                print mkt, curr, curr_data.id, "%.8f" % (curr_data.last_price)

    if 0 == 0:
        balances    = polo.getBalances()
        coins       = []
        btc_total   = 0.0

        if balances != None:
            for coin, balance in balances.iteritems():
                btc_total   += balance.btc_value
                try:
                    try:
                        btc_xchg    = ticker[u'BTC'][coin].last_price
                    except Exception as e:
                        if u'BTC' == coin:
                            btc_xchg    = 1.0
                        else:
                            raise e
                    btc_value   = balance.balance * btc_xchg
                except:
                    print coin, "using balance BTC value"
                    btc_value   = balance.btc_value
                coin_len    = max(coin_len,     len(coin))
                bal_len     = max(bal_len,      len("%.8f" % (balance.balance)))
                order_len   = max(order_len,    len("%.8f" % (balance.on_order)))
                btc_len     = max(btc_len,      len("%.8f" % (btc_value)))
                if usdt_price:
                    usdt_len    = max(btc_len,      len("%.2f" % (btc_value * usdt_price)))
                coins.append((coin, balance.balance, balance.on_order, btc_value, 0.0 if not usdt_price else btc_value * usdt_price))
            btc_len     = max(btc_len,      len("%.8f" % (btc_total)))
            if usdt_price:
                usdt_len    = max(btc_len,      len("%.2f" % (btc_total * usdt_price)))

        if len(balances) > 0:
            coins.sort(key=lambda coin: -coin[3])
            print "%-*s  %-*s  %-*s  %-*s  %-*s  %-*s" % (coin_len, coin_label, bal_len, bal_label, order_len, order_label, btc_len, btc_label, usdt_len, usdt_label, pct_len, pct_label)
            for coin in coins:
                print "%*s  %*.8f  %*.8f  %*.8f  %*.2f  %*.2f%%" % (coin_len, coin[0], bal_len, coin[1], order_len, coin[2], btc_len, coin[3], usdt_len, coin[4], pct_len - 1, coin[3] / btc_total * 100.0)
            print "%*s  %*s  %*s  %*.8f  %*.2f  %*s" % (coin_len, '', bal_len, '', order_len, '', btc_len, btc_total, usdt_len, 0.0 if not usdt_price else btc_total * usdt_price, pct_len - 1, '')


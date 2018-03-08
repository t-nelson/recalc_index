#!/usr/bin/env python

import urllib
import urllib2
import json
import sys
import os

class coinmarketcap(object):
    _api_url     = "https://api.coinmarketcap.com/v1/ticker/"
    _dump_file   = "dump_coinmarketcap.json"

#{
#        "id": "bitcoin", 
#        "name": "Bitcoin", 
#        "symbol": "BTC", 
#        "rank": "1", 
#        "price_usd": "573.137", 
#        "price_btc": "1.0", 
#        "24h_volume_usd": "72855700.0", 
#        "market_cap_usd": "9080883500.0", 
#        "available_supply": "15844176.0", 
#        "total_supply": "15844176.0", 
#        "percent_change_1h": "0.04", 
#        "percent_change_24h": "-0.3", 
#        "percent_change_7d": "-0.57", 
#        "last_updated": "1472762067"
#},
    class coin_mkt_data(object):
        def __init__(self, coin_data):
            self.symbol = coin_data[u'symbol']
            try:
                self.mkt_cap_usd    = float(coin_data[u'market_cap_usd'])
            except:
                self.mkt_cap_usd    = 0.0
            try:
                self.rank           = int(coin_data[u'rank'])
            except:
                self.rank           = sys.maxint
        def __repr__(self):
            return "sym: %s, mkt_cap_usd: %.2f, mkt_cap_rank: %d" % (self.symbol, self.mkt_cap_usd, self.rank)

    def __init__(self, debug=False):
        self.debug  = debug
        # TODO query cache
        pass

    def getMarkets(self, limit=None):
        markets     = None
        params      = {}
        param_str   = ''
        if limit != None:
            try:
                params['limit'] = int(limit)
            except:
                pass
        if params:
            param_str   = "?%s" % (urllib.urlencode(params))

        if not self.debug or not os.path.exists(coinmarketcap._dump_file):
            doc     = urllib2.urlopen(coinmarketcap._api_url + param_str)
            doc_txt = doc.read()
            if self.debug:
                dump    = open(coinmarketcap._dump_file, 'w')
                dump.write(doc_txt)
        else:
            doc     = open(coinmarketcap._dump_file, 'r')
            doc_txt = doc.read()

        mkt_data    = json.loads(doc_txt)

        if mkt_data:
            markets = []
            for coin_data in mkt_data:
                try:
                    coin_mkt    = coinmarketcap.coin_mkt_data(coin_data)
                    markets.append(coin_mkt)
                    if len(markets) == limit:
                        break
                except Exception as e:
                    print e
            markets.sort(key=lambda m : m.rank)
        return markets

if __name__ == '__main__':
    rank_label          = u'Rank'
    coin_label          = u'Coin'
    mkt_cap_label       = u'Market Cap. (USD)'
    mkt_cap_pct_label   = u'Market Cap. (%)'
    rank_len            = len(rank_label)
    coin_len            = len(coin_label)
    mkt_cap_len         = len(mkt_cap_label)
    mkt_cap_pct_len     = len(mkt_cap_pct_label)
    mkt_cap_total       = 0
    cmc                 = coinmarketcap(debug=(1 == 0))
    markets             = cmc.getMarkets(50)

    for coin_mkt in markets:
        coin_len    = max(coin_len, len(coin_mkt.symbol))
        try:
            mkt_cap_len     = max(mkt_cap_len, len("%.0f" % (coin_mkt.mkt_cap_usd)))
            mkt_cap_total   += coin_mkt.mkt_cap_usd
        except:
            pass

    rank_len    = max(rank_len, len(str(len(markets))))
    print "%-*s  %-*s  %-*s  %-*s" % (rank_len, rank_label, coin_len, coin_label, mkt_cap_len, mkt_cap_label, mkt_cap_pct_len, mkt_cap_pct_label)
    for coin_mkt in markets:
        try:
            mkt_cap = float(coin[u'market_cap_usd'])
        except:
            mkt_cap = 0

        print "%*d  %*s  %*.0f  %*.2f%%" % (rank_len, coin_mkt.rank, coin_len, coin_mkt.symbol, mkt_cap_len, coin_mkt.mkt_cap_usd, mkt_cap_pct_len - 1, 100.0 * coin_mkt.mkt_cap_usd / mkt_cap_total)


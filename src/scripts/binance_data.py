import pandas as pd
import ccxt
import time

def retry_fetch_ohlcv(exchange, symbol, timeframe, since, limit):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
    #print('Fetched', len(ohlcv), symbol, 'candles from', exchange.iso8601 (ohlcv[0][0]), 'to', exchange.iso8601 (ohlcv[-1][0]))
    return ohlcv


def get_ohlcv(exchange, symbol, timeframe, since, limit):
    exchange = getattr(ccxt, exchange)({
        'enableRateLimit': True,  # required by the Manual
    })
    
    if isinstance(since, str):
        since = exchange.parse8601(since)

    earliest_timestamp = exchange.milliseconds()
    timeframe_duration_in_seconds = exchange.parse_timeframe(timeframe)
    timeframe_duration_in_ms = timeframe_duration_in_seconds * 1000
    timedelta = limit * timeframe_duration_in_ms
    all_ohlcv = []
    while True:
        fetch_since = earliest_timestamp - timedelta
        ohlcv = retry_fetch_ohlcv(exchange, symbol, timeframe, fetch_since, limit)

        # if we have reached the beginning of history
        if ohlcv[0][0] >= earliest_timestamp:
            break
        earliest_timestamp = ohlcv[0][0]
        all_ohlcv = ohlcv + all_ohlcv
        #print(len(all_ohlcv), symbol, 'candles in total from', exchange.iso8601(all_ohlcv[0][0]), 'to', exchange.iso8601(all_ohlcv[-1][0]))
        # if we have reached the checkpoint
        if fetch_since < since:
            break
    print(f"{symbol.split('/')[0]} - finished fetching data.")

    df = pd.DataFrame(all_ohlcv, columns=["timestampMs", "open", "high", "low", "close", "volume"])
    df.index = df.timestampMs
    return df.close

def get_closes_many(exchange, symbols, timeframe, since, limit):
    return pd.DataFrame(
        {
            symbol.split("/")[0]: get_ohlcv(exchange, symbol, timeframe, since, limit)
            for symbol in symbols
        }
    ).sort_index()

def whole_kit_and_kaboodle():

    closes = get_closes_many(
        'binance',
        [
            'BTC/USDT',
            'ETH/USDT',
        ],
        '1m',
        '2022-06-01T00:00:00Z',
        1000,
    );

    closes.to_csv("./data/binance_prices.csv")


if __name__ == "__main__":
    whole_kit_and_kaboodle()
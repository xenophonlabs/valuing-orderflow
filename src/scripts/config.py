from collections import defaultdict
import datetime as dt

start_timestamp = dt.datetime(2022, 7, 1).timestamp() # dt.datetime(2023, 1, 8).timestamp()
end_timestamp = dt.datetime(2023, 1, 1).timestamp() # dt.datetime(2023, 1, 2).timestamp()


# top pools by volume (in the last 7 days)
pools = {
    # top pools by volume (in the last 7 days)
    "USDC-ETH-0.05": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
    # "USDC-USDT-0.01": "0x3416cf6c708da44db2624d63ea0aaef7113527c6",
    # "ETH-USDT-0.05": "0x11b815efb8f581194ae79006d24e0d814b7697f6",
    # "WBTC-ETH-0.05": "0x4585fe77225b41b697c938b018e2ac67ac5a20c0",
    # "LDO-ETH-0.30": "0xa3f558aebaecaf0e11ca4b2199cc5ed341edfd74",
    # "DAI-USDC-0.01": "0x5777d92f208679db4b9778590fa3cab3ac9e2168",

    # # a pool with different fee but same pair as a top volume pool
    # "USDC-ETH-0.30": "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
}

# tells us which assets for each pool we should fill in binance data for
# make it a defaultdict so that we don't need to define superfluous assets
# like stable pairs
pools_to_binance_priced_assets = defaultdict(dict)
pools_to_binance_priced_assets.update(
    {
        "USDC-ETH-0.05": {"token1": "ETH"},
        "ETH-USDT-0.05": {"token0": "ETH"},
        "WBTC-ETH-0.05": {"token0": "BTC", "token1": "ETH"},
        "LDO-ETH-0.30": {"token1": "ETH"},

        "USDC-ETH-0.30": {"token1": "ETH"},
    }
)

MAX_SANDWICH_DIFFERENTIAL = 10 # maximum percentage difference between front-run amount0 and back-run amount0
"""
Code for retrieving hella swap data from the Graph.

Should be run from the src/ directory.

Shoutout to https://github.com/ZooWallet/Uniswap-MEV-Analysis
for the inspiration on the sandwich code (and the MIT license!).

"""

import asyncio
from collections import defaultdict
import datetime as dt
import json


from pprint import pprint

import aiohttp
import numpy as np
import pandas as pd

from informedness import informedness

def price_token0(swap):
    """
    Converting from Uniswap's SqrtPriceX96 quantity
    to a de-sqrt'ed, de-X96'ed, and de-decimalized number.
    
    This gives the price of token1 in units of token0.
    
    Reference: https://docs.uniswap.org/sdk/v3/guides/fetching-prices
    """
    d0 = int(swap["pool"]["token0"]["decimals"])
    d1 = int(swap["pool"]["token1"]["decimals"])

    p_smol = float(swap["sqrtPriceX96"])**2 / (2**192)
    
    p = p_smol * (10**(-d1)) / (10**(-d0))
    
    return p

def price_token1(swap):
    """
    This gives the price of token1 in units of token0.
    """
    return 1/price_token0(swap)

def prep_swap_data(swaps, start_timestamp=None, end_timestamp=None):  
    """
    Given a bunch of swap dictionary data from TheGraph response,
    create a pandas df.
    """  
    rows = []
    router_addresses = {
        "0xe592427a0aece92de3edee1f18e0157c05861564": "V3 router 1", # V3 router
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "V3 router 2", # V3 router 2
        "0x881d40237659c251811cec9c364ef91dc08d300c": "Metamask Router", # metamask
        "0x3b17056cc4439c61cea41fe1c9f517af75a978f7": "1inch Deployer 4",
        "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch V4 Router", # 1inch V4 aggregation router
        "0x1111111254eeb25477b68fb85ed929f73a960582": "1inch V5 Router", # 1inch V5 aggregation router
        "0x53222470cdcfb8081c0e3a50fd106f0d69e63f20": "1inch Unlabeled Router", # 1inch unlabeled
        "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x Router", # 0x
    }
    for swap in swaps:
        rows.append(
            {
                "blockTimestamp": float(swap["timestamp"]),
                "blockNumber": int(swap["transaction"]["blockNumber"]),
                "logIndex": int(swap["logIndex"]),

                "txnHash": swap["transaction"]["id"],
                "origin": swap["origin"],
                "sender": swap["sender"],
                "gasUsed": int(swap["transaction"]["gasUsed"]),
                "gasPrice": int(swap["transaction"]["gasPrice"]),

                "amount0": float(swap["amount0"]),
                "amount1": float(swap["amount1"]),
                "amountUSD": float(swap["amountUSD"]),
                "boughtToken0": 1 if (float(swap["amount0"]) < 0) else 0, # it's a buy if amount0 is positive
                "viaRouter": router_addresses[swap["sender"]] if (swap["sender"] in router_addresses) else 0,
                "price0After": price_token0(swap),
                "price1After": price_token1(swap),
            }
        )
    
    df = pd.DataFrame(rows)
    if start_timestamp:
        df = df[(df.blockTimestamp >= start_timestamp) & (df.blockTimestamp <= end_timestamp)]
    
    df = df.sort_values(by=["blockNumber", "logIndex"], ascending=True) # sorts the transactions by occurrence within the block
    df.index = range(len(df))
    return df

async def get_basic_swap_data(pool, cutoff_timestamp, end_timestamp, session, pool_name) -> pd.DataFrame:
    """
    Get all of the Uniswap swaps on a particular pool, back
    to a specific time `cutoff_timestamp`.
    
    pool: str
    cutoff_timestamp: int
    """
    pool = pool.lower().strip()
    url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
    allswaps = []
    sup_timestamp = 10**15 # greates that the timestamp can be, on each round of pagination
    
    # note: if we wanted to make this super fast, we'd set a manual lookback timestamp
    # and run all of the requests, e.g. 10_000 requests, in parallel. This would fucking
    # blast the Graph, but it would be faster. No need for this currently.
    for i in range(1_001):       
        query = '''
        {
            swaps(
                first: 1000, 
                orderBy: timestamp, 
                orderDirection: desc,
                where: {
                    pool: "%s",
                    timestamp_lte: %d
                    #timestamp_gt: %d
                }
            ) {
                amount0
                amount1
                amountUSD
                timestamp
                sqrtPriceX96
                tick
                logIndex
                sender
                origin

                pool {
                    token0 {
                        id
                        symbol
                        decimals
                    }
                    token1 {
                        id
                        symbol
                        decimals
                    }
                }
                
                transaction {
                    blockNumber
                    id
                    gasUsed
                    gasPrice                    
                }
            }
        }
        ''' % (
            pool,
            sup_timestamp,
            cutoff_timestamp
        )

        repeats = 100
        while repeats > 0:
            async with session.post(url, json={"query": query}) as resp:
                result = await resp.json()
            
            if ("data" not in result) or (len(result["data"]["swaps"]) == 0):
                repeats -= 1
                print(f"Encountered an error, now retrying. {repeats} repeats left.")
            else:
                repeats = 0
        
        swaps = result["data"]["swaps"]

        # linear-time search for the last timestamp; can be optimized to O(log(n)), but not worth it rn
        j = len(swaps)
        while int(swaps[j-1]["timestamp"]) < cutoff_timestamp:
            j -= 1

        if sup_timestamp == int(swaps[j-1]["timestamp"]):
            # note, this could be problematic if we had >1,000 swaps that all had the same timestamp
            print("done, since we have the same sup_timestamp as before")
            break
        else:
            sup_timestamp = int(swaps[j-1]["timestamp"]) # set the maximum time

        # concatenate all swaps that have timestamp >= cutoff_timestamp
        allswaps += swaps[:j]
        if j != len(swaps):
            #print("done, since the final swap is in the interior of the result batch")
            break

        if i % 10 == 0:
            print(f"\t{pool_name} swap_data - {dt.datetime.fromtimestamp(sup_timestamp)}")
            
    #pprint(allswaps[-1])
            
    return prep_swap_data(allswaps, cutoff_timestamp, end_timestamp)


def make_sandwich_data(swap_data: pd.DataFrame) -> pd.DataFrame:
    sandwich_data = {}

    for block_number in swap_data['blockNumber'].unique():
        blockData = swap_data[swap_data['blockNumber']==block_number]

        if len(blockData) >= 3:
            senders = blockData['sender']     
            for sender in senders.unique():
                senderSwapData = blockData[blockData['sender']==sender]
                if len(senderSwapData) == 2: # more than 1 tx in a block
                    sandwichStartIndex = senderSwapData.iloc[0].name

                    sandwichedSwap = blockData.loc[sandwichStartIndex+1] # the starting index of the potential sandwich
                    # three criteria to see if it's a sandwich attack 
                    withMiddleTx = senderSwapData.iloc[0].name == senderSwapData.iloc[-1].name - 2 # if there's a middle tx
                    sameTradingFlow = sandwichedSwap['amount1'] * senderSwapData.iloc[0]['amount1'] > 0 # same direction
                    withCloseTradeTx = senderSwapData.iloc[0]['amount1'] * senderSwapData.iloc[-1]['amount1'] < 0 # different direction

                    if withMiddleTx and sameTradingFlow and withCloseTradeTx:
                        # calculate start and end price 
                        ethStartPrice = abs(senderSwapData.iloc[0]['amount0'] / senderSwapData.iloc[0]['amount1'])
                        ethEndPrice = abs(senderSwapData.iloc[-1]['amount0'] / senderSwapData.iloc[-1]['amount1'])

                        # calculate gas cost
                        startGasFee = ethStartPrice * senderSwapData.iloc[0]['gasUsed'] * senderSwapData.iloc[0]['gasPrice'] / 1e18
                        endGasFee = ethEndPrice * senderSwapData.iloc[-1]['gasUsed'] * senderSwapData.iloc[-1]['gasPrice'] / 1e18
                        cost = (startGasFee + endGasFee)
                        if senderSwapData.iloc[0]['amount1'] < 0: # sell ETH first, buy it back later
                            revenue = (ethStartPrice - ethEndPrice) * abs(senderSwapData.iloc[0]['amount1'])

                        else:  # buy ETH first, sell it later
                            revenue = (ethEndPrice - ethStartPrice) * abs(senderSwapData.iloc[0]['amount1'])

                        sandwichTime = senderSwapData.iloc[0]["blockTimestamp"]                    

                        sandwich_data[sandwichTime] = {
                            
                            "blockNumber": block_number,
                            "top_bun_txn": senderSwapData.iloc[0].txnHash,
                            "meat_txn": sandwichedSwap.txnHash,
                            "bottom_bun_txn": senderSwapData.iloc[-1].txnHash,
                            
                            "sandwich_revenue": revenue,
                            "sandwich_cost": cost,
                            "sandwich_profit": revenue - cost,
                            
                            "buns_trader": sender,
                            "meat_trader": sandwichedSwap.sender,
                            
                            "top_bun_amount0": senderSwapData.iloc[0].amount0,
                            "meat_amount0": sandwichedSwap.amount0,
                            "bottom_bun_amount0": senderSwapData.iloc[-1].amount0,                            
                        }
    
    sandwich_data = pd.DataFrame(sandwich_data).T

    return sandwich_data


def make_most_recent_binance_price_before_block(symbol, binance_prices):
    def most_recent_binance_price_before_block(block_timestamp):
        block_dt = dt.datetime.fromtimestamp(block_timestamp)
        adder = (-block_dt.second)
        adder += 60 # add 60 seconds because we're looking at binance close data
        price_time = int(block_timestamp + adder)*1000

        return binance_prices[symbol][price_time]
    return most_recent_binance_price_before_block

def make_most_recent_binance_price_n_minutes_after_block(n, symbol, binance_prices):
    def most_recent_binance_price_before_block(block_timestamp):
        block_dt = dt.datetime.fromtimestamp(block_timestamp)
        adder = (-block_dt.second)
        adder += 60 # add 60 seconds because we're looking at binance close data
        adder += n*60
        price_time = int(block_timestamp + adder)*1000
        
        if price_time in binance_prices[symbol]:
            return binance_prices[symbol][price_time]
        else:
            return np.nan
    
    return most_recent_binance_price_before_block

def join_binance_price_data(swap_data: pd.DataFrame, binance_prices: pd.DataFrame,  tokens) -> pd.DataFrame:
    """
    Edits swap_data in-place to add a bunch of lagged binance prices.

    tokens: Dict. For example, tokens={"token1": "ETH"}
    """
    for token_enum, token_name in tokens.items():
        swap_data["binance_price_token1_pre_block"] = swap_data.blockTimestamp.apply(
            make_most_recent_binance_price_before_block("ETH", binance_prices)
        )
        for lag_minutes in [1, 5, 10, 30, 60]:
            swap_data[f"binance_price_{token_enum}_{lag_minutes}m_lag"] = swap_data.blockTimestamp.apply(
                make_most_recent_binance_price_n_minutes_after_block(lag_minutes, token_name, binance_prices)
            )
    return

async def get_all_data_single_asset(pool_name, pool_addr, start_timestamp, end_timestamp, binance_prices, pools_to_binance_priced_assets, session):
    print(f"Beginning the accumulation of {pool_name} data - {dt.datetime.now()}")

    swap_data = await get_basic_swap_data(pool_addr, start_timestamp, end_timestamp, session, pool_name)

    # create sandwich data from the swap data
    sandwich_data = make_sandwich_data(swap_data)

    # determine if the swaps are informed
    swap_data["informed"] = informedness(swap_data, sandwich_data)

    # join binance price data
    join_binance_price_data(swap_data, binance_prices, pools_to_binance_priced_assets[pool_name])

    # save the data
    swap_data.to_csv(f"./data/pairs/{pool_name}-swap_data.csv")
    sandwich_data.to_csv(f"./data/pairs/{pool_name}-sandwich_data.csv")

    print(f"Finished the accumulation of {pool_name} data - {dt.datetime.now()}.\n")

async def whole_kit_and_caboodle():
    # start_timestamp = (dt.datetime.now() - dt.timedelta(days=183)).timestamp()
    start_timestamp = dt.datetime(year=2022, month=7, day=1).timestamp() # 1673043302 # approx Jan 6th at 05pm eastern
    end_timestamp =   dt.datetime(year=2023, month=1, day=2).timestamp() # 1673061302 # approx Jan 6th at 10pm eastern
    assert start_timestamp < end_timestamp
    
    # top pools by volume (in the last 7 days)
    pools = {
        # top pools by volume (in the last 7 days)
        "USDC-ETH-0.05": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        "USDC-USDT-0.01": "0x3416cf6c708da44db2624d63ea0aaef7113527c6",
        "ETH-USDT-0.05": "0x11b815efb8f581194ae79006d24e0d814b7697f6",
        "WBTC-ETH-0.05": "0x4585fe77225b41b697c938b018e2ac67ac5a20c0",
        "LDO-ETH-0.30": "0xa3f558aebaecaf0e11ca4b2199cc5ed341edfd74",
        "DAI-USDC-0.01": "0x5777d92f208679db4b9778590fa3cab3ac9e2168",

        # a pool with different fee but same pair as a top volume pool
        "USDC-ETH-0.30": "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
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

    binance_prices = pd.read_csv("./data/binance_prices.csv").set_index("timestampMs")
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[
            get_all_data_single_asset(pool_name, pool_addr, start_timestamp, end_timestamp, binance_prices, pools_to_binance_priced_assets, session)
            for (pool_name, pool_addr) in pools.items()
        ])

    pass

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(whole_kit_and_caboodle())
    loop.close()

    
    pass
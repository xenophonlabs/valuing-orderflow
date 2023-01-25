from collections import defaultdict
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tabulate import tabulate

def _get_dfs(pools, path="./data/pairs-golden-dataset-dont-fuck-with/"):
    """
    Get swap and sandwich data for the specified pools.
    """
    dfs = defaultdict(dict)
    for pool in pools:
        dfs[pool]["swap"] = pd.read_csv(os.path.join(path, pool+"-swap_data.csv"))
        dfs[pool]["sandwich"] = pd.read_csv(os.path.join(path, pool+"-sandwich_data.csv"))
    
    return dfs

old_to_new_interfaces = {
    "V3 router 1": "Uniswap Router",
    "V3 router 2": "Uniswap Router",
    "Metamask Router": "MetaMask",
    "1inch Deployer 4": "1inch",
    "1inch V4 Router": "1inch",
    "1inch V5 Router": "1inch",
    "1inch Unlabeled Router": "1inch",
    "0x Router": "0x",
    "0": "No Interface",
}

def example_sandwich_txn(data, pools):
    new_datas = []
    indices = []
    for i, pool in enumerate(pools):
        df = data[pool]["sandwich"]
        y = np.transpose([x for x in df[["top_bun_txn", "meat_txn", "bottom_bun_txn"]].iloc[0].values])
        y = [[x] for x in y]
        row_to_name = {
            0: f"{pool}% Front-run Transaction",
            1: f"{pool}% Victim Transaction",
            2: f"{pool}% Back-run Transaction",
        }
        for j, x in enumerate(df[["top_bun_txn", "meat_txn", "bottom_bun_txn"]].iloc[0].values):
            indices.append(row_to_name[j])
            new_datas.append([x])

    print(tabulate(new_datas, showindex=indices, headers=["Transaction Hash"], tablefmt="latex"))

    # new_datas = np.transpose(new_datas)
    # print()
    pass

def swap_source_graphs(data, pools):
    """
    Pie chart of the interface used to create a swap.
    """
    
    for i, pool in enumerate(pools):
        fig, axs = plt.subplots(1, 2)
        fig.set_size_inches(8, 4)
        fig.set_dpi(250)
        df = data[pool]["swap"]
        new_interfaces_ = df.viaRouter.apply(
            lambda x: old_to_new_interfaces[x]
        )

        df.groupby(new_interfaces_)["viaRouter"].count().plot.pie(ax=axs[0])
        axs[0].set_title(f"{pool}% Swap Count")
        axs[0].set_ylabel("")

        df.groupby(new_interfaces_)["amountUSD"].sum().plot.pie(ax=axs[1])
        axs[1].set_title(f"{pool}% Swap Volume")
        axs[1].set_ylabel("")

        fig.savefig(f"./generated-figs/swap-sources/{pool}.png")
    
    # plt.show()
    return

def meat_source_graphs(data, pools):
    """
    Pie charts with interface source of the sandwich.
    """

    for i, pool in enumerate(pools):
        fig, axs = plt.subplots(1, 2)
        fig.set_size_inches(8, 4)
        fig.set_dpi(250)
        df = data[pool]["sandwich"]
        new_interfaces_ = df.meat_interface.apply(
            lambda x: old_to_new_interfaces[x]
        )
        df.groupby(new_interfaces_)["meat_interface"].count().plot.pie(ax=axs[0])
        axs[0].set_title(f"{pool}% Count")
        axs[0].set_ylabel("")
        
        meat_volume = df.meat_amount0.abs()
        meat_volume.groupby(new_interfaces_).sum().plot.pie(ax=axs[1])
        axs[1].set_title(f"{pool}% Volume")
        axs[1].set_ylabel("")

        fig.savefig(f"./generated-figs/meat-sources/{pool}.png")
    
    # plt.show()
    return

def pool_vs_sandwich_data(data, pools):
    """
    Rows=pool, columns={uninformed volume pct, bun volume pct, meat volume pct, sandwich count}. 
    """
    headers = ["{Uninformed Volume %}", "Front- Back-run Volume %", "Victim Volume %", "Sandwich Count", "Sandwich Multiple"]
    indices = pools
    table_data = []
    for pool in pools:
        sandwich = data[pool]["sandwich"]
        swap = data[pool]["swap"]

        total_swap_volume = swap.amount0.abs().sum()
        total_uninformed_volume = swap[~swap.informed].amount0.abs().sum()
        total_meat_volume = sandwich.meat_amount0.abs().sum()
        total_bun_volume = (sandwich.top_bun_amount0.abs() + sandwich.bottom_bun_amount0.abs()).sum()
        sandwich_count = len(sandwich)
        sandwich_multiple = f"{total_bun_volume / (total_uninformed_volume - total_bun_volume):<.4f}"

        print(total_uninformed_volume, total_meat_volume, total_bun_volume, sandwich_count)

        table_data.append([
            100*total_uninformed_volume / total_swap_volume,
            100*total_bun_volume / total_swap_volume,
            100*total_meat_volume / total_swap_volume,
            sandwich_count,
            sandwich_multiple,
        ])
    
    print(tabulate(table_data, headers=headers, showindex=indices, tablefmt="latex"))
    pass

def whole_kit_and_kaboodle():
    pools = [
        "USDC-ETH-0.05",
        "ETH-USDT-0.05",
        "DAI-USDC-0.01",
        "LDO-ETH-0.30",
        "USDC-ETH-0.30",
        "USDC-USDT-0.01",
        "WBTC-ETH-0.05"
    ]
    data = _get_dfs(pools)
    swap_source_graphs(data, pools)
    meat_source_graphs(data, pools)
    # example_sandwich_txn(data, pools)
    # pool_vs_sandwich_data(data, pools)
    pass

if __name__ == "__main__":
    whole_kit_and_kaboodle()
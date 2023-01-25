"""
is_informed() is a binary decider. 1=informed, 0=uninformed
"""

import pandas as pd

eps_ = 1e-10
has_lte_5_dec = lambda x: (((x%1) % 1e-5)/(1e-5) < eps_) or (1-((x%1) % 1e-5)/(1e-5) < eps_)
    
def is_informed3(swaps_in_block, swap_index):
    """
    Checks if an order went through an order router.
    """
    swap = swaps_in_block.iloc[swap_index]
    return True if (swap.viaRouter == 0) else False

def informedness(swap_data: pd.DataFrame, sandwich_data: pd.DataFrame):
    """
    The source of truth for determining if an order is informed.

    a txn is informed IFF it's not from a router and it's not a sandwich txn
    the idea is that router orders mostly come from uninformed traders, and
    sandwich txn's are either (a) uninformed meat or (b) uninformed atomic-arb buns

    """

    from_router = swap_data.viaRouter.apply(lambda x: False if str(x)=="0" else True) # informed if not from a router

    if len(sandwich_data) > 0:
        sandwich_top_bun_txns = {x for x in sandwich_data.top_bun_txn.values}
        sandwich_meat_txns = {x for x in sandwich_data.meat_txn.values}
        sandwich_bottom_bun_txns = {x for x in sandwich_data.bottom_bun_txn.values}
        sandwich_txns = sandwich_top_bun_txns | sandwich_meat_txns | sandwich_bottom_bun_txns
        is_sandwich_txn = swap_data.txnHash.apply(lambda x: x in sandwich_txns)
    else: # there are no sandwich txn's, so mark all of them to False
        is_sandwich_txn = swap_data.txnHash.apply(lambda _: False)

    return ~from_router & ~is_sandwich_txn


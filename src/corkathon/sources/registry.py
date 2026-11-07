from .cso_trade import CsoTradeLoader
from .ecb_fx import EcbFxLoader

LOADERS = {"cso_trade": CsoTradeLoader, "ecb_fx": EcbFxLoader}

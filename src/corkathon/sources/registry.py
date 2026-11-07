from .comext import ComextLoader
from .cso_trade import CsoTradeLoader
from .ecb_fx import EcbFxLoader

LOADERS = {"comext": ComextLoader, "cso_trade": CsoTradeLoader, "ecb_fx": EcbFxLoader}

from .comext import ComextLoader
from .cso_trade import CsoTradeLoader
from .ecb_fx import EcbFxLoader
from .gdelt import GdeltLoader
from .holidays import HolidaysLoader
from .met_warnings import MetWarningsLoader

LOADERS = {
    "comext": ComextLoader,
    "cso_trade": CsoTradeLoader,
    "ecb_fx": EcbFxLoader,
    "gdelt": GdeltLoader,
    "holidays": HolidaysLoader,
    "met_warnings": MetWarningsLoader,
}

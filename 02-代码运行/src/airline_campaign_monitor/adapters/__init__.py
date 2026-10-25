from .air_china import AirChinaAdapter
from .airasia import AirAsiaAdapter
from .ana import AnaAdapter
from .jal import JalAdapter
from .scoot import ScootAdapter
from .singapore_airlines import SingaporeAirlinesAdapter
from .vietnam_airlines import VietnamAirlinesAdapter

ALL_ADAPTERS = (
    AnaAdapter,
    JalAdapter,
    VietnamAirlinesAdapter,
    AirAsiaAdapter,
    ScootAdapter,
    SingaporeAirlinesAdapter,
    AirChinaAdapter,
)

__all__ = ["ALL_ADAPTERS"]


from __future__ import annotations

from alpaca.clr import CLRToken, CLRList
from alpaca.utils import Wrangler
from seer._params import Params

class Inspector(Wrangler):
    def apply(self, params: Params) -> None:
        self._apply([params], [params])

    @Wrangler.default
    def default_(fn, params: Params) -> None:
        print("\n"*32)
        print(params.inspect())
        input()
        for child in params.asl:
            if isinstance(child, CLRList):
                fn.apply(params.but_with(asl=child, mod=params.oracle.get_module(child)))
    

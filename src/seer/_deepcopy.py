from __future__ import annotations

from alpaca.utils import Wrangler
from alpaca.clr import CLRList, CLRToken

from seer._params import Params

# copy an ASL
class DeepCopy(Wrangler):
    def apply(self, params: Params):
        return self._apply([params], [params])

    # CLRTokens should be treated as literals 
    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params) -> CLRToken:
        return params.asl

    @Wrangler.default
    def default_(fn, params: Params) -> CLRList | CLRToken:
        components = [fn.apply(params.but_with(asl=child)) for child in params.asl]
        return CLRList(
            type=params.asl.type,
            lst=components,
            line_number=params.asl.line_number,
            guid=params.asl.guid)

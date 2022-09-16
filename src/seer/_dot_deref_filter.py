from __future__ import annotations

from alpaca.clr import CLRToken, CLRList
from alpaca.utils import Wrangler

class DotDerefFilter(Wrangler):
    def apply(self, asl: CLRList) -> CLRList:
        return self._apply([asl], [asl])
    
    def is_dot_deref(asl: CLRList):
        return (isinstance(asl, CLRList)
            and asl.type == "."
            and isinstance(asl.first(), CLRList)
            and asl.first().type == "deref")

    @Wrangler.default
    def default_(fn, asl: CLRList):
        children = [fn.apply(child) for child in asl]
        asl._list = children
        return asl

    @Wrangler.covers(lambda asl: isinstance(asl, CLRToken))
    def token_(fn, asl: CLRList) -> CLRToken:
        return asl

    @Wrangler.covers(is_dot_deref)
    def dot_deref_(fn, asl: CLRList) -> CLRList:
        print("here")
        ref_child = fn.apply(asl.first().first())
        tag_child = asl.second()
        return CLRList(
            type="->", 
            lst=[ref_child, tag_child],
            line_number=asl.line_number,
            guid=asl.guid)
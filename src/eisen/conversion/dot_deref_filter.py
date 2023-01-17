from __future__ import annotations

from alpaca.clr import CLRToken, CLRList
from alpaca.utils import Visitor

class DotDerefFilter(Visitor):
    def apply(self, asl: CLRList) -> CLRList:
        return self._route(asl, asl)

    @classmethod
    def is_dot_deref(cls, asl: CLRList):
        return (isinstance(asl, CLRList)
            and asl.type == "."
            and isinstance(asl.first(), CLRList)
            and asl.first().type == "deref")

    @Visitor.for_default
    def default_(fn, asl: CLRList):
        children = [fn.apply(child) for child in asl]
        asl._list = children
        return asl

    @Visitor.for_tokens
    def token_(fn, asl: CLRList) -> CLRToken:
        return asl

    @Visitor.for_asls(".")
    def dot_deref_(fn, asl: CLRList) -> CLRList:
        if DotDerefFilter.is_dot_deref(asl):
            ref_child = fn.apply(asl.first().first())
            tag_child = asl.second()
            return CLRList(
                type="->",
                lst=[ref_child, tag_child],
                line_number=asl.line_number,
                guid=asl.guid)
        return asl

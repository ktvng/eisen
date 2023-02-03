from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken

class Writer(Visitor):
    def apply(self, asl: CLRList):
        self._route(asl, asl)

    @Visitor.for_asls()
    def start_(fn, asl: CLRList):
        pass

from __future__ import annotations

from alpaca.clr import CLRList, CLRToken

from eisen.common.state import State
from eisen.common.nodedata import NodeData
from eisen.validation.nodetypes import Nodes

class RestructureIsStatement():
    @classmethod
    def run(cls, state: State):
        node = Nodes.Is(state)
        is_asl = state.get_asl()
        new_token = CLRToken(type_chain=["TAG"], value="is_" + node.get_type_name())
        new_ref = CLRList(type="ref", lst=[new_token], line_number=is_asl.line_number, data=NodeData())
        new_params = CLRList(type="params", lst=[is_asl.first()], line_number=is_asl.line_number, data=NodeData())
        is_asl.update(type="is_call", lst=[new_ref, new_params])

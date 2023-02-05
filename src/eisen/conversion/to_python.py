from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken
from alpaca.pattern import Pattern
import alpaca
from eisen.state.topythonstate import ToPythonState as State
from eisen.state.stateb import StateB
import eisen.adapters as adapters

class ToPython(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self.python_gm = alpaca.config.parser.run("./src/python/python.gm")

    def run(self, state: StateB) -> CLRList:
        return self.apply(State.create_from_stateb(state))

    def apply(self, state: State) -> CLRList:
        return self._route(state.asl, state)

    def create_asl(self, txt: str):
        return alpaca.clr.CLRParser.run(self.python_gm, txt)

    @Visitor.for_default
    def default_(fn, state: State):
        print(f"ToPython unimplemented for {state.asl}")
        return

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        return CLRList("start", lst=[fn.apply(state.but_with(asl=child))
            for child in state.get_all_children()])

    @Visitor.for_asls("struct")
    def struct_(fn, state: State):
        node = adapters.Struct(state)

        struct_name_token = Pattern("('struct name xs...)").match(state.get_asl()).name

        create_asl = node.get_create_asl()
        self_name_token: CLRToken = Pattern("('create _ _ ('rets (': name _)) _)") \
            .match(create_asl).name
        attr_toks = Pattern("(': attr_name _)").map(state.get_asl(),
            into_pattern=f"('= ('. ('ref '{self_name_token.value}) attr_name) 'None)")

        create_node = adapters.Create(state.but_with(asl=create_asl))
        arg_asl = fn.apply(state.but_with(asl=create_node.get_args_asl()))
        arg_asl._list = [CLRList("tags", lst=[self_name_token, *arg_asl._list])]
        seq_asl = fn.apply(state.but_with(asl=create_node.get_seq_asl()))
        seq_asl._list = [*attr_toks, *seq_asl._list]
        init_asl = CLRList("init", lst=[arg_asl, seq_asl])
        return CLRList("class", lst=[struct_name_token, init_asl])

    @staticmethod
    def get_ret_names(ret_asl: CLRList) -> list[CLRToken]:
        if ret_asl.has_no_children():
            return []
        if ret_asl.first().type == "prod_type":
            return [m.name for m in map(Pattern("(': name _)").match, ret_asl.first()._list) if m]
        return [Pattern("('rets (': name _))").match(ret_asl).name]

    @Visitor.for_asls("def")
    def def_(fn, state: State):
        node = adapters.Def(state)
        return_vars = Pattern("(': ret_name _)").map(node.get_rets_asl(),
            into_pattern=f"('= ret_name 'None)")
        ret_names = ToPython.get_ret_names(node.get_rets_asl())
        arg_asl = fn.apply(state.but_with(asl=node.get_args_asl()))
        seq_asl = fn.apply(state.but_with(
            asl=node.get_seq_asl(),
            ret_names=ret_names))
        seq_asl._list = [*return_vars, *seq_asl._list]
        return CLRList("def", lst=[state.first_child(), arg_asl, seq_asl])

    @Visitor.for_asls("return")
    def return_(fn, state: State):
        if state.get_ret_names():
            return CLRList("return", lst=[CLRList("tags", lst=state.get_ret_names())])
        return CLRList("return", lst=[])

    @Visitor.for_asls("args")
    def args_(fn, state: State):
        if state.get_asl().has_no_children():
            return CLRList("args", lst=[])
        return CLRList("args", lst=[fn.apply(state.but_with_first_child())])

    @Visitor.for_asls(":")
    def colon_(fn, state: State):
        return Pattern("(': name _)").match(state.get_asl()).name

    @Visitor.for_asls("prod_type")
    def prod_type_(fn, state: State):
        return CLRList("tags", lst=[fn.apply(state.but_with(asl=child))
            for child in state.get_all_children()])

    @Visitor.for_asls("seq")
    def seq_(fn, state: State):
        children = state.get_all_children()
        if children[-1].type != "return" and state.get_ret_names():
            children.append(CLRList("return", lst=[]))
        return CLRList("seq", lst=[fn.apply(state.but_with(asl=child))
            for child in children])

    @Visitor.for_asls("ilet", "ivar", "let", "var", "val", "var?")
    def iletivar_(fn, state: State):
        return CLRList("=", lst=[fn.apply(state.but_with(asl=child))
            for child in state.get_all_children()])

    @Visitor.for_asls("ref", "fn")
    def ref_(fn, state: State):
        return CLRList("ref", lst=[state.first_child()])

    @Visitor.for_asls("if", "cond", "lvals",
        "params", "call", "tags", "tuple",
        "=", ".", "+", "-", "/",
        "*", "==", "+=", "-=", "/=", "*=")
    def binop_(fn, state: State):
        return CLRList(state.get_asl().type, lst=[fn.apply(state.but_with(asl=child))
            for child in state.get_all_children()])

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        if state.get_asl().value == "true":
            return CLRToken(type_chain=["code"], value="True")
        if state.get_asl().value == "false":
            return CLRToken(type_chain=["code"], value="False")
        return state.get_asl()

from __future__ import annotations

import alpaca
from alpaca.clr import CLRList, CLRToken
from alpaca.utils import Visitor

from seer.common import asls_of_type

class Writer(Visitor):
    def run(self, asl: CLRList) -> str:
        parts = self.apply(asl)
        raw_text = "".join(parts)
        return alpaca.utils.formatter.indent(raw_text)

    def apply(self, asl: CLRList) -> list[str]:
        return self._apply([asl], [asl])

    @Visitor.covers(lambda x: isinstance(x, CLRToken))
    def token_(fn, asl: CLRToken):
        return [asl.value]

    @Visitor.covers(asls_of_type("start"))
    def start_(fn, asl: CLRList):
        parts = []
        for child in asl:
            parts += fn.apply(child) + ["\n"]
        return parts

    @Visitor.covers(asls_of_type("struct"))
    def struct_(fn, asl: CLRList):
        parts = ["struct ", *fn.apply(asl.first()), " {\n"]
        for child in asl[1:]:
            parts += fn.apply(child) + ["\n"]
        return parts + ["}\n"]

    @Visitor.covers(asls_of_type("mod"))
    def mod_(fn, asl: CLRList):
        parts = ["mod ",
            *fn.apply(asl.first()),
            " {\n"]
        for child in asl[1:]:
            parts += fn.apply(child) + ["\n"]
        parts += ["}\n"]
        return parts
 
    @Visitor.covers(asls_of_type(":"))
    def colon_(fn, asl: CLRList):
        return [*fn.apply(asl.first()), 
            ": ",
            *fn.apply(asl.second())]
 
    @Visitor.covers(asls_of_type("create"))
    def create_(fn, asl: CLRList):
        return ["create(",
            *fn.apply(asl.first()),
            ") -> ",
            *fn.apply(asl.second()),
            *fn.apply(asl.third())]

    @Visitor.covers(asls_of_type("type", "fn_type_in", "args", "rets", "fn_type_out", "ref", "fn"))
    def pass_(fn, asl: CLRList):
        if not asl:
            return []
        return fn.apply(asl.first())
 
    @Visitor.covers(asls_of_type("prod_type", "params"))
    def prod_type(fn, asl: CLRList):
        parts = []
        if asl:
            parts += fn.apply(asl.first())
        for child in asl[1:]:
            parts += [", ", *fn.apply(child)]
        return parts
 
    @Visitor.covers(asls_of_type("def"))
    def def_(fn, asl: CLRList):
        return ["fn ",
            *fn.apply(asl.first()),
            "("
            *fn.apply(asl.second()),
            ") -> ",
            *fn.apply(asl.third()),
            *fn.apply(asl[-1])]
    
    @Visitor.covers(asls_of_type("fn_type"))
    def fn_type_(fn, asl: CLRList):
        return ["(",
            *fn.apply(asl.first()),
            ") -> ",
            *fn.apply(asl.second())]
    
    @Visitor.covers(asls_of_type("ilet"))
    def ilet(fn, asl: CLRList):
        return ["let ", *fn.apply(asl.first()), " = ", *fn.apply(asl.second())]

    @Visitor.covers(asls_of_type("let"))
    def let_(fn, asl: CLRList):
        return ["let ", *fn.apply(asl.first())]
 
    @Visitor.covers(asls_of_type("while"))
    def while_(fn, asl: CLRList):
        return ["while ", *fn.apply(asl.first())]
 
    @Visitor.covers(asls_of_type("seq"))
    def seq_(fn, asl: CLRList):
        parts = []
        for child in asl:
            parts += fn.apply(child) + ["\n"]
        return ["{\n", *parts, "}\n"]
 
    @Visitor.covers(asls_of_type("cond"))
    def cond_(fn, asl: CLRList):
        return ["(", *fn.apply(asl.first()), ") ", *fn.apply(asl.second())]
      
    @Visitor.covers(asls_of_type(["<", ">", "<=", ">=", "+", "-", "/", "*", "+=", "=", "==", ".", "::"]))
    def bin_op_(fn, asl: CLRList):
        if asl.type in [".", "::"]:
            operator = asl.type
        else:
            operator = f" {asl.type} "
        return [*fn.apply(asl.first()), operator, *fn.apply(asl.second())]
 
    @Visitor.covers(asls_of_type("call"))
    def call_(fn, asl: CLRList):
        return [*fn.apply(asl.first()), "(", *fn.apply(asl.second()), ")"]
    
    # TODO: need to work with elseif
    @Visitor.covers(asls_of_type("if"))
    def if_(fn, asl: CLRList):
        return ["if ", *fn.apply(asl.first())]

    @Visitor.covers(asls_of_type("return"))
    def return_(fn, asl: CLRList):
        return ["return"]
  
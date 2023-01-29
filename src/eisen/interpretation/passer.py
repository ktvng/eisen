from __future__ import annotations
from eisen.interpretation.obj import Obj

class Passer():
    @classmethod
    def pass_by_value(cls, context: dict, l: Obj, r: Obj):
        l.copy(r)

    @classmethod
    def pass_by_reference(cls, context: dict, l: Obj, r: Obj):
        context[l.name] = r

    @classmethod
    def handle_assignment(cls, context: dict, l: Obj, r: Obj):
        if l.is_var:
            cls.pass_by_reference(context, l, r)
        else:
            cls.pass_by_value(context, l, r)

    @classmethod
    def add_var(cls, context: dict, name: str, val: Obj):
        context[name] = val

    @classmethod
    def add_let(cls, context: dict, name: str, val: Obj):
        l = Obj(None, name=name)
        context[name] = l
        Passer.pass_by_value(context, l, val)

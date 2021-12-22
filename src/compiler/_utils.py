from __future__ import annotations

from compiler._context import Context
from compiler._object import Object
from compiler._definitions import Definitions

def _deref_ir_obj_if_needed(compiler_obj : Object, cx : Context):
    if Definitions.is_primitive(compiler_obj.type):
        return cx.builder.load(compiler_obj.get_ir())

    return compiler_obj.get_ir()


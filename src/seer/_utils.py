import compiler
from seer._definitions import Definitions

def _deref_ir_obj_if_needed(compiler_obj : compiler.Object, cx : compiler.Context):
    if Definitions.is_primitive(compiler_obj.type):
        return cx.builder.load(compiler_obj.get_ir())

    return compiler_obj.get_ir()
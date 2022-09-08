from __future__ import annotations

from alpaca.config import Config
from alpaca.utils import Wrangler
from alpaca.concepts import Type, TypeFactory, Context
from alpaca.asts import CLRList

from seer._params import Params
from seer._typewrangler import TypeWrangler
from seer._common import ContextTypes, asls_of_type, SeerInstance


# generate the module structure and add types to the respective modules
class ModuleWrangler(Wrangler):
    def apply(self, params: Params):
        return self._apply([params], [params])

    @classmethod
    def init_params(cls, config: Config, asl: CLRList, txt: str):
        global_mod = Context("global", type=ContextTypes.mod)
        global_mod.add_type(TypeFactory.produce_novel_type("int"))
        global_mod.add_type(TypeFactory.produce_novel_type("str"))
        global_mod.add_type(TypeFactory.produce_novel_type("flt"))
        global_mod.add_type(TypeFactory.produce_novel_type("bool"))
        global_mod.add_type(TypeFactory.produce_novel_type("int*"))
        global_mod.add_type(TypeFactory.produce_novel_type("str*"))
        global_mod.add_type(TypeFactory.produce_novel_type("flt*"))
        global_mod.add_type(TypeFactory.produce_novel_type("bool*"))
        global_mod.add_type(TypeFactory.produce_novel_type("int?"))
        global_mod.add_type(TypeFactory.produce_novel_type("str?"))
        global_mod.add_type(TypeFactory.produce_novel_type("flt?"))
        global_mod.add_type(TypeFactory.produce_novel_type("bool?"))

        return Params(
            config=config, 
            asl=asl,
            txt=txt,
            mod=global_mod,
            starting_mod=global_mod,
            struct_name=None,
            exceptions=[],
            is_ptr=False)

    @classmethod
    def parse_type(cls, params: Params) -> Type:
        return TypeWrangler().apply(params)
    
    @Wrangler.covers(asls_of_type("start"))
    def start_i(fn, params: Params):
        params.asl.module = params.mod
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Wrangler.covers(asls_of_type("struct"))
    def struct_i(fn, params: Params):
        params.asl.module = params.mod
        params.mod.resolve_type(ModuleWrangler.parse_type(params))
        for child in params.asl:
            fn.apply(params.but_with(asl=child, struct_name=params.asl.first().value))

    @Wrangler.covers(asls_of_type("mod"))
    def mod_i(fn, params: Params):
        params.asl.module = params.mod
        child_mod = Context(
            name=params.asl.first().value,
            type=ContextTypes.mod, 
            parent=params.mod)

        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                mod=child_mod))

    @Wrangler.covers(asls_of_type("def"))
    def def_i(fn, params: Params):
        params.asl.module = params.mod
        new_type = ModuleWrangler.parse_type(params)
        params.mod.resolve_type(new_type)
        params.asl.instances = [params.mod.add_instance(
            SeerInstance(
                name=params.asl.first().value,
                type=new_type,
                context=params.mod))]

    @Wrangler.covers(asls_of_type("create"))
    def create_i(fn, params: Params):
        params.asl.module = params.mod
        new_type = ModuleWrangler.parse_type(params)
        params.mod.resolve_type(new_type)
        params.asl.instances = [params.mod.add_instance(
            SeerInstance(
                name="create_" + params.struct_name,
                type=new_type,
                context=params.mod))]

    @Wrangler.covers(asls_of_type("TAG", ":"))
    def TAG_i(fn, params: Params):
        return

    @Wrangler.default
    def default_(fn, params: Params):
        params.asl.module = params.mod

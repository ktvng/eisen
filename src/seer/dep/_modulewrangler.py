from __future__ import annotations

from alpaca.utils import Wrangler
from alpaca.concepts import Type, Context
from alpaca.clr import CLRList, CLRToken

from seer._params import Params
from seer.dep._typewrangler import TypeWrangler
from seer._common import ContextTypes, asls_of_type, SeerInstance


# generate the module structure and add types to the respective modules
class ModuleWrangler(Wrangler):
    def apply(self, params: Params):
        if self.debug and isinstance(params.asl, CLRList):
            print("\n"*64)
            print(params.inspect())
            print("\n"*4)
            input()
        return self._apply([params], [params])

    @classmethod
    def parse_type(cls, params: Params) -> Type:
        return TypeWrangler().apply(params)
    
    @Wrangler.covers(asls_of_type("start"))
    def start_i(fn, params: Params):
        params.oracle.add_module(params.asl, params.mod)
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Wrangler.covers(asls_of_type("struct", "interface"))
    def struct_i(fn, params: Params):
        params.oracle.add_module(params.asl, params.mod)
        params.mod.resolve_type(ModuleWrangler.parse_type(params))
        for child in params.asl:
            fn.apply(params.but_with(asl=child, struct_name=params.asl.first().value))

    @Wrangler.covers(asls_of_type("mod"))
    def mod_i(fn, params: Params):
        params.oracle.add_module(params.asl, params.mod)
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
        params.oracle.add_module(params.asl, params.mod)
        new_type = ModuleWrangler.parse_type(params)
        params.mod.resolve_type(new_type)
        params.oracle.add_instances(
            asl=params.asl,
            instances = [params.mod.add_instance(
                SeerInstance(
                    name=params.asl.first().value,
                    type=new_type,
                    context=params.mod,
                    asl=params.asl))])



    @Wrangler.covers(asls_of_type("create"))
    def create_i(fn, params: Params):
        # add the struct name as the first parameter
        params.asl._list.insert(0, CLRToken(type_chain=["TAG"], value=params.struct_name))
        params.oracle.add_module(params.asl, params.mod)
        new_type = ModuleWrangler.parse_type(params)
        params.mod.resolve_type(new_type)
        params.oracle.add_instances(
            asl=params.asl,
            instances=[params.mod.add_instance(
                SeerInstance(
                    name=params.struct_name,
                    type=new_type,
                    context=params.mod,
                    asl=params.asl,
                    is_constructor=True))])

    @Wrangler.covers(asls_of_type("TAG", ":"))
    def TAG_i(fn, params: Params):
        return

    @Wrangler.default
    def default_(fn, params: Params):
        params.oracle.add_module(params.asl, params.mod)

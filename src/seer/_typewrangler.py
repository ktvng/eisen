from __future__ import annotations

from alpaca.utils import Wrangler
from alpaca.asts import CLRList, CLRToken
from alpaca.concepts import Type, TypeFactory

from seer._params import Params
from seer._common import asls_of_type

# generate a type within a module
class TypeWrangler(Wrangler):
    def apply(self, params: Params) -> Type:
        return self._apply([params], [params])

    @classmethod
    def _get_component_names(cls, components: list[CLRList]) -> list[str]:
        if any([component.type != ":" for component in components]):
            raise Exception("expected all components to have type ':'")

        return [component.first().value for component in components]

    @classmethod
    def _asl_has_return_clause(cls, asl: CLRList):
        return len(asl) == 4

    @Wrangler.covers(asls_of_type("type"))
    def type_(fn, params: Params) -> Type:
        # eg. (type int)
        token: CLRToken = params.asl.head()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")
        predefined_type = params.mod.get_type_by_name(token.value)
        if predefined_type:
            params.asl.returns_type = predefined_type
            return predefined_type

        params.asl.returns_type = params.mod.resolve_type(
            type=TypeFactory.produce_novel_type(token.value));
        
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type(":"))
    def colon_(fn, params: Params) -> Type:
        # eg. (: name (type int))
        return fn.apply(params.but_with(asl=params.asl.second()))

    @Wrangler.covers(asls_of_type("prod_type"))
    def prod_type_(fn, params: Params) -> Type:
        # eg.  (prod_type
        #           (: name1 (type int))
        #           (: name2 (type str)))
        component_types = [fn.apply(params.but_with(asl=component)) for component in params.asl]
        return params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(components=component_types))

    @Wrangler.covers(asls_of_type("types"))
    def types_(fn, params: Params) -> Type:
        # eg. (types (type int) (type str))
        component_types = [fn.apply(params.but_with(asl=component)) for component in params.asl]
        return params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(components=component_types))

    @Wrangler.covers(asls_of_type("fn_type_in", "fn_type_out"))
    def fn_type_out(fn, params: Params) -> Type:
        # eg. (fn_type_in/out (type(s) ...))
        if len(params.asl) == 0:
            return params.mod.resolve_type(TypeFactory.produce_novel_type("void"))
        return params.mod.resolve_type(
            type=fn.apply(params.but_with(asl=params.asl.first())))

    @Wrangler.covers(asls_of_type("fn_type")) 
    def fn_type_(fn, params: Params) -> Type:
        # eg. (fn_type (fn_type_in ...) (fn_type_out ...))
        return params.mod.resolve_type(
            type=TypeFactory.produce_function_type(
                arg=fn.apply(params.but_with(asl=params.asl.first())),
                ret=fn.apply(params.but_with(asl=params.asl.second()))))

    @Wrangler.covers(asls_of_type("args", "rets"))
    def args_(fn, params: Params) -> Type:
        # eg. (args (type ...))
        if params.asl:
            return fn.apply(params.but_with(asl=params.asl.first()))
        return TypeFactory.produce_novel_type("void")

    @Wrangler.covers(asls_of_type("create"))
    def create_(fn, params: Params) -> Type:
        # eg. (create (args ...) (rets ...) (seq ...))
        return params.mod.resolve_type(
            type=TypeFactory.produce_function_type(
                arg=fn.apply(params.but_with(asl=params.asl.first())),
                ret=fn.apply(params.but_with(asl=params.asl.second()))))

    @Wrangler.covers(asls_of_type("def"))
    def def_(fn, params: Params) -> Type:
        # eg. (def name (args ...) (rets ...) (seq ...))
        if TypeWrangler._asl_has_return_clause(params.asl):
            return params.mod.resolve_type(
                type=TypeFactory.produce_function_type(
                    arg=fn.apply(params.but_with(asl=params.asl.second())),
                    ret=fn.apply(params.but_with(asl=params.asl.third()))))
        else:
            return params.mod.resolve_type(
                type=TypeFactory.produce_function_type(
                    arg=fn.apply(params.but_with(asl=params.asl.second())),
                    ret=TypeFactory.produce_novel_type("void")))

    @Wrangler.covers(asls_of_type("struct"))
    def struct_(fn, params: Params) -> Type:
        # eg. (struct name (: ...) (: ...) ... (create ...))
        attributes = [component for component in params.asl if component.type == ":"]
        return params.mod.resolve_type(
            type=TypeFactory.produce_struct_type(
                name=params.asl.first().value,
                components=[fn.apply(params.but_with(asl=component)) for component in attributes],
                component_names=TypeWrangler._get_component_names(attributes)))


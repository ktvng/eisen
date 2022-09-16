from __future__ import annotations

from alpaca.utils import Wrangler
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import Type, TypeFactory

from seer._params import Params
from seer._common import asls_of_type

# generate a type within a module
class TypeWrangler(Wrangler):
    def apply(self, params: Params) -> Type:
        return self._apply([params], [params])

    # resolve the type returned by 'f' inside the current module as specified 
    # by params.mod in order to reduce the number of duplicate type objects created
    def resolves_type(f):
        def decorator(fn, params: Params):
            result: Type = f(fn, params)
            return params.mod.resolve_type(result)
        return decorator

    @classmethod
    def _get_component_names(cls, components: list[CLRList]) -> list[str]:
        if any([component.type != ":" for component in components]):
            raise Exception("expected all components to have type ':'")

        return [component.first().value for component in components]

    @Wrangler.covers(asls_of_type("type"))
    @resolves_type
    def type_(fn, params: Params) -> Type:
        # eg. (type int)
        token: CLRToken = params.asl.head()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")
        
        found_type = params.mod.get_type_by_name(token.value)
        if found_type:
            return found_type

        raise Exception("unknown type!")
        return TypeFactory.produce_novel_type(token.value)

    @Wrangler.covers(asls_of_type(":"))
    @resolves_type
    def colon_(fn, params: Params) -> Type:
        # eg. (: name (type int))
        return fn.apply(params.but_with(asl=params.asl.second()))

    @Wrangler.covers(asls_of_type("prod_type"))
    @resolves_type
    def prod_type_(fn, params: Params) -> Type:
        # eg.  (prod_type
        #           (: name1 (type int))
        #           (: name2 (type str)))
        component_types = [fn.apply(params.but_with(asl=component)) for component in params.asl]
        return TypeFactory.produce_tuple_type(components=component_types)

    @Wrangler.covers(asls_of_type("types"))
    @resolves_type
    def types_(fn, params: Params) -> Type:
        # eg. (types (type int) (type str))
        component_types = [fn.apply(params.but_with(asl=component)) for component in params.asl]
        return TypeFactory.produce_tuple_type(components=component_types)

    @Wrangler.covers(asls_of_type("fn_type_in", "fn_type_out"))
    @resolves_type
    def fn_type_out(fn, params: Params) -> Type:
        # eg. (fn_type_in/out (type(s) ...))
        if len(params.asl) == 0:
            return params.mod.resolve_type(TypeFactory.produce_novel_type("void"))
        return fn.apply(params.but_with(asl=params.asl.first()))

    @Wrangler.covers(asls_of_type("fn_type")) 
    @resolves_type
    def fn_type_(fn, params: Params) -> Type:
        # eg. (fn_type (fn_type_in ...) (fn_type_out ...))
        return TypeFactory.produce_function_type(
            arg=fn.apply(params.but_with(asl=params.asl.first())),
            ret=fn.apply(params.but_with(asl=params.asl.second())))

    @Wrangler.covers(asls_of_type("args", "rets"))
    @resolves_type
    def args_(fn, params: Params) -> Type:
        # eg. (args (type ...))
        if params.asl:
            return fn.apply(params.but_with(asl=params.asl.first()))
        return TypeFactory.produce_novel_type("void")

    @Wrangler.covers(asls_of_type("def", "create"))
    @resolves_type
    def def_(fn, params: Params) -> Type:
        # eg. (def name (args ...) (rets ...) (seq ...))
        return TypeFactory.produce_function_type(
            arg=fn.apply(params.but_with(asl=params.asl.second())),
            ret=fn.apply(params.but_with(asl=params.asl.third())))

    @Wrangler.covers(asls_of_type("struct"))
    @resolves_type
    def struct_(fn, params: Params) -> Type:
        # eg. (struct name (: ...) (: ...) ... (create ...))
        attributes = [component for component in params.asl if component.type == ":"]
        return TypeFactory.produce_struct_type(
            name=params.asl.first().value,
            components=[fn.apply(params.but_with(asl=component)) for component in attributes],
            component_names=TypeWrangler._get_component_names(attributes))


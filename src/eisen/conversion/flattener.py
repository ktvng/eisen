from __future__ import annotations

import alpaca
from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken

import eisen.adapters as adapters
from eisen.state.stateb import StateB
from eisen.common._common import Utils

State = StateB

# date structure which contains the information obtain from flattening.
class FlatteningPacket:
    def __init__(self, asl: CLRList, auxillary: list[CLRList | CLRToken]):
        # the actual asl propagated up.
        self.asl = asl

        # any auxillary lists/tokens which need to be merged in with the first
        # (seq ...) ancestor.
        self.aux = auxillary


# flatten the function calls out of an expression
class Flattener(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self.config = alpaca.config.parser.run("./src/eisen/grammar.gm")
        self.counter = 0

    def run(self, params: State) -> CLRList:
        return self.apply(params.but_with(params.asl)).asl

    def apply(self, params: State) -> FlatteningPacket:
        return self._route(params.asl, params)

    # TODO: allow the reuse of old variables of the same type if they are freed up
    def _produce_var_name(self) -> str:
        self.counter += 1
        return f"__var{self.counter}__"

    @Visitor.for_tokens
    def leaf_(fn, params: State) -> FlatteningPacket:
        return FlatteningPacket(params.asl, [])

    @Visitor.for_default
    def default_(fn, params: State) -> FlatteningPacket:
        children = []
        auxillary = []
        for child in params.asl:
            if isinstance(child, CLRToken):
                children.append(child)
                continue

            if child.type == "call":
                # special case, need to unpack call
                decls_and_call, refs = fn._flatten_call(params.but_with(asl=child))

                # add the necessary variable declarations to the list of auxillaries, as these
                # will be added to the seq before the function is call
                auxillary.extend(decls_and_call)

                # add the return variables of the function as children of the parent asl, if
                # multiple keep them as a tuple.
                if len(refs) > 1:
                    children.append(CLRList(
                        type="tuple",
                        lst=refs,
                        line_number=params.asl.line_number,
                        guid=params.asl.guid,
                        data=params.asl.data))
                elif len(refs) == 1:
                    children.append(refs[0])
                # if no refs, then nothing to add.
            else:
                packet = fn.apply(params.but_with(asl=child))
                children.append(packet.asl)
                auxillary += packet.aux

        return FlatteningPacket(
            asl=CLRList(
                type=params.asl.type,
                lst=children,
                line_number=params.asl.line_number,
                guid=params.asl.guid,
                data=params.asl.data),
            auxillary=auxillary)

    @Visitor.for_asls("seq")
    def seq_(fn, params: State) -> tuple[CLRList, list[CLRList]]:
        children = []
        for child in params.asl:
            if child.type == "call" and not adapters.Call(params.but_with(asl=child)).is_print():
                decls_and_call, _ = fn._flatten_call(params.but_with(asl=child))
                children += decls_and_call
            else:
                packet =  fn.apply(params.but_with(asl=child))

                # add the auxillary asls/tokens first (these include necessary temporary
                # variable declarations). Only then add the propagated asl.
                children += packet.aux + [packet.asl]

        return FlatteningPacket(
            asl=CLRList(
                type=params.asl.type,
                lst=children,
                line_number=params.asl.line_number,
                guid=params.asl.guid,
                data=params.asl.data),
            auxillary=[])

    # note, we do not need the wrangler to cover asls_of_type "call" because
    # all (call ...) lists should be caught and handled in their containing list
    def _flatten_call(fn, params: State) -> tuple[list[CLRList], list[CLRList]]:

        # this will flatten the (params ...) component of the (call ...) list.
        packet = fn.apply(params.but_with(asl=params.asl.second()))

        # get the asl of type (fn <name>)
        node = adapters.Call(params)
        asl_defining_the_function = node.get_asl_defining_the_function()

        # the third child is (rets ...)
        asl_defining_the_function_return_type = asl_defining_the_function.third()

        if not asl_defining_the_function_return_type:
            decls = []
            refs = []
        else:
            decls, refs = fn._unpack_function_return_type(params.but_with(
                asl=asl_defining_the_function_return_type))

        decls = [Flattener._make_code_token_for(txt) for txt in decls]
        refs = [Flattener._make_code_token_for(txt) for txt in refs]

        # add flattened parts as code tokens
        for ref in refs:
            packet.asl._list.append(Flattener._make_code_token_for(f"(addr {ref.value})"))

        fn_instance = node.get_fn_instance()
        fn_name = fn_instance.get_full_name()

        # missing a close paren as we need to add the (params ...) which is added as
        # an asl, not a token, because we don't yet have the ability to transmute it.
        # TODO:
        suffix = "_constructor" if fn_instance.is_constructor else ""
        decls.append(Flattener._make_code_token_for(f"(call (fn {fn_name}{suffix})"))
        decls.append(packet.asl)
        decls.append(Flattener._make_code_token_for(")"))

        # finally, add any declarations from flattening the (params ...) component of
        # this call list before the declarations for this call list. this order is
        # important as auxillary statements from flattening (params ...) are hard
        # dependencies for this call list.
        decls = packet.aux + decls
        return decls, refs

    @classmethod
    def _make_code_token_for(cls, txt: str) -> CLRToken:
        return CLRToken(type_chain=["code"], value=txt)

    def _unravel_scoping(self, asl: CLRList) -> CLRList:
        if asl.type != "::" and asl.type != "fn":
            raise Exception(f"unexpected asl type of {asl.type}")

        if asl.type == "fn":
            return asl
        return self._unravel_scoping(asl=asl.second())

    # return a tuple of two lists. the first list contains the code for the declaration
    # of any temporary variables. the second list contains the code for the return
    # variables of the function
    def _unpack_function_return_type(self, params: State) -> tuple[list[str], list[str]]:
        if params.asl.first().type == "prod_type":
            decls, refs = self._unpack_prod_type(params.but_with(asl=params.asl.first()))
        else:
            decls, refs = self._unpack_type(params.but_with(asl=params.asl.first()))
        return decls, refs

    # TODO: fix
    # type actually looks like (: n (type int))
    def _unpack_type(self, params: State) -> tuple[list[str], list[str]]:
        type = params.but_with(asl=params.asl.second()).get_returned_type()
        prefix = "struct_" if type.is_struct() else ""
        type_name = Utils.get_name_of_type(
            type=type,
            mod=type.mod)

        var_name = self._produce_var_name()
        return [f"({prefix}decl (type {type_name}) {var_name})"], [f"(ref {var_name})"]

    def _unpack_prod_type(self, params: State) -> tuple[list[str], list[str]]:
        all_decls, all_refs = [], []
        for child in params.asl:
            decls, refs = self._unpack_type(params.but_with(asl=child))
            all_decls.extend(decls)
            all_refs.extend(refs)

        return all_decls, all_refs

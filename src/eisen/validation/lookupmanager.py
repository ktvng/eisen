from __future__ import annotations

from alpaca.clr import AST
from alpaca.concepts import Module, Context, Type, Instance

class LookupManager():
    """manages all lookup logic for resolving instances"""

    @classmethod
    def resolve_module_from_base(cls, global_module: Module, module_ast: AST):
        pass

    @classmethod
    def resolve_module_from_local(cls, current_module: Module, module_ast: AST):
        pass


    @classmethod
    def resolve_type_in_module(cls, name: str, mod: Module):
        return mod.get_defined_type(name)


    @classmethod
    def resolve_local_reference(cls, name: str, context: Context) -> Instance | None:
        return context.get_instance(name)

    @classmethod
    def resolve_function_references_by_name(cls, name: str, mod: Module) -> list[Instance]:
        return mod.get_all_function_instances_with_name(name)

    @classmethod
    def resolve_function_reference_by_signature(cls, name: str, argument_type: Type, mod: Module) -> Instance:
        return mod.get_function_instance(name, argument_type)

    @classmethod
    def resolve_reference(cls, name: str, context: Context, mod: Module, argument_type: Type = None) -> Instance | None:
        # first try resolving the reference as a local_reference
        resolved_ref = LookupManager.resolve_local_reference(name, context)

        # try resolving the reference as a method via its signature
        if resolved_ref is None and argument_type is not None:
            resolved_ref = LookupManager.resolve_function_reference_by_signature(name, argument_type, mod)

        # try resolving the reference purely by name
        if resolved_ref is None:
            resolved_refs = LookupManager.resolve_function_references_by_name(name, mod)
            if len(resolved_refs) > 1:
                raise Exception(f"expected only one reference, but got multiple with {name}")
            if len(resolved_refs) == 1:
                resolved_ref = resolved_refs[0]
        return resolved_ref


    @classmethod
    def resolve_local_reference_type(cls, name: str, context: Context) -> Type | None:
        return context.get_reference_type(name)

    @classmethod
    def resolve_function_reference_types_by_name(cls, name: str, mod: Module) -> list[Type]:
        return [i.type for i in mod.get_all_function_instances_with_name(name)]

    @classmethod
    def resolve_function_reference_type_by_signature(cls, name: str, argument_type: Type, mod: Module) -> Type:
        function_instance = mod.get_function_instance(name, argument_type)
        return function_instance.type if function_instance is not None else None

    @classmethod
    def resolve_reference_type(cls, name: str, context: Context, mod: Module, argument_type: Type = None) -> Type | None:
        # first try resolving the reference as a local_reference
        resolved_type = None
        if context:
            resolved_type = LookupManager.resolve_local_reference_type(name, context)

        # try resolving the reference as a method via its signature
        if resolved_type is None and argument_type is not None:
            resolved_type = LookupManager.resolve_function_reference_type_by_signature(name, argument_type, mod)

        # try resolving the reference purely by name
        if resolved_type is None:
            resolved_types = LookupManager.resolve_function_reference_types_by_name(name, mod)
            if len(resolved_types) > 1:
                raise Exception(f"expected only one reference, but got multiple with {name}")
            if len(resolved_types) == 1:
                resolved_type = resolved_types[0]
        return resolved_type


    @classmethod
    def resolve_defined_type(cls, name: str, mod: Module):
        return mod.get_defined_type(name)

    resolve_struct_type = resolve_defined_type
    resolve_interface_type = resolve_defined_type
    resolve_variant_type = resolve_defined_type

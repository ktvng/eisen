from __future__ import annotations
import dataclasses
from dataclasses import dataclass, field

from typing import Any, Type as TypingType, ClassVar

class Corpus:
    """
    The collection of all known types.
    """

    def __init__(self) -> None:
        self.types: dict[str, Type2] = {}

    def get_type(self,
                 name: str,
                 environmental_namespace: str | None,
                 specified_namespace: str | None) -> Type2 | None:

        namespaces = Namespaces.get_namespaces_to_lookup_in_order(
            environmental_namespace, specified_namespace)

        for ns in namespaces:
            if found_type := self.types.get(RealizedType.get_uuid_str_for(name, ns), None):
                return found_type
        return None

    def add_type(self, type_: RealizedType):
        self.types[type_.get_uuid_str()] = type_

class Namespaces:
    @staticmethod
    def _parse_namespace(namespace: str) -> list[str]:
        return namespace.split("::")

    @staticmethod
    def _get_parent_namespaces_in_order(environmental_namespace: str) -> list[str]:
        """
        For the environmental namespace A::B::C, we want to check, in this order,
        A::B::C, A::B, then A
        """
        parts = Namespaces._parse_namespace(environmental_namespace)

        # For a namespace A::B, we want to check A::B, then A, so the logic
        # above is actually going to omit the namespaces in reverse order

        # The last namespace to check is the global namespace. If the environmental
        # namespace is the global namespace, then it will be checked, as parts will be
        # [''], but if there is some environment namespace, then '' will never appear in
        # parts
        parent_namespaces = [""] if not environmental_namespace else []
        for i in range(len(parts)):
            parent_namespaces.append("::".join(parent_namespaces[0 : i+1]))

        # Reverse to return the correct order
        parent_namespaces.reverse()
        return parent_namespaces

    @staticmethod
    def join(parent: str, child: str) -> str:
        return parent + "::" + child

    @staticmethod
    def get_namespaces_to_lookup_in_order(
            environmental_namespace: str,
            specified_namespace: str | None) -> list[str]:

        # If no namespace is specified, resolve the type my moving up through parents
        # of the environmental_namespace
        if specified_namespace is None:
            return Namespaces._get_parent_namespaces_in_order(environmental_namespace)

        # There is no environmental namespace for type definitions/declarations
        if environmental_namespace is None:
            return [specified_namespace]


        # If the specified namespace starts with "::", then it is an absolute path and
        # is exactly the namespace to use
        if specified_namespace.startswith("::"):
            # Remove the leading "::"
            return [specified_namespace[2:]]

        # Otherwise we consider the specified namespace (1) as a child of the environmental
        # namespace, and then (2) as an absolute path.
        return [Namespaces.join(environmental_namespace, specified_namespace), specified_namespace]

class TypeFactory2:
    def __init__(self,
                 corpus: Corpus,
                 classes: dict[str, Type2]) -> None:

        self.classes = classes
        self.corpus = corpus

    def produce_type(self, type_: Type2, **options) -> Type2:
        match type_:
            case VoidType():
                return type_
            case NilType():
                return type_
            case RealizedType():
                return self.create_type_manifest(type_, **options)
            case TypeManifest():
                return dataclasses.replace(type_, **options)
            case _:
                return type_

    def create_type_manifest(self, type_: RealizedType, **options) -> TypeManifest:
        type_manifest: TypingType[TypeManifest] = self.classes["manifest"]
        return type_manifest(corpus=self.corpus, name=type_.name, namespace=type_.namespace, **options)

    def add_declared_to_known_corpus(self, type_: Type2):
        self.corpus.add_type(type_)

    def declare_novel_type(self, name: str, namespace: str):
        novel_type: TypingType[NovelType] = self.classes["novel"]
        self.add_declared_to_known_corpus(novel_type(name=name, namespace=namespace))

    def declare_void_type(self):
        void_type: TypingType[VoidType] = self.classes["void"]
        self.add_declared_to_known_corpus(void_type())

    def produce_void_type(self, **options) -> Type2:
        void_type: TypingType[VoidType] = self.classes["void"]
        return void_type(**options)

    def declare_nil_type(self):
        nil_type: TypingType[NilType] = self.classes["nil"]
        self.add_declared_to_known_corpus(nil_type())

    def produce_nil_type(self, **options) -> Type2:
        nil_type: TypingType[NilType] = self.classes["nil"]
        return nil_type(**options)

    def produce_function_type(self, args: Type2, rets: Type2, **options) -> TypeManifest:
        function_type: TypingType[FunctionType] = self.classes["function"]
        return function_type(
            argument=args,
            returnValue=rets, **options)

    def produce_tuple_type(self, components: list[TypeManifest], **options) -> TypeManifest:
        tuple_type: TypingType[TupleType] = self.classes["tuple"]
        return tuple_type(
            components=components, **options)

    def declare_type(self, name: str, namespace: str):
        type_declaration: TypingType[TypeDeclaration] = self.classes["declaration"]
        self.add_declared_to_known_corpus(type_declaration(name=name, namespace=namespace))

    def define_struct_type(self,
            struct_name: str,
            namespace: str,
            attribute_names: list[str],
            attribute_types: list[Type2]):

        struct_type: TypingType[StructType] = self.classes["struct"]
        new_type = struct_type(
            name=struct_name,
            namespace=namespace,
            component_names=attribute_names,
            components=attribute_types)
        print(new_type)
        self.add_declared_to_known_corpus(new_type)

    def define_trait_type(self,
            trait_name: str,
            namespace: str,
            attribute_names: list[str],
            attribute_types: list[Type2]):

        trait_type: TypingType[TraitType] = self.classes["trait"]
        self.add_declared_to_known_corpus(trait_type(
            name=trait_name,
            namespace=namespace,
            component_names=attribute_names,
            components=attribute_types))

@dataclass(frozen=True, kw_only=True)
class Type2:
    modifier: Any = None
    nilable: bool = None

    def delegated(self):
        raise Exception(f"Not implemented for {self}")

    def get_uuid_str(self) -> str: self.delegated()

    def get_direct_attribute_name_type_pairs(self) -> list[tuple[str, Type2]]: self.delegated()
    def get_all_attribute_name_type_pairs(self) -> list[tuple[str, Type2]]: self.delegated()
    def has_member_attribute_with_name(self, name: str) -> bool: self.delegated()
    def get_member_attribute_by_name(self, name: str) -> Type2: self.delegated()
    def get_all_component_names(self) -> list[str]: self.delegated()

    def get_return_type(self) -> Type2: self.delegated()
    def get_first_parameter_type(self) -> Type2: self.delegated()
    def get_argument_type(self) -> Type2: self.delegated()

    def is_function(self) -> bool: return False
    def is_struct(self) -> bool: return False
    def is_trait(self) -> bool: return False
    def is_novel(self) -> bool: return False
    def is_tuple(self) -> bool: return False
    def is_void(self) -> bool: return False
    def is_nil(self) -> bool: return False

    def is_vec(self) -> bool: return False
    def is_parametric(self) -> bool: return False

    def unpack(self) -> list[Type2]: self.delegated()

    def _get_modifier_str(self) -> str:
        modifier = str(self.modifier) if self.modifier is not None else ""
        if modifier: modifier += " "
        return modifier


@dataclass(frozen=True, kw_only=True)
class ConstructedType(Type2):
    """
    A constructed type is one which is built using well-defined composition procedures from other
    realized types or constructed types.
    """

@dataclass(frozen=True, kw_only=True)
class FunctionType(ConstructedType):
    """
    A function type contains two child type manifests: an argument type and a return type
    """
    argument: Type2
    returnValue: Type2

    def is_function(self) -> bool:
        return True

    def get_return_type(self) -> Type2:
        return self.returnValue

    def get_first_parameter_type(self) -> Type2:
        return self.get_argument_type().unpack()[0]

    def get_argument_type(self) -> Type2:
        return self.argument

    def unpack(self) -> list[Type2]:
        return [self]

    def __str__(self) -> str:
        args = str(self.argument)
        if args[0] != "(": args = f"({args})"
        return self._get_modifier_str() + f"{args} -> {str(self.returnValue)}"

@dataclass(frozen=True, kw_only=True)
class TupleType(ConstructedType):
    """
    Similar to a struct type, but not realized (no-name), a tuple type also does not associate
    names with child attributes.
    """
    components: list[Type2]

    def is_tuple(self) -> bool:
        return True

    def unpack(self) -> list[Type2]:
        match len(self.components):
            case 0: return [VoidType()]
            case _: return [tm.get_type() for tm in self.components]

    def __str__(self) -> str:
        return f"({', '.join([str(c) for c in self.components])})"


@dataclass(frozen=True, kw_only=True)
class RealizedType(Type2):
    """
    A realized type is one which is one with a unique name. For instance, structs, primitives,
    and traits are all examples of realized types as a unique name is associated to each.

    Realized types may refer to other realized types, or even themselves.
    """
    name: str
    namespace: str

    def get_uuid_str(self) -> str:
        """
        Return a globally unique identifier for this type
        """
        return self._get_modifier_str() + self.namespace + "::" + self.name

    @staticmethod
    def get_uuid_str_for(name: str, namespace: str) -> str:
        return namespace + "::" + name

@dataclass(frozen=True, kw_only=True)
class TypeDeclaration(RealizedType):
    """
    A stand-in for a struct/trait type that has been declared but not finalized
    """

@dataclass(frozen=True, kw_only=True)
class NovelType(RealizedType):
    """
    A novel type is a unique, standalone type bound to a name, used to represent primitives and
    other fundamental types.
    """

    def is_novel(self) -> bool:
        return True

@dataclass(frozen=True, kw_only=True)
class VoidType(RealizedType):
    """
    A realized type used to represent the absence of any type.
    """
    NAME: ClassVar[str] = "void"
    NAMESPACE: ClassVar[str] = ""
    name: str = field(init=False, default=NAME)
    namespace: str = field(init=False, default=NAMESPACE)

    def is_void(self) -> bool:
        return True

    def __str__(self) -> str:
        return "void"

@dataclass(frozen=True, kw_only=True)
class NilType(RealizedType):
    """
    A realized type use to represent nil
    """
    NAME: ClassVar[str] = "nil"
    NAMESPACE: ClassVar[str] = ""
    name: str = field(init=False, default=NAME)
    namespace: str = field(init=False, default=NAMESPACE)

    def is_nil(self) -> bool:
        return True

@dataclass(frozen=True, kw_only=True)
class _StructLikeType(RealizedType):
    classification: str
    component_names: list[str]
    components: list[Type2]

    def unpack(self) -> list[Type2]:
        match len(self.components):
            case 0: return [VoidType()]
            case _: return [tm.get_type() for tm in self.components]

    def get_direct_attribute_name_type_pairs(self) -> list[tuple[str, Type2]]:
        return [(n, t)for n, t in zip(self.component_names, self.components)]

    def get_all_attribute_name_type_pairs(self) -> list[tuple[str, Type2]]:
        return [(n, t)for n, t in zip(self.component_names, self.components)]

    def has_member_attribute_with_name(self, name: str) -> bool:
        return any(n == name for n in self.component_names)

    def get_member_attribute_by_name(self, name: str) -> Type2:
        for n, t in zip(self.component_names, self.components):
            if n == name:
                return t
        return None

    def get_all_component_names(self) -> list[str]:
        return self.component_names

    def __str__(self) -> str:
        s = self.classification + " " + self.get_uuid_str() + "{\n"
        for n, t in zip(self.component_names, self.components):
            s += "  " + n + ": " + str(t) + "\n"
        return s + "}"

@dataclass(frozen=True, kw_only=True)
class TraitType(_StructLikeType):
    """
    A trait type contains a list of child functions which must be defined if a struct is to
    implement that trait.
    """
    classification: str = field(init=False, default="trait")

    def is_trait(self) -> bool:
        return True

@dataclass(frozen=True, kw_only=True)
class StructType(_StructLikeType):
    """
    A struct type contains a list of type manifests for child attributes.
    """
    classification: str = field(init=False, default="struct")

    def is_struct(self) -> bool:
        return True




@dataclass(frozen=True, kw_only=True)
class TypeManifest(Type2):
    """
    A type manifest refers to another type. It may add additional information such as bindings,
    const-ness, modifiers, or nullability.
    """
    corpus: Corpus
    name: str
    namespace: str

    def get_type(self) -> Type2:
        """
        Return the type referenced by this manifest.
        """
        return self.corpus.get_type(self.name,
                                    environmental_namespace=None,
                                    specified_namespace=self.namespace)

    def get_uuid_str(self) -> str: RealizedType.get_uuid_str_for(self.name, self.namespace)

    def get_direct_attribute_name_type_pairs(self) -> list[tuple[str, Type2]]:
        return self.get_type().get_direct_attribute_name_type_pairs()

    def get_all_attribute_name_type_pairs(self) -> list[tuple[str, Type2]]:
        return self.get_type().get_all_attribute_name_type_pairs()

    def has_member_attribute_with_name(self, name: str) -> bool:
        return self.get_type().has_member_attribute_with_name(name)

    def get_member_attribute_by_name(self, name: str) -> Type2:
        return self.get_type().get_member_attribute_by_name(name)

    def get_all_component_names(self) -> list[str]:
        return self.get_type().get_all_component_names()

    def _not_supported(self): raise Exception("This function is not supported for TypeManifests")

    def get_return_type(self) -> Type2: self._not_supported()
    def get_first_parameter_type(self) -> Type2: self._not_supported()
    def get_argument_type(self) -> Type2: self._not_supported()

    def is_function(self) -> bool: return False
    def is_struct(self) -> bool: self.get_type().is_struct()
    def is_trait(self) -> bool: self.get_type().is_trait()
    def is_novel(self) -> bool: return False
    def is_tuple(self) -> bool: return False
    def is_void(self) -> bool: return False
    def is_nil(self) -> bool: return False
    def is_vec(self) -> bool: return False
    def is_parametric(self) -> bool: return False

    def unpack(self) -> list[Type2]:
        return self.get_type().unpack()

    def __str__(self) -> str:
        return self._get_modifier_str() + RealizedType.get_uuid_str_for(self.name, self.namespace)

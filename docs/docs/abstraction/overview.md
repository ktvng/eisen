# Overview
Abstraction is an incredibly powerful tool. Instead of writing targeted code to every scenario or use case, abstraction allows the developer to encode their logic in an _abstracted_ way such that it can be applicable to many particular cases. 

Object oriented programming languages rely on a class hierarchy or inheritance structure to achieve logical abstraction. Breaking a large program into separate classes provides separation of concerns, and having subclasses inherit from superclasses facilitates code reuse and polymorphism. All of these ideas are intended to improve the developer experience, and yield an end product source code which is easier to understand and maintain.

However, inheritance is difficult to do right, and often misused. Modern advice favors composition over inheritance, _has-a_ relationships over _is-a_ relationships. Eisen follows this approach; it has no notion of inheritance. Instead, abstraction is accomplished through other channels that we argue, provide the same desired functionality as inheritance, but in a cleaner, less complex way.

## Polymorphism
In loose terms, polymorphism represents the desire to have a single form which may be manifested in different ways. One key example with subtyping polymorphism, is that, given `Dog` and `Cat` as two subclasses of the `Animal` class, an `Animal` variable may be used to refer to either a `Dog` or `Cat`. The same form, `Animal`, may be manifested in one of two ways. 

Subtyping polymorphism is useful because it reduces hard dependencies in code. By methods and variables of parent types, code is less bound to a single implementation, but rather bound instead to a public interface. However, this desirable decoupling is only possible if the Liskov Substitution Principle holds, which states that instances of a superclass should be interchangeable with instances of a subclass without breaking the application.

When a subtype overwrites functionality inherited from its parent class, we run the risk of breaking Liskov substitutability. This leads to the general conclusion that, as a best practice, classes should be closed for modification, and open for extension (see the SOLID principle)

In following this guideline, Eisen does not implement inheritance; rather, polymorphism is achieved in one of two ways. We distinguish between runtime and compile-time polymorphism. 

Without polymorphism, all instances of the same type should behave isomorphically (ignoring differences in the configuration of member attributes).

**Runtime polymorphism** is the ability to, during runtime, define different instances of the same type which exhibit different functionality, despite containing the same "data". This can be achieved through the use of member functions, which allow structs to store pointers to functions that can be hot swapped at runtime.

**Compile-time** polymorphism is the ability to, at compile time, define different functionality for different implementations of a type. This is achieved through interfaces.

## Code Reuse
Often, it is desirable to write shared functionality and logic only once, even if it is necessary to be used by different objects and in different places. Traditionally, inheriting from a subclass provides the developer the ability to reuse code from the superclass inside the subclass. But most languages do not support multiple inheritance, so code reuse in this way is not always convenient nor extensible.

Instead, Eisen supports code resuse through struct embedding (analogous to mixins) and interface methods.

In general, most experts recommend favoring composition over inheritance; if a class requires the functionality of another class, that can be achieved by associating an instance of ths secondary class with the new class, and not having the new class inherit from the secondary class. **Struct embedding** is a syntactic shortcut for this paradigm. Embedded structs are simply member attributes. However, embedding the struct allows for the functionaly of these embedded member attributes to be called with less overhead, as if the functionality as inherited.

**Interface Methods** allow common functionality over an interface to be written once and applied to any struct which implements the interface.

## Functionality Namespaces
Object oriented programming is also useful in that objects group together, and can limit, what functionality is available to the developer. Some objects have internal data that must meet certain requirements or conditions; and by only allowing internal state to be modified by public methods, objects can effectively protect the internal state of an object from being misconfigured. 

Eisen provides **Variants** to allow the developer to demarcate certain conditions or structure over data. Variants are defined over a pre-existing base struct, but provide assurances as to the internal state of the struct during runtime. To protect this state from misconfiguration, variants may limit functionality of the pre-existing struct, or even add additional functionality to it. 

Variants provide a loose guarantee that a given object confirms to some required internal state; it is still the perogative of the programmer ensure that all functionality available to a variant does not improperly change the object's internal state.
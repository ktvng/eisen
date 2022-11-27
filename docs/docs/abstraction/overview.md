# Overview
Abstraction is an incredibly powerful tool. Instead of writing targeted code to every scenario or use case, abstraction allows the developer to encode their logic in an _abstracted_ way such that it can be applicable to many particular cases. 

Object oriented programming languages rely on a class hierarchy or inheritance structure to achieve logical abstraction. Breaking a large program into separate classes provides separation of concerns, and having subclasses inherit from superclasses facilitates code reuse and polymorphism. All of these ideas are intended to improve the developer experience, and yield an end product source code which is easier to understand and maintain.

However, inheritance is difficult to do right, and often misused. Modern advice favors composition over inheritance, _has-a_ relationships over _is-a_ relationships. Eisen follows this approach; it has no notion of inheritance. Instead, abstraction is accomplished through other channels that we argue, provide the same desired functionality as inheritance, but in a cleaner, less complex way.

## Polymorphism
In loose terms, polymorphism represents the desire to have a single form which may be manifested in different ways. One key example with subtyping polymorphism, is that, given `Dog` and `Cat` as two subclasses of the `Animal` class, an `Animal` variable may be used to refer to either a `Dog` or `Cat`. The same form, `Animal`, may be manifested in one of two ways. 

Subtyping polymorphism is useful
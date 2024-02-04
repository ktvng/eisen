# Structs
Without proper classes, structs provide Eisen the ability to construct more complex data types. Structs are declared similarly as in C, with an additional requirement that a cannonical constructor is required. This constructor is the sole way in which a new struct may be initialized.

```eisen
struct Document {
    name: str
    data: byte[]

    create(name: str, data: byte[]) -> new self: Document {
        self.name = name
        self.data = data
    }

    destroy(new self: Document) {
        free(self.data)
    }
}
```

The constructor is required to return a type of the defined struct. By convention, this is given the name `self`.

In addition, if the defined struct manages any heap allocated memory, an option destructor may need to be defined to cleanup any memory used internally by the struct.

## Struct Functions
Eisen does not explicity associate a struct with a given selection of methods (as one would expect with classes in standard Object Oriented Programming). Instead, Eisen provides an alternative paradigm by which struct methods are global methods which may be associated with a struct by the compiler.

```eisen
struct Circle {
    x: int
    y: int
    radius: flt

    create(radius: int) -> new self: Circle {
        self.x = x
        self.y = y
        self.radius = radius
    }
}

fn getArea(new self: Circle) -> area: flt {
    area = math::pi * self.radius ** 2
}

fn main() {
    let myCircle = Circle()
    getArea(myCircle)
    myCircle.getArea()
}
```

In the example above, `getArea` is defined as a global method which takes in a `Circle` as its first parameter. The convention for struct methods is to name the "parent object" `self`.

Calling `getArea` cand be done in the C style convention, or by using the `.` operator after a `Circle` instance. This latter syntax is simply shorthand for the C style convention, but gives us the benefit of conceptualizing the global method as an instance method.

## Member Functions
Functions are also treated as first-class entities by Eisen, and structs may also be written where the "data" stored by the struct is itself a function

```eisen
struct ShortestPathSolver() {
    impl: (g: Graph, start: Node, end: Node) -> shortestPathLen: int

    create(impl: (Graph, Node, Node) -> int) -> new self: ShortestPathSolver {
        self.impl = impl
    }
}

fn dijkstrasAlgo() { ... }
fn depthFirstSearch() { ... }

fn run(
    new self: ShortestPathSolver,
    g: Graph,
    start: Node,
    end: Node) -> shortestPathLen: int
{
    shortestPathLen = self.impl(g, start, end)
}

fn main() {
    let solver = ShortestPathSolver(dijkstrasAlgo)
    solver.run(...)
}

```

In the example above, the `ShortestPathSolver` may be created with some implementation of the actual algorithm to use. That algorithm is stored as the `impl` field, and can be invoked using the familiar syntax of `self.impl(...)`.

The compiler is able to resolve any ambiguity if `impl` is a global method (which should take as its first argument, some instance of `ShortestPathSolver`) or if `impl` is a member function of the `ShortestPathSolver` struct. In the event of ambiguity, the compiler will throw an error and the developer must resolve the naming conflict.

## Reassignment
After declaration, reassigment of structs is expressly prohibited. Consider the `Document` struct defined above and reproduced below,

```eisen
struct Document {
    name: str
    data: byte[]

    create(name: str, data: byte[]) -> new self: Document {
        self.name = name
        self.data = data
    }

    destroy(new self: Document) {
        free(self.data)
    }
}

fn readDocument(path: str) -> newDoc: Document {
    // read file from path into newDoc
}
```

and the following code (which does not compile)

```eisen
let doc1 = readDocument("./doc1")
doc1 = readDocument("./doc2")
```

In this case, `doc1` initially gets populated with a heap allocated byte buffer corresponding to `"./doc1"`. But upon reassigning, what happens to this data? To avoid a memory leak, we'd need to free it, which means we'd need an implicit call to the destructor.

While C++ allows this operation for objects, it requires copy/move constructors, and this adds [complexity](https://en.cppreference.com/w/cpp/language/rule_of_three). Semantically, reassignment of structs is often a logical error: in higher level languages like Java, reassignment of this sort is cannonical; objects are pointers and it makes sense to reassign pointers. Reassignment, semantically, states that _this pointer refer to the object of this other pointer_.

But if the reference that's being reassigned refers to the actual memory allocation of some object, then semantically it does not make sense to say that _this memory allocation should now refer to this other memory allocation_.

For this reason, Eisen prohibits the reassignment of struct entities. Instead, the concept of Variables is introduced.

# Syntax
This page contains a high level overview of how different programming concepts are realized in Eisen. All constructions here should be familiar to anyone who as worked with Go/Rust before.

## Entry Point
Similar to C/C++, Eisen requires a `main` method to be defined as the entry point of a program. A single project must only contain one `main` method.

```eisen
fn main() {
    print("hello world")
}
```

## Variables
Eisen is statically typed with inference. Variables are defined by providing a name in general, a type (unless inference is possible).

```eisen
let x: int
x = 4
let y = 4
```

## Types
Currently, there are three primitive types, `int`, `bool`, and `flt`. Primitive types must be defined with the `let` keyword, and are the only types passed by value into functions.

Primitives can be reassigned, and all arithmetic operators are defined for them, in the obvious way

```eisen
let x = 4.2;
let y = x * 4
x += y
```

There is a built-in `str` type for strings, but as this type encapsulates some heap allocated buffer, `str` should not be considered a primitive, and in fact, is not passed by reference.

Eventually, we plan to support other primitive types such as `long`, `unsigned int`, `double`, etc.

### Constructed Types
Users may also define their own structs to be used as types. These are collectively called constructed types. Constructed types may be composites of primitive types, and may also contain references to additional heap allocated memory.

When defining a struct, the programmer must also define the `create` construction so that the struct can be initialized properly.


```eisen
struct vector {
    direction: flt
    magnitude: flt

    create() -> new self: vector {
        self.direction = 0
        self.magnitude = 0
    }
}
```

Unlike primitive types, Eisen restricts the reassignment of constructed types in order to correctly manage the lifetime of the heap allocated memory.

## Functions
The standard approach for defining a function in Eisen requires a user to provide the a complete return clause after the `->` symbol which includes both the return type, but also a name for the returned parameter.

In the example below, `sum` must be fully initialized within the function, after which the function is allowed to return, either by specifying and empty `return` keyword, or by reaching the end of the function. For more details about why we chose this approach, see [Functions](/intro/functions).

```eisen
fn add(x: int, y: int) -> sum: int {
    sum = x + y
    return  // optional
}
```

Tuples are built-in to allow for multiple return values

```eisen
fn quadratic(a: int, b: int, c: int) -> zero1: flt, zero2: flt {
    let discriminant = sqrt(b ** 2 - 4 * a * c)
    zero1 = (-b + discriminant) / (2 * a)
    zero2 = (-b - discriminant) / (2 * a)
}
```

## Comments
We follow C/C++ conventions for comments.

```eisen
fn main() {
    // Say hello to the programmer!
    print("hello world")
}
```

Eventually we do plan to support multiline comments using the `/* comment */` syntax.

## Conditionals
```eisen
fn max(a: int, b: int) -> r: int {
    if (a > b) {
        r = a
    }
    else {
        r = b
    }
}
```

## Loops: while
```eisen
let x = 0
while (x < 10) {
    print("%i", x)
    x += 1
}
```

# Variables
To allow Eisen to operate at the C/C++ level, it is necessary to make the distinction between two different concepts: allocated object and references to objects.

An object can be allocated using the `let` keyword. This sets aside a given amount of space for the object on the stack.

```eisen
struct Object {
    ...
}

fn main() {
    let myObj = Object()
}
```

The reference `myObj` can be used to manipulate the memory it refers to. But it is also bound to this single instance of `Object`, as it refers to a single and particular memory allocation. There are many cases where it is useful or necessary to have some type of reference which we can reassign.

```eisen
let o1: Object
let o2: Object

var bestCandidate: Object

if (...) {
    bestCandidate = o1
}
else {
    bestCandidate = defaultObj
}

// common functionality using the bestCandidate
```

In the example above, we want to be able to determine the `bestCandidate` and then use this `Object`. We don't need a new memory allocation, we just need a _variable_ that can refer to existing memory allocations, and be assigned, or ever reassigned to the proper one.

Eisen give us this ability with the `var` keyword. Whereas the `let` keyword establishes a new memory allocation, the `var` keyword serves the purpose of a pointer. It provides access to some pre-existing memory allocation. It can be assigned or reassigned as needed without restriction.


## Primitives
Note that primitive types do not share this same problem because we can in fact modify the memory of the primitive object in place. Primitive types are the simplest examples of Data Structs.

# Variants
Typing is also useful to provide contextual clues as to the purpose of data. For instance, one may choose to create a new type definition to provide additional context, as illustrated by the following example.

```c
typedef int secs
secs delayTime = 5
```

Often, it is the case where the structure of the data may not change, but the usage or state of the data may change during runtime, and we may want to encode this using type information. This often occurs when we would wish to enforce a predicate on a given type.

For instance, it is useful to convert the `str` struct to some `Path` type if the string is a well formed file path. In doing so, we also require additional functionality for `Path` types, such as decomposing the `Path` into directory and file.

When the underlying structure or memory required to represent data does not change, but the data satisfies some additional constraint or additional structure, Eisen permits the developer to define a Variant on the underlying struct to encode this semantic change.

Variants may either add additional functionality or restrict existing functionality to preserve the additional constraints on the data.

```eisen
variant Path of str {
    is(self: new str) -> bool {
        if (/* check if well formed URL */) {
            return true
        }

        return false
    }

    // restrict append method as arbitrary appends
    // may not yield a valid file Path
    @deny (append)
}

// The append method may be redefined as the original is disabled
fn append(self: new Path, relativePath: Path) -> result: Path {
    result = self.as(str).append(relativePath[2: ]).as(Path)
}

fn getDirectory(self: new Path) -> directory: Path {
    if (self.isPath) {
        directory = self
    }
    else {
        let fileStart = self.indexOf("/", reversed = True)
        directory = self[ : fileStart].as(Path)
    }
}
```

A couple points stand out from the following example:

1. Existing methods defined over the underlying struct may be restricted with the `@deny` clause. This may be necessary to protect the structure the underlying data, so that the variant condition is preserved. Similarly, one may opt to use the `@allow` clause to specify only which methods from the underlying struct to permit.

2. To define a variant, the `is` operator must also be overloaded to determine whether the underlying struct satisfies the conditions required by the variant. It is the programmers responsibility to ensure that the condition is met. By default, compiling with optimizations will not check the variant condition before each cast.

3. Casting allows the developer to switch between the underlying struct and the variant types. This may allow usage of methods denied to the variant. It is the programmer's responsibility to ensure that the type predicates are satisfied.

## Usage
A variant can be used by casting from a type. It is the developer's responsibility to ensure that the cast is safe.

```eisen
let myStr = "./path/to/file.txt"
var myPath: Path
if (myPath is Path) {
    myPath = myStr.as(Path)
}
else {
    // handle failure case
}

myPath.getDirectory()
```

Note that variants do not create a new memory allocation. Using variants is equivalent to casting an existing pointer to a pointer of the variant's type. Again, we cannot emphasize this enough, it is the responsibility of the programmer to ensure that variant preconditions are never violated.

When this may be difficult, it may be necessary to check the variant condition explicitly

```eisen
fn somePathOperation(self: new Path) -> status: bool, newPath: Path {
    // some complex operations yields
    let possibleNewPath = ...
    if (possibleNewPath is Path) {
        return true, possibleNewPath.as(Path)
    }

    // we need to supply some default value for the returned Path.
    return false, self
}
```

Or if there is no default value, a nilable return type may be specified

```eisen
fn somePathOperation(self: new Path) -> newPath: Path? {
    // some complex operations yields
    let possibleNewPath = ...
    if (possibleNewPath is Path) {
        return possibleNewPath.as(Path)
    }

    // we can return nil as Path? is nilable
    return nil
}
```

# Functions
If you haven't already, take a look at Functions section in [Syntax 101](/intro/syntax.md#functions) for a high level overview.

Functions map some tuple of input arguments to some tuple of output arguments. The syntax for defining a function follows this convention. Note that names are required for both arguments as well as return values.
```eisen
fn range(numbers: vec[int]) -> min: int, max: int {
    if (numbers.len() == 0) {
        min, max = 0, 0
        return
    }

    min, max = numbers[0], numbers[0]
    for (n in numbers) {
        if (n < min) {
            min = n
        }
        if (n > max) {
            max = n
        }
    }
}

fn main() {
    min, max = range([1, -2, 56, 0, 5])
}
```

As the example shows, requiring return values to have names has several consequences. Primarily, and what may at first be flustering, is that the `return` keyword does not take any arguments. This may take some getting used to.

But before you finalize your own judgements on this convention, we urge you to consider the following points:

## Self-documentation
If we were instead given this function header below, we find ourselves missing crucial pieces of information required to understand what this function does. It takes a list of integers, and it returns two integers; the name of the function, `range` provides contextual clues which _may_ allow us to conclude that this function returns the max and min elements in the list. But without looking at accompanying documentation or, worse, the implementation, we must make assumptions.

```python
def range(numbers: list[int]) -> int, int:
    # implementation
```

Instead, in Eisen, naming the return values provides more context that allows us to understand what's actually going on.

```eisen
fn range(numbers: vec[int]) -> min: int, max: int
```

Of course, this isn't foolproof, and there will be cases where accompanying documentation is advisable or even necessary. But the fundemental point here is that as the author of a function, **you should be able to express what it returns**, and as a consumer of a function, it is important to know what is being returned.

## Clean Functions
A common C++ paradigm is to have the function return only a status code, and to have the _real_ return values passing into the function by reference. Something like this

```cpp
int makeBigObject(BigObj& obj) {
    /* construct the big obj */
    return 1; // success
}

void main() {
    BigObj obj;
    int result = makeBigObject(obj);
}
```

Spend a lot of time working with industry grade C++ and you see this everywhere. Engineers prefer this paradigm as it avoids an unnecessary copy. Consider this:

```cpp
BigObj makeBigObject2() {
    BigObj internalObj; // this is a second allocation
                        // of a BigObj local to makeBigObject2
    /* construct obj */
    return internalObj;
}

void main() {
    BigObj obj; // this is the allocation we care about
    obj = makeBigObject(obj); // this step is a copy!
}
```

If we were to use `makeBigObject2` (and this is the Java) way, then what we're doing is constructing a _second_ `BigObj` inside of `makeBigObject2` (named `internalObj`) and in the main method, we'd be copying `internalObj` into `obj`.

In most cases, the compiler should be smart enough to detect and optimize out this extra allocation and copy, but as C++ developers, we don't trust the compiler.

So the convention in C++ is to pass anything you need to construct into the method as a reference. We argue that this convention is absolutely not clean.

1. It overloads the semantics of a parameter vs return value
2. It obscures the intent of a function. Without carefully examining the signature of the method, we can't be sure what's going on.
3. It just looks kinda bad.

Instead, by requiring return values to be named, Eisen allows us to obtain the performance advantage of this C++ convention cleanly. Return values are never contructed inside a function! They're being passed into the function (as if by reference),

## Parameters <Badge type="info" text="In Development" />
A function can be defined with default arguments.

```eisen
fn add_argument(
    name: str,
    shorthand: str,
    required = false,
    help = "") -> loweredStr: str
{ ... }

```

A function can be called with named arguments.

```eisen
add_argument(
    name = "--input",
    shorthand = "-i",
    help = "input file to be processed")
```

But if a function with optional parameters is assigned to a function object, neither defaults arguments nor named arguments are supported.

::: info
This is because the compiler is no longer able to identify the names/default values of the arguments passed into a function object. In the example below, the type of `myFunction` is purely the method signature of `add_argument`, that is, `(str, str, bool, str) -> void`, with none of the necessary annotations to determine argument names/defaults.
:::

```eisen
let myFunction = add_argument
myFunction("--output", "-o", false, "output file to be written")
```

## Extension Functions
Functions are not defined as 'belonging' to a struct in the same way that functions 'belong' to a class. The syntax `obj.function(...)` is purely shorthand for `function(obj, ...)` which is unraveled by the Eisen compiler. This feature makes defining extension functions trivial. For instance, integers can be treated as objects themselves via extension functions.

```eisen
fn timesTryTo(n: int, f: () -> bool) {
    for (0..n) {
        if (f()) {
            return
        }
    }
}

fn processPayment() {
    ...
}

fn main() {
    5.timesTryTo(processPayment)
}
```

The ability to define the function `timesTryTo` to take the integer parameter first allows us to call it via an integer literal as if it were a function. This simple example leads some very clean, readable code.

The same idea can be applied to extend functionality over structs which the developer may not have direct access over.

# Pointers
Eisen does not explicity have the notion of a pointer, but variables provide the same expressivity. Consider the following code:

```eisen
struct Exception {
    code: int
    msg: str
    ...
}

fn print(ex: Exception) {
    print("%i: %s", ex.code, ex.msg)
}

fn setMessage(var ex: Exception, message: str) {
    ex.msg = message
}
```

We can create a new instance of an `Exception` as well as pointers to this instance as follows.

```eisen
let status = Exception()
var myStatus = status

myStatus.code = 0x00000
myStatus.setMessage("success")
myStatus.print()
```

By using the variable `myStatus`, we can refer to the memory allocation of `status`, and we can invoke all of the same functionality we could when using the original reference to that allocation. Unlike C/C++ where a pointer must be dereferenced before use (either `(*ptr).attr` or `ptr->attr`), Eisen variables have the same syntactic usage as the original `let` defined object. 

By default, all structs are passed by constant reference, and all data structs are passed by value. This avoids unnecessary memory copying, and in general, and gives us the same behavior as Java and other higher level languages.

## Values
A value is a type of constant pointer. Whereas variables can be assigned and reassigned without restriction, a value can only be initialized, after which, reassignment is prohibited. 

```eisen
let status = Exception()
val myStatus = status

// these lines of code are problematic
myStatus.code = 0x00001
myStatus.setMessage("error")

// these lines of code are fine
status.code = 0x00001
myStatus.print()
```

An additional restriction when using values is that beyond the value of the pointer being fixed, the object being pointed to is also treated as immutable. Therefore direct manipulation of `myStatus.code` is prohibited by the compiler. However, as `status` is the original owner of the memory allocation, it is still able to access and modify the memory.

Finally, in the example, `myStatus.print()` is fine as the `print` method takes an instance of `Exception` by constant reference (think of this as by `val`, not by value). The `setMessage` method would generate a compiler error as it recieves the instances as a `var` (a variable reference), and a `val` cannot be coerced into a `var`.

## Mutability and Assignability
Any memory allocated with the `let` keyword retains full permissions over the data allocation. Eisen only provides `val` a way to ensure additional memory safety by treating the memory allocation as immutable. A common convention is to `let` define the allocation as "private".

```eisen
let _status = Exception()
val status = _status
```

In this way, the programmer can convey the information that `_status` is not to be used in a clear and precise way. 

To date, feel that a separate keyword or additional syntactic sugar for this paradigm is not necessary.

The usage `let`, `val`, and `var` is summarized below:
- `let` should be used when a new instance of a struct needs to be allocated. The reference bound by `let` refers to this memory allocation. Data structs and primitives must be defined in this way, and are the only types which, when instantiated by `let`, can be reassigned.
- `var` can be used to create a pointer to an existing memory allocation. It is fully unrestricted and can be reassigned (made to point to a different memory allocation) or even used to modify the memory allocation it points to.
- `val` can be likewise be used to create a pointer to an existing memory allocation. It is restricted in that once assigned, it cannot be reassigned, and it cannot be used to modify the existing memory allocation.

#### Proposed Modifier: ref <Badge type="info" text="In Development" /> 
It may be necessary to introduce another reference class; this would allow the value to be reassgined, but the memory allocation it points to to be immutable. This is useful if ever we need to assign over various `val` references.

### Shortcoming <Badge type="info" text="In Development" />
Consider the scenario where we need to find an element in an array. We want to write a method that encapsulates this functionality; we won't need to modify the array to find the element, but we may want to modify the element we find. We would want something like this

```eisen
fn findFirst(
    items: vec[Obj], 
    criteria: (Obj) -> bool) -> firstMatch: Obj var? 
{
    firstMatch = nil
    for (obj in items) {
        if (criteria(obj)) {
            firstMatch = obj
            return
        }
    }
}
```

But given the current system, a problem emerges. As `items` is being passed into the function by `val`, it's immutable. This is fine everywhere until we get to the line `firstMatch = obj` as we can't assign a `val` reference to a `var` reference (this would allow us to modify the `val` reference, and defeat the purpose of the restriction)

But if we were to call `findFirst` over a vector we fully manage, and can modify, we may want to do something like this.

```eisen
let items = {...}
var match = findFirst(items, someCriteria)
match.modify()
```

One possible solution would be to allow coersion, and have the programmer attest that this is safe themselves.

```eisen
firstMatch = obj.as(var)
```

Or the function could return a `val` and the cast could occur on the caller side:

```eisen
var match = findFirst(items, someCriteria).as(var)
```

This second option is more appealing, the caller has the full picture, or at least a fuller picture.

Essentially, the dilemma boils down to the fact that we may not need to change a parameter in a method, but we may want that method to supply a mutable reference to part of that parameter, so that we can change it in the future.

Or maybe we don't actually need additional machinery here. In the original function, the `var` keyword is a return value. This means it doesn't actually belong to the function scope. So while the vector has `val` access inside the function, this may not be the case outside. Therefore, as long as we prevent `var` return values from being used inside a function, this isn't a problem.

But the compiler will still have to catch this case, which should be disallowed.

```eisen
let _items = {...}
val items = items
var match = findFirst(items, someCriteria)
match.modify()
```

Probably this is not decidable. Instead of solving this, possible the programmer should just be content with something like this. Note how `items` is no longer passed in by `val` but by `var`.

```eisen
fn findFirst(
    var items: vec[Obj], 
    criteria: (Obj) -> bool) -> firstMatch: Obj var? 
{
    firstMatch = nil
    for (obj in items) {
        if (criteria(obj)) {
            firstMatch = obj
            return
        }
    }
}
```
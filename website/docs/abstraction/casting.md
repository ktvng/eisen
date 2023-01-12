# Casting
Casting allows a struct to be converted to either an interface it inherits, or a variant of it.

## Syntax
Casting from `typeA` to `typeB` can be imagined as a function of the following signature.

```eisen
fn as(in: typeA, type: Types) -> out: type {
    ...
}
```

With this model in mind, the syntax for casting follows very naturally:

```eisen
let myA = typeA()
val myB = myA.as(typeB)
```

When casting, because the underlying memory is not changed, either `val` or `var` must be used to receive the result, with the exceptions of primitives.

## Interfaces
A struct may be cast into an interface it implements. Either of `val` or `var` should be used to receive the result.

```eisen
let _myClient = SpecificHttpClient()
val myClient = _myClient.as(GeneralHttpClient)
```

## Variants
Casting may be used to convert an underlying struct into a variant of that struct. Either of `val` or `var` should be used to receive the result.


```eisen
let myStr = "./path/to/some/file.txt"
val path = myStr.as(path)
```


## Primitives
Some primitives support cast operations. By default there is no implicit casting of primitives. When casting primitives, the result should be captured by `let`, as in this case, we are in fact writing a new memory allocation.

```eisen
let myInt = 4
let myFlt = myInt.as(flt)
```

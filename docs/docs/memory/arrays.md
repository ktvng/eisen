# Arrays
Where a general purpose, extensible container is required, the developer should use a vector (`vec`) instead. 

## Static Length Arrays
If all elements of an array ars known at compile time, then the array can be declared as a static length array with an initializer list. If elements may be unknown, prefer to use a vector.

```eisen
let nums = int[] { 4, 5, 2, 12 }
let docs = City[] { 
    City("New York", 1624), 
    City("London", 47), 
    City("Seattle", 1851) 
}
```

## Vectors
A vector is stack allocated wrapper over heap memory that handles bounds checking,
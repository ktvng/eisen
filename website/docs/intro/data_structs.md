# Data Structs <Badge type="info" text="In Development" />
Sometimes we have structs that don't need to manage any heap allocated memory, and are intended simply to consolidate together some useful or related information. In these cases a Data Struct can be used to enable the object to be reassigned.

```eisen
data struct Point {
    x: int
    y: int
}
```

The default constructor of a data struct requires all member fields to be passed in by the order they are listed. As data classes are not allowed to manage heap allocated memory, no destructor is needed.

```eisen
let p = Point(0, 3)
```

With a data struct, we can use `Point` as if it were a primitive type.

```eisen
let p = Point(2, 2)
p += Point(4, 3)
```

Operators for data struct must be defined explicity via overloading within the data struct definition.

```eisen
data struct Point {
    x: int
    y: int

    add(new self: Point, o: Point) -> result: Point {
        result = Point(self.x + o.x, self.y + o.y)
    }
}
```

# TODO

3. Better exceptions for parameter incompatibility

4. Fix var? p = nil (this works but should break)

6. Document nil narrowing

9: Nilcheck: this should work
struct obj {
    x: int
    y: int
    o: obj?

    create(x: int, y: int) -> new self: obj {
        self.x = x
        self.y = y
        self.o = nil
    }
}

fn main() {
    let o1 = obj(1, 2)
    let o2 = obj(2, 3)
    o1.o = o2
    if (o1.o != nil) {
        print("%i", o1.o.x)
    }
}

10.
why does struct not have let visiting
struct ptr {
    o: obj
    var o: obj

    create(o: obj) -> new self: obj {
        self.o = obj()
        self.o = o
    }
}

11.
Search for this comment.
    # TODO: need to detect recursion for functions as arguments and for structs which could
    # have functions on them.

interface positionable {
    x: int
    y: int
}

fn el_distance(p: positionable) -> distance: int {
    distance = p.x + (p.y)
}

struct point3d implements positionable {
    x: int
    y: int
    z: int

    create(x: int, y: int, z: int) -> self: point3d {
        self.x = x
        self.y = y
        self.z = z
    }
}

struct vector implements positionable {
    x: int
    y: int
    magnitude: int

    create(x: int, y: int) -> self: vector {
        self.x = x
        self.y = y
        self.magnitude = 0
    }
}

fn main() {
    let p = point3d(1, 2, 5)
    // print("3 5 12 0")
    // TODO: obj will need to be changed to var once pointers are implemented
    // this test will fail then...
    let obj1: positionable
    obj1 = p.as(positionable)
    print("%i ", obj1.el_distance())
    print("%i ", p.z)

    let obj2: positionable
    let v = vector(8, 4)
    obj2 = v.as(positionable)
    print("%i ", obj2.el_distance())
    print("%i", v.magnitude)
}

interface positionable {
    x: int
    y: int
}

fn el_distance(p: positionable) -> distance: int {
    distance = p.x + (p.y)
}

struct point3d is positionable {
    x: int
    y: int
    z: int

    create(x: int, y: int, z: int) -> self: point3d {
        self.x = x
        self.y = y
        self.z = z
    }
}

struct vector is positionable {
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
    // TODO: obj will need to be changed to var once pointers are implemented
    // this test will fail then...
    let obj: positionable
    obj = p.as(positionable)
    print("%i ", obj.el_distance())
    print("%i ", p.z)

    let v = vector(8, 4)
    obj = v.as(positionable)
    print("%i ", obj.el_distance())
    print("%i", v.magnitude)
}

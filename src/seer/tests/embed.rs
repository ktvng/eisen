struct point {
    x: int
    y: int
}

fn say(p: point) {
    print("(%i,%i) ", p.x, p.y)
}

struct point3d {
    embed point
    z: int

    create() -> self: point3d {
        self.x = 0
        self.y = 2
        self.z = 0
    }
}

fn say3d(p: point3d) {
    print("(%i,%i,%i) ", p.x, p.y, p.z)
}

fn main() {
    let p = point3d()
    p.say()
    p.x = 3
    p.z = 4
    p.say()
    p.say3d()
}
// #0 void function 
// asl
fn main() {
    print("asl")
    return
}


// #1 advanced functions
// asl
fn one(x: int, y: int) {
    return
}

fn main() {
    print("asl")
    return
}

// #2 declaring memory
fn two() {
    let x : int
    let y : str?
    let z : int = 12

    var a : int?
    var b = z
    mut var b = z

    val a = 15
    val a : int = 24
    mut val a : int = 10
}

// #3 basic operations
fn three() {
    let x : int = 4
    let y : int = 6
    let z = ((x + y) - 12) * 16
}

// #4 basic function calls
fn four() {
    zero()
    one(12)
    one2(1, 2)
}

// #5 modules
mod space {
    fn five() {
        return
    }

    mod location {
        fn five() {
            return
        }
    }
}

// #6 structs
mod space {
    struct point {
        x : int
        y : int

        create(x : int, y : int) -> self : point {
            self.x = x
            self.y = y
        }
    }
}

// #7 functions again
mod space {
    fn set(self : point, x : int, y : int) {
        self.x = x
        self.y = y
    }
}

fn main() -> int {
    let p = space::point(10, -10)
    p.set(1, 1)
    return 0
}

// #8 fn operator
fn times(n : int, f : () -> null) {
    f()
}

fn say() {
    print("hello")
}

fn main() -> x : int {
    5.times(say)
    x = 4
}

// #9 control flow
fn main() -> int {
    if(true) {
        if(true || false) {
            while(false && true) {
                return 4
            }
        }
        else if (false){
            return 3
        }
        else if (!true){
            return 2
        }
        else {
            return 5
        }
    }
    else {
        return 1
    }
}

// #10 arrays
fn main() -> int {
    var x : int[]
    val y : int[5]
}
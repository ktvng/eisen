fn before() -> result: int {
    result = 4
}

fn sum(a: int, b: int) -> result: int {
    result = a + b
    a = 12
}

fn main() {
    let x = before()
    after()
    print("%i ", x)
    let y = sum(x, x)
    
    // test that y is correctly updated and x is unchanged
    print("%i %i", x, y)
}

fn after() {
    print("after ")
}
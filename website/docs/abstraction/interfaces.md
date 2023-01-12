# Interfaces
While storing member functions as attributes inside a struct allows us to achieve polymorphism between different entities with the same structural data (i.e. same attributes), interfaces add a second degree of polymorphism for entities which may differ in structural data.

An interface is a specification of required functionality. Any struct which implements an interface must implement this set of functionality, but there are no restrictions placed on the member attributes of a struct.

An interface may also be defined as to specify certain member attributes which must be implemented by any struct which implements the interface.

```eisen
interface Payable {
    getPaymentAmount: (Self) -> dollarAmount: flt
    getPaymentDate: (Self, today: Date) -> due: Date

}

struct Order implements Payable {
    itemName: str
    quantity: int
    price: flt
    orderPlacedAt: Date

    fn getPaymentAmount(self: Order) -> dollarAmount: int {
        dollarAmount = self.quantity * self.price
    }

    fn getPaymentDate(self: Order, today: Date) -> due: Date {
        due = min(self.orderPlacedAt.afterDays(5), today.afterDays(3))
    }

    /* constructor & destructor */
    ...
}
```

Notice how implementing the implemented methods are written directly into the into the the struct body. This is the only time where Eisen permits a definition of a method directly inside the struct body. This design was chosen as:

1. All methods required for inheritence are grouped together; there is less of a chance that one gets forgotten or overlooked with everything in one place
2. These methods are associated with the specific struct which implements an interface. Whereas general functions are free-standing, global functions, the methods associated with an interface must be written into a function table by the compiler. These are 'virtual' functions.

The `Self` keyword is required as the first argument of all functions defined inside an interface. This is because these functions must be dispatched from the function table of the implementing struct.

## Creating an Instance
An interface can either be cast as a pointer to an existing memory allocation or created as an actual memory allocation using `let`

```eisen
let myOrder = Order("Pants", 1, 79.99, "6/28/22".toDate())
// casting yields a pointer to an existing memory allocation
val firstPayableThing = myOrder.as(Payable)

// creating an actual memory allocation
let realPayableThing = Order("Pillow", 2, 19.99, "3/14/22".toDate())
```

These are not interchangeable. In particular, in the first part of the example, `myOrder` is created as an `Order` memory allocation, and contains all the memory required to represent an `Order`. And while `realPayableThing` is a memory allocation, it is an allocation for a `Payable` object. As each object which implements an interface may differ in size, the allocation required for `Payable` cannot be easily known. Instead, it is standardized to exactly the amount of memory required for functionality/attributes of the `Payable` interface, and the remaining member attributes of the underlying struct are stored on the heap dynamically.


## Multiple Interfaces
Provided there are no naming conflicts, Eisen puts no limit onto the number of interfaces that a given struct can implement. Currently, naming conflicts between methods required of different interfaces will result in a compile time error; there are no plans to change this caveat.

```eisen
interface Hashable {
    hash: (Self) -> int
}

interface Debuggable {
    write: (Self) -> str
}

struct LedgerEntry implements Hashable, Debuggable {
    price: flt
    amount: flt

    fn hash() {
        return hash(hash(price) + hash(amount))
    }

    fn write(self: LedgerEntry) -> str {
        return "{self.amount} at ${self.price}"
    }

    ...
}
```

## Low-Cost implementation
Eisen implements interfaces as C level structs with function pointers (i.e. a virtual function table). The interfact struct also has a pointer to the underlying object instance, which gets passed into each entry of the function table.

## Interface Specific Methods
Interfaces can also be written with certain methods already implemented. Because an interface represents a public set of attributes and methods, Eisen actually permits the developer to defined functions which may treat an interface as if it were a struct. When an interface is used in this way, only the attributes and methods publically comprising the interface may be used.

```eisen
interface AuthenticationManager {
    username: str
    endpointUrl: str
    isAuthorized: (Self) -> bool
}

fn generateLogMessage(manager: AuthenticationManager) -> msg: str {
    msg = "Authenticating {username} with {endpointUrl}"
}
```

Defining functions on interfaces allows an additional component of code reuse; all implementations of the interface will be able to use these functions. Further, as these functions are defined over the interface, they cannot be redefined a given implementation of the interface.

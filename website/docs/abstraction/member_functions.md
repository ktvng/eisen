# Member Functions
Functions may be defined over structs, externally, and this allows all instances of this struct to exhibit this functionality. However, it may also be useful dynamically change the behavior of certain functions which can be invoked by a given instance during runtime. Eisen treats functions as first class citizens, so structs themselves can contain member functions.

```eisen
struct WelcomeMessage {
    name: str
    getMessage: (new self: WelcomeMessage) -> msg: str

    create(
        name: str,
        getMessage: (WelcomeMessage) -> str
    ) -> new self: WelcomeMessage {
        self.name = name
        self.getMessage = getMessage
    }
}

fn formal(new self: WelcomeMessage) -> msg: str {
    msg = "Dear {self.name}, we are happy to receive you on this day..."
}

fn casual(new self: WelcomeMessage) -> msg: str {
    msg = "Hi {self.name}; welcome!..."
}

fn main() {
    let formalWelcome = WelcomeMessage("Bryan", formal)
    let informalWelcome = WelcomeMessage("Claire", informal)

    formalWelcome.getMessage()
    informalWelcome.getMessage()
}
```

The above allows us to define two different instances of the `WelcomeObject` struct with different functionalities of `getMessage`. This approach can be used to to allow for runtime polymorphism of types.

Specifically, for the entities that have the same structural data; that is, different entitities with the same member attributes, we can now change functionality at runtime. The next sections shows how we can achieve a greater degree of polymorphism using interfaces.

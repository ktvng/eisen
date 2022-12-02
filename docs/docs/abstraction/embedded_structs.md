# Embedded Structs
Most design principles recommend relying on composition instead of inheritance to achieve code reuse. Embedded structs provide a shorthand which makes composition seamless.

In the example below, composition is used to faciliate code reuse of the `HttpHelper` instead of using inheritance and defining `TokenServiceClient` as a subclass of `HttpHelper`.

```eisen
struct HttpHelper {
    endpoint: URL
    timeoutMilli: secs
    retries: int
}

fn sendGetRequest(self: HttpHelper, body: str) -> response: HttpResponse {
    /* send reponse with configured settings */
}

struct TokenServiceClient {
    httpHelper: HttpHelper

    create(timeoutMilli: secs, retries: int) -> self: TokenServiceClient {
        self.httpHelper.timeoutMilli = timeoutMilli
        self.httpHelper.retries = retries
        self.httpHelper.endpoint = "https://token_service.com/get".ToUrl()
    }
}

fn sendGetRequest(client: TokenServiceClient, body: str) {
    client.httpHelper.sendGetRequest(body)
}

fn main() {
    let client = TokenServiceClient()
    client.sendGetRequest(...)
}
```

As the above code shows, composition may require extra "boilerplate" code to access the composed member. To fully hide the internal implementation of `TokenServiceClient`, it was also necessary to redefined the `sendGetRequest` method.

Eisen provides language level support for embedding a struct, in this case, `HttpHelper` directly into another struct to achieve composition without requiring the additional verbosity.

```eisen
struct HttpHelper {
    endpoint: URL
    timeoutMilli: secs
    retries: int
}

fn sendGetRequest(self: HttpHelper, body: str) -> response: HttpResponse {
    /* send reponse with configured settings */
}

struct TokenServiceClient {
    embed HttpHelper

    create(timeoutMilli: secs, retries: int) -> self: TokenServiceClient {
        self.timeoutMilli = timeoutMilli
        self.retries = retries
        self.endpoint = "https://token.service.com/token/".ToUrl()
    }
}

fn main() {
    let client = TokenServiceClient()
    client.sendGetRequest(...)
}
```

The line `embed HttpHelper` creates an instance of `HttpHelper` inside the `TokenServiceClient`, but whereas in the traditional composition paradigm, this instance must be referred to directly, the member attributes and methods of an embedded struct can be referred to directly _as if_ they were direct members of `TokenServiceClient`.

Provided there are no naming conflicts, one may chose to embed any number of other structs, however, in practice, this may lead to more complex dependency relationships. Embedded structs are powerful, but as most abstractions, should be used with care and thought.
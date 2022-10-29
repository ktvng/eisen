mod outer {
    mod inner {
        fn sayInner() {
            print("inner ")
        }

        fn sayInner2() {
            print("inner2 ")
        }
    }

    fn sayOuter() {
        inner::sayInner2()
        print("outer ")
    }
}

fn sayGlobal() {
    print("global")
}

fn main() {
    outer::sayOuter()
    outer::inner::sayInner()
    sayGlobal()
}
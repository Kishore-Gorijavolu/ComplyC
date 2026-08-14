int foo(int x) {
    int a = 10;          // should flag
    int b = 0xFFu;       // should flag
    if (x > -1) {        // -1 ignored (in ignore_values)
        return 42;       // should flag
    }
    return a + b;
}

enum Year { Y1989 = 1989, Y1999 = 1999 }; // ignored if allow_in_enum: true

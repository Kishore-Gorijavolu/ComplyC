/*
Module Name: brace_rules_test_bad
Description: Test brace rules
Author: ComplyC
Version: 1.0
*/

int test_braces(int x)
{
    int result = 0;

    if (x > 0)
        result = 1;

    if (x > 1) { // <-- Brace here not following coding style guide
        result = 2;
    }

    else if (x > 2)
        result = 3;

    else { // <-- Brace here not following coding style guide
        result = 4;
    }

    for (int i = 0; i < 3; i++)
        result += i;

    while (x > 0)
        x--;

    switch (result) {  // Brace issue here
        case 1:
            result = 10;
            break;
        default:
            result = 0;
            break;
    }

    return result;
}

/*
Should give the following Violations:
FORMAT_BRACE_001: 4 violations
BRACE_STYLE_002: 3 violations
*/

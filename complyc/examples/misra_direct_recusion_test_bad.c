/*
Module Name: direct_recursion_test_bad
Description: Test SAFETY_RECURSION_001
Author: ComplyC
Version: 1.0
*/

int factorial_bad(int n)
{
    if (n <= 1)
    {
        return 1;
    }

    return n * factorial_bad(n - 1);
}

int countdown_bad(int value)
{
    if (value <= 0)
    {
        return 0;
    }

    return countdown_bad(value - 1);
}

int helper_good(int value)
{
    return value - 1;
}

int no_recursion_good(int value)
{
    return helper_good(value);
}
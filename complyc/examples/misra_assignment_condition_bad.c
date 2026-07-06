/*
Module Name: test
Description: test
Author: test
Version: 1.0
*/

int test_assignment_condition(int x, int y)
{
    int result = 0;

    if (x = y)
    {
        result = 1;
    }

    while (result = 0)
    {
        result++;
    }

    if (x == y)
    {
        result = 2;
    }

    return result;
}
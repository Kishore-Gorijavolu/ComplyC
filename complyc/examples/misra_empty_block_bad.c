/*
Module Name: test
Description: test
Author: test
Version: 1.0
*/

int test_empty_block(int error, int x)
{
    if (error)
    {
    }

    if (x)
    {
        /* intentionally empty */
    }

    while (x)
    {
    }

    return 0;
}
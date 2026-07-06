/*
Module Name: test
Description: test
Author: test
Version: 1.0
*/

int test_unreachable(int x)
{
    int result = 0;

    if (x > 0)
    {
        return 1;
        result = 10;
    }

    while (x > 0)
    {
        break;
        result = 20;
    }

    switch (x)
    {
        case 0:
            result = 1;
            break;
            result = 30;

        default:
            result = 2;
            break;
    }

    return result;
}
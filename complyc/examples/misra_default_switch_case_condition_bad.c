/*
Module Name: test
Description: test
Author: test
Version: 1.0
*/

int test_switch_default(int mode)
{
    int result = 0;

    switch (mode)
    {
        case 0:
            result = 1;
            break;
        case 1:
            result = 2;
            break;
    }

    switch (result)
    {
        case 1:
            result = 3;
            break;
        default:
            result = 4;
            break;
    }

    return result;
}
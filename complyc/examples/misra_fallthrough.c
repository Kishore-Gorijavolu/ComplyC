/*
Module Name: test
Description: test
Author: test
Version: 1.0
*/

int test_fallthrough(int mode)
{
    int result = 0;

    switch (mode)
    {
        case 0:
            result = 10;

        case 1:
            result = 20;
            break;

        case 2:
            result = 30;
            /* fallthrough */

        case 3:
            result = 40;
            break;

        case 4:
        case 5:
            result = 50;
            break;

        default:
            result = 60;
            break;
    }

    return result;
}
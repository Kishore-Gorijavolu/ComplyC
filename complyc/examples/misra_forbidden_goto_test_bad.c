/*
Module Name: forbidden_goto_test
Description: Test FORBIDDEN_GOTO_001
Author: ComplyC
Version: 1.0
*/

int no_goto(int x)
{
    if (x > 0)
    {
        return x;
    }

    return 0;
}

int with_goto(int x)
{
    if (x > 5)
    {
        goto EXIT;
    }

    x++;

EXIT:
    return x;
}

int multiple_goto(int a)
{
    if (a == 0)
    {
        goto END;
    }

    if (a == 1)
    {
        goto END;
    }

END:
    return a;
}
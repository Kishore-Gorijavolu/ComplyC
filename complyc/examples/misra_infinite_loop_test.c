/*
Module Name: infinite_loop_test
Description: Test LOOP_INFINITE_001
Author: ComplyC
Version: 1.0
*/

void while_forever(void)
{
    while (1)
    {
    }
}

void for_forever(void)
{
    for (;;)
    {
    }
}

void do_forever(void)
{
    do
    {
    }
    while (1);
}

void intentional_superloop(void)
{
    while (1)
    {
        /* super loop */
    }
}

void intentional_scheduler(void)
{
    for (;;)
    {
        /* scheduler loop */
    }
}

void normal_loop(int x)
{
    while (x > 0)
    {
        x--;
    }
}
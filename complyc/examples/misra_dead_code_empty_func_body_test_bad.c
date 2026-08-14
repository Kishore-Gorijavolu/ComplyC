/*
Module Name: empty_function_body_test
Description: Test DEAD_CODE_EMPTY_FUNC_001
Author: ComplyC
Version: 1.0
*/

void empty_function(void)
{
}

void intentional_empty(void)
{
    /* intentionally empty */
}

void stub_function(void)
{
    /* stub */
}

void valid_function(void)
{
    int a = 0;
    a++;
}
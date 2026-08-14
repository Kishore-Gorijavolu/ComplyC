/*
Module Name: security_pack_v1_good.c
Description: Positive fixture for ComplyC Security Rule Pack v1.
Author: ComplyC
Version: 1.0
*/
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>

void security_good_examples(const char *input)
{
    char buffer[16];
    int written;

    written = snprintf(buffer, sizeof(buffer), "%s", input);
    if ((written < 0) || (written >= (int)sizeof(buffer)))
    {
        buffer[0] = '\0';
    }

    printf("%s", buffer);
}

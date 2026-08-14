/*
Module Name: security_pack_v1_bad.c
Description: Negative fixture for ComplyC Security Rule Pack v1.
Author: ComplyC
Version: 1.0
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *api_key = "embedded-production-key";

void security_bad_examples(char *input, unsigned int count)
{
    char small[4];
    char command[64];
    int divisor = 0;

    gets(small);
    strcpy(small, input);
    strcat(small, input);
    sprintf(small, "%s", input);
    printf(input);
    scanf("%s", small);
    system(command);
    tmpnam(small);
    srand(1U);
    (void)rand();
    small[4] = 'X';
    divisor = 10 / 0;
    divisor = 1 << 32;
    input = malloc(count * sizeof(char));
    (void)divisor;
    (void)api_key;
}

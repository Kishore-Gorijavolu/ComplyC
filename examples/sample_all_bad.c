/* Intentionally bad example file for ComplyC rule violations.
 * NOTE: Do NOT use this code in production!
 */

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>

/* Violates NAMING_MACRO_001 (macro not UPPER_SNAKE_CASE) */
#define someMacroValue 123

/* Violates NAMING_GLOBAL_001: global does not start with g_ */
int bad_global_counter = 0;

/* Violates NAMING_STATIC_001: static variable does not start with s_ */
static int fileStaticCounter = 0;

/* Violates NAMING_VAR_003: variable name longer than 31 chars */
int variable_name_that_is_definitely_longer_than_thirty_one_chars = 0;

/* Forward declaration with bad name – violates NAMING_FUNC_001 */
int BadFunctionName(int a, int b);

/* Function without Doxygen header – violates DOC_FUNC_001 (conceptually) */
/* Also uses single-letter vars x,y – violates NAMING_VAR_004 (conceptually) */
/* Uses magic numbers – violates MAGIC_NUMBER_001 */
int BadFunctionName(int a, int b)
{
    int x = 10;      /* magic number 10 */
    int y = 42;      /* magic number 42 */

    if (a > 5)
    {
        x += 2;      /* magic number 2 */
    }

    if (b > 7)
    {
        y += 3;      /* magic number 3 */
    }

    bad_global_counter += x + y;
    fileStaticCounter += 1;
    return x + y;
}

/* Violates SAFETY_DYNAMIC_MEM_001 via forbidden dynamic memory functions */
void use_dynamic_memory(void)
{
    int i;
    int *ptr = (int *)malloc(10 * sizeof(int));  /* malloc forbidden */

    if (ptr)
    {
        for (i = 0; i < 10; i++)
        {
            ptr[i] = i;
        }
        free(ptr);  /* free forbidden */
    }
}

/* Recursion + missing final else + goto + infinite loop patterns:
 *   - Recursion violates SAFETY_RECURSION_001 (conceptually)
 *   - while(1) and for(;;) violate LOOP_INFINITE_001 (conceptually)
 *   - goto violates FORBIDDEN_GOTO_001 (conceptually)
 *   - Missing final else – CTRL_ELSEIF_001 (conceptually)
 */
int recursive_function(int n)
{
    if (n <= 0)
    {
        return 0;
    }
    else if (n == 1)
    {
        return 1;
    }
    else if (n == 2)
    {
        return 2;
    }
    /* Missing final else branch – violates CTRL_ELSEIF_001 (conceptually) */

    while (1)
    {
        break;  /* Infinite loop pattern while(1) */
    }

    for (;;)
    {
        goto end_label;  /* for(;;) infinite loop + goto */
    }

end_label:
    return n + recursive_function(n - 1);
}

/* Function with more than 6 parameters – violates FUNC_PARAMS_001 */
int function_with_too_many_params(int a, int b, int c, int d, int e, int f, int g)
{
    return a + b + c + d + e + f + g;
}

/* Deeply nested, long, complex function:
 *   - Violates FUNC_SIZE_001 (too many lines)
 *   - Violates FUNC_CC_001 (cyclomatic complexity too high)
 *   - Violates FUNC_NESTING_001 (nesting depth > 4)
 *   - Contains more magic numbers for MAGIC_NUMBER_001
 *   - Contains binary-point-like scaling without comment – FIXEDPOINT_COMMENT_001 (conceptually)
 *   - Mixed indentation / brace style could trigger formatting rules (conceptually)
 */
int giant_bad_function(int a)
{
    int x = 0;
    int y = 1;
    int z = 2;
    int scaled = a * 128;      /* binary point change, no explanatory comment */
    int i;

    x = x + 10;
    y = y + 20;
    z = z + 30;

    if (a > 0)
    {
        x++;
        if (a > 10)
        {
            y++;
            if (a > 20)
            {
                z++;
                if (a > 30)
                {
                    x += y;
                    if (a > 40)
                    {
                        z += x;
                    }
                }
            }
        }
    }

    for (i = 0; i < 10; i++)
    {
        x += i;
        if (x % 2 == 0)
        {
            y += x;
        }
        else
        {
            z += y;
        }
    }

    while (x < 100)
    {
        x++;
        y++;
        if (x > 50)
        {
            break;
        }
    }

    switch (a)
    {
        case 0:
            x++;
            break;

        case 1:
            y++;
            break;

        case 2:
            z++;
            break;

        default:
            x += y + z + scaled;
            break;
    }

    return x + y + z + scaled;
}

/* Simple function with bad brace style and no braces on single-line if:
 *   - Violates FORMAT_BRACE_001 (require braces, conceptually)
 *   - Violates BRACE_STYLE_002 (brace on same line, conceptually)
 */
void bad_brace_style(int flag)
{
    if (flag > 0)
        bad_global_counter++;   /* no braces */

    if (flag < 0) {
        fileStaticCounter--;    /* opening brace on same line */
    }
}

/* Trivial entry point just to make the file self-contained */
int main(void)
{
    BadFunctionName(1, 2);
    use_dynamic_memory();
    recursive_function(3);
    function_with_too_many_params(1, 2, 3, 4, 5, 6, 7);
    giant_bad_function(5);
    bad_brace_style(1);
    return 0;
}

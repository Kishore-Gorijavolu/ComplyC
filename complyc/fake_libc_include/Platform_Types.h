#ifndef PLATFORM_TYPES_H
#define PLATFORM_TYPES_H
#include <stdint.h>
typedef unsigned char boolean;
typedef signed char sint8;
typedef unsigned char uint8;
typedef signed short sint16;
typedef unsigned short uint16;
typedef signed int sint32;
typedef unsigned int uint32;
typedef signed long long sint64;
typedef unsigned long long uint64;
typedef float float32;
typedef double float64;
#ifndef TRUE
#define TRUE 1u
#endif
#ifndef FALSE
#define FALSE 0u
#endif
#endif

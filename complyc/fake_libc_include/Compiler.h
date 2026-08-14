#ifndef COMPILER_H
#define COMPILER_H
#define AUTOMATIC
#define STATIC static
#define NULL_PTR ((void*)0)
#define FUNC(rettype, memclass) rettype
#define P2VAR(ptrtype, memclass, ptrclass) ptrtype *
#define P2CONST(ptrtype, memclass, ptrclass) const ptrtype *
#define CONSTP2VAR(ptrtype, memclass, ptrclass) ptrtype * const
#define CONSTP2CONST(ptrtype, memclass, ptrclass) const ptrtype * const
#define VAR(vartype, memclass) vartype
#define CONST(consttype, memclass) const consttype
#endif

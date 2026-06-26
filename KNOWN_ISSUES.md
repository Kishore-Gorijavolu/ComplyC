# Known Issues

## Source Line Numbers

**Status:** Open (Planned for v0.3)

With GCC preprocessing enabled, reported line numbers currently refer to
the preprocessed translation unit rather than the original source file.

## Header Attribution

**Status:** Open

Declarations originating from included header files may be reported
under the selected C source file.

## Experimental Dataflow

Current dataflow analysis may produce false positives for: -
Uninitialized variables - Dead stores - Unused variables

## Current Priority

1.  Report correctness
2.  Source mapping
3.  Embedded project compatibility

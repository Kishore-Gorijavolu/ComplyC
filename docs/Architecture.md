# ComplyC Software Architecture & Design Specification

> **Status:** Draft
>
> This document is intentionally left as a template. It will be expanded
> as the project architecture stabilizes.


## Source Mapping Engine

ComplyC now includes a dedicated `complyc.source_mapping` module. The engine registers a source map for each analyzed translation unit and translates analyzer coordinates back to original user source locations before violations are reported.

Current support:

- GCC/CPP line-marker parsing from preprocessed output.
- Built-in preprocessor identity mapping with synthetic typedef offset handling.
- JSON report fields for both mapped source locations and analyzer/preprocessed locations.
- HTML report columns for source file, mapped line, and analyzer line.

Key diagnostic fields:

- `file` / `line`: user-facing mapped location.
- `source_file` / `source_line`: explicit original source location.
- `analyzed_file` / `analyzed_line`: internal translation-unit coordinate used by the parser.
- `source_mapped`: whether the mapping engine successfully resolved the location.

Planned extensions:

- Macro-expansion range tracking.
- Include-file ownership filters.
- Compile database integration for exact project flags.
- Rich source snippets in HTML reports.

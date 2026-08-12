"""
ComplyC GUI - Project-aware Windows desktop wrapper for ComplyC static analysis.
"""
from __future__ import annotations

import os
import html
import json
import shutil
import subprocess
import sys
import threading
import queue
import traceback
import webbrowser
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from complyc.loader import load_rules
from complyc.parser import parse_c_file
from complyc.project_discovery import ProjectInfo, discover_project
from complyc.rule_engine import run_rules, Violation
from complyc.reporters import write_csv_report, write_json_report, write_html_report, violations_to_dict


APP_TITLE = "ComplyC GUI"
APP_VERSION = "0.2.1"


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def default_rules_path() -> Path:
    return app_base_dir() / "rules" / "complyc_style.yml"


def default_reports_dir() -> Path:
    path = app_base_dir() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


class ComplyCGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1220x780")
        self.minsize(1080, 690)

        self.project_info: ProjectInfo | None = None
        self.selected_files: List[str] = []
        self.include_dirs: List[str] = []
        self.defines: List[str] = []
        self.last_json_report: Path | None = None
        self.last_html_report: Path | None = None
        self.last_csv_report: Path | None = None
        self.last_error_report: Path | None = None
        self._scan_running = False
        self._ui_queue: queue.Queue = queue.Queue()
        self._violation_locations: Dict[str, tuple[str, int]] = {}
        # Complete in-memory violation set used by GUI filters.
        # Filtering only repopulates the Treeview; it never reruns analysis.
        self._all_violation_rows: List[dict] = []

        self.violation_file_filter_var = tk.StringVar(value="All")
        self.violation_rule_filter_var = tk.StringVar(value="All")
        self.violation_severity_filter_var = tk.StringVar(value="All")
        self.violation_search_var = tk.StringVar(value="")
        self.violation_filter_count_var = tk.StringVar(value="Showing 0 of 0 violations")

        self.project_root_var = tk.StringVar(value="")
        self.rules_path_var = tk.StringVar(value=str(default_rules_path()) if default_rules_path().exists() else "")
        self.preprocessor_var = tk.StringVar(value="gcc")
        self.auto_detect_var = tk.BooleanVar(value=True)
        self.scan_headers_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="No scan has been run yet.")
        self.project_summary_var = tk.StringVar(value="No project detected yet.")

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=(14, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="ComplyC", font=("Segoe UI", 22, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Project-aware Coding Guideline Compliance Engine for Embedded C",
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w")

        controls = ttk.LabelFrame(self, text="Project Configuration", padding=10)
        controls.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Project Root:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(controls, textvariable=self.project_root_var).grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Button(controls, text="Browse", command=self.browse_project_root).grid(row=0, column=2, padx=(8, 0), pady=3)
        ttk.Button(controls, text="Detect Project", command=self.detect_project).grid(row=0, column=3, padx=(8, 0), pady=3)

        ttk.Label(controls, text="Rules YAML:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(controls, textvariable=self.rules_path_var).grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Button(controls, text="Browse", command=self.browse_rules).grid(row=1, column=2, padx=(8, 0), pady=3)

        opts = ttk.Frame(controls)
        opts.grid(row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Label(opts, text="Preprocessor:").grid(row=0, column=0, padx=(0, 8))
        ttk.Radiobutton(opts, text="GCC Recommended", variable=self.preprocessor_var, value="gcc").grid(row=0, column=1)
        ttk.Radiobutton(opts, text="Built-in Demo Only", variable=self.preprocessor_var, value="builtin").grid(row=0, column=2, padx=(12, 0))
        ttk.Checkbutton(opts, text="Auto-detect include paths", variable=self.auto_detect_var).grid(row=0, column=3, padx=(18, 0))
        ttk.Checkbutton(opts, text="Scan .h files too", variable=self.scan_headers_var).grid(row=0, column=4, padx=(18, 0))

        ttk.Label(controls, textvariable=self.project_summary_var, foreground="#333333").grid(row=3, column=1, sticky="w", pady=(6, 0))

        main = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main.grid(row=2, column=0, sticky="nsew", padx=14)

        left = ttk.Frame(main)
        left.rowconfigure(0, weight=2)
        left.rowconfigure(1, weight=1)
        left.rowconfigure(2, weight=1)
        left.columnconfigure(0, weight=1)
        main.add(left, weight=2)

        source_frame = ttk.LabelFrame(left, text="Source Files", padding=8)
        source_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        source_frame.rowconfigure(0, weight=1)
        source_frame.columnconfigure(0, weight=1)
        self.files_listbox = tk.Listbox(source_frame, selectmode=tk.EXTENDED)
        self.files_listbox.grid(row=0, column=0, sticky="nsew")
        src_scroll = ttk.Scrollbar(source_frame, orient="vertical", command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=src_scroll.set)
        src_scroll.grid(row=0, column=1, sticky="ns")
        src_buttons = ttk.Frame(source_frame)
        src_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(src_buttons, text="Add Files", command=self.add_files).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(src_buttons, text="Add Folder", command=self.add_folder).grid(row=0, column=1, padx=5)
        ttk.Button(src_buttons, text="Remove", command=self.remove_selected_files).grid(row=0, column=2, padx=5)
        ttk.Button(src_buttons, text="Clear", command=self.clear_files).grid(row=0, column=3, padx=5)

        include_frame = ttk.LabelFrame(left, text="Include Paths Passed to GCC", padding=8)
        include_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        include_frame.rowconfigure(0, weight=1)
        include_frame.columnconfigure(0, weight=1)
        self.include_listbox = tk.Listbox(include_frame, selectmode=tk.EXTENDED)
        self.include_listbox.grid(row=0, column=0, sticky="nsew")
        inc_scroll = ttk.Scrollbar(include_frame, orient="vertical", command=self.include_listbox.yview)
        self.include_listbox.configure(yscrollcommand=inc_scroll.set)
        inc_scroll.grid(row=0, column=1, sticky="ns")
        inc_buttons = ttk.Frame(include_frame)
        inc_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(inc_buttons, text="Add Include Folder", command=self.add_include_dir).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(inc_buttons, text="Remove", command=self.remove_selected_include_dirs).grid(row=0, column=1, padx=5)
        ttk.Button(inc_buttons, text="Clear", command=self.clear_include_dirs).grid(row=0, column=2, padx=5)

        define_frame = ttk.LabelFrame(left, text="Compiler Defines Passed to GCC", padding=8)
        define_frame.grid(row=2, column=0, sticky="nsew")
        define_frame.rowconfigure(0, weight=1)
        define_frame.columnconfigure(0, weight=1)
        self.defines_listbox = tk.Listbox(define_frame, selectmode=tk.EXTENDED)
        self.defines_listbox.grid(row=0, column=0, sticky="nsew")
        def_scroll = ttk.Scrollbar(define_frame, orient="vertical", command=self.defines_listbox.yview)
        self.defines_listbox.configure(yscrollcommand=def_scroll.set)
        def_scroll.grid(row=0, column=1, sticky="ns")
        def_buttons = ttk.Frame(define_frame)
        def_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(def_buttons, text="Add Define", command=self.add_define).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(def_buttons, text="Remove", command=self.remove_selected_defines).grid(row=0, column=1, padx=5)
        ttk.Button(def_buttons, text="Clear", command=self.clear_defines).grid(row=0, column=2, padx=5)

        right = ttk.Frame(main)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        main.add(right, weight=3)

        action = ttk.Frame(right)
        action.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.run_button = ttk.Button(action, text="Run Scan", command=self.run_scan_threaded)
        self.run_button.grid(row=0, column=0, padx=(0, 8))
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            action,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            length=180,
        )
        self.progress_bar.grid(row=1, column=0, columnspan=7, sticky="ew", pady=(8, 0))
        
        ttk.Button(
            action,
            text="Clear Results",
            command=self.clear_results,
        ).grid(row=0, column=1, padx=(0, 8))

        ttk.Button(
            action,
            text="HTML Report",
            command=self.open_html_report,
        ).grid(row=0, column=2, padx=(0, 8))

        ttk.Button(
            action,
            text="CSV Report",
            command=self.open_csv_report,
        ).grid(row=0, column=3, padx=(0, 8))

        ttk.Button(
            action,
            text="Reports Folder",
            command=self.open_reports_folder,
        ).grid(row=0, column=4, padx=(0, 8))

        ttk.Button(
            action,
            text="Error Report",
            command=self.open_error_report,
        ).grid(row=0, column=5, padx=(0, 8))

        ttk.Label(
            action,
            textvariable=self.summary_var,
        ).grid(row=0, column=6, sticky="w", padx=(12, 0))

        violations_frame = ttk.LabelFrame(right, text="Violations", padding=8)
        violations_frame.grid(row=1, column=0, sticky="nsew")
        violations_frame.rowconfigure(2, weight=1)
        violations_frame.columnconfigure(0, weight=1)

        # -------------------------------------------------------------
        # Violation filters
        # -------------------------------------------------------------
        filter_bar = ttk.Frame(violations_frame)
        filter_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        filter_bar.columnconfigure(7, weight=1)

        ttk.Label(filter_bar, text="File:").grid(row=0, column=0, sticky="w")
        self.violation_file_filter = ttk.Combobox(
            filter_bar,
            textvariable=self.violation_file_filter_var,
            state="readonly",
            width=24,
            values=("All",),
        )
        self.violation_file_filter.grid(row=0, column=1, sticky="w", padx=(4, 10))
        self.violation_file_filter.bind(
            "<<ComboboxSelected>>",
            self._on_violation_filter_changed,
        )

        ttk.Label(filter_bar, text="Rule ID:").grid(row=0, column=2, sticky="w")
        self.violation_rule_filter = ttk.Combobox(
            filter_bar,
            textvariable=self.violation_rule_filter_var,
            state="readonly",
            width=22,
            values=("All",),
        )
        self.violation_rule_filter.grid(row=0, column=3, sticky="w", padx=(4, 10))
        self.violation_rule_filter.bind(
            "<<ComboboxSelected>>",
            self._on_violation_filter_changed,
        )

        ttk.Label(filter_bar, text="Severity:").grid(row=0, column=4, sticky="w")
        self.violation_severity_filter = ttk.Combobox(
            filter_bar,
            textvariable=self.violation_severity_filter_var,
            state="readonly",
            width=13,
            values=("All", "critical", "major", "minor", "unspecified"),
        )
        self.violation_severity_filter.grid(row=0, column=5, sticky="w", padx=(4, 10))
        self.violation_severity_filter.bind(
            "<<ComboboxSelected>>",
            self._on_violation_filter_changed,
        )

        ttk.Label(filter_bar, text="Search:").grid(row=0, column=6, sticky="w")
        self.violation_search_entry = ttk.Entry(
            filter_bar,
            textvariable=self.violation_search_var,
        )
        self.violation_search_entry.grid(
            row=0,
            column=7,
            sticky="ew",
            padx=(4, 8),
        )
        self.violation_search_entry.bind(
            "<KeyRelease>",
            self._on_violation_filter_changed,
        )

        ttk.Button(
            filter_bar,
            text="Clear Filters",
            command=self.clear_violation_filters,
        ).grid(row=0, column=8, sticky="e")

        ttk.Label(
            violations_frame,
            textvariable=self.violation_filter_count_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 5))

        columns = ("file", "line", "rule", "severity", "message", "reference")
        self.tree = ttk.Treeview(
            violations_frame,
            columns=columns,
            show="headings",
        )
        for col, heading_text in zip(
            columns,
            ("File", "Line", "Rule ID", "Severity", "Message", "Reference"),
        ):
            self.tree.heading(col, text=heading_text)

        self.tree.column("file", width=180, anchor="w")
        self.tree.column("line", width=60, anchor="center")
        self.tree.column("rule", width=120, anchor="w")
        self.tree.column("severity", width=90, anchor="center")
        self.tree.column("message", width=520, anchor="w")
        self.tree.column("reference", width=150, anchor="w")

        yscroll = ttk.Scrollbar(
            violations_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        xscroll = ttk.Scrollbar(
            violations_frame,
            orient="horizontal",
            command=self.tree.xview,
        )
        self.tree.configure(
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
        )
        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self.open_selected_violation)
        yscroll.grid(row=2, column=1, sticky="ns")
        xscroll.grid(row=3, column=0, sticky="ew")

        footer = ttk.Frame(self, padding=(14, 8))
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

    def browse_project_root(self) -> None:
        folder = filedialog.askdirectory(title="Select embedded project root")
        if folder:
            self.project_root_var.set(folder)
            self.detect_project()

    def detect_project(self) -> None:
        root = self.project_root_var.get().strip()
        if not root or not os.path.isdir(root):
            self._show_error("Project root is missing or invalid.")
            return
        try:
            info = discover_project(root)
            self.project_info = info
            self.selected_files = list(info.source_files)
            if not self.scan_headers_var.get():
                self.selected_files = [p for p in self.selected_files if p.lower().endswith(".c")]
            self.include_dirs = list(info.header_dirs)
            self.defines = list(info.defines)
            self._refresh_listbox(self.files_listbox, self.selected_files)
            self._refresh_listbox(self.include_listbox, self.include_dirs)
            self._refresh_listbox(self.defines_listbox, self.defines)
            self.project_summary_var.set(
                f"Detected: {info.project_type} | C files: {len(info.source_files)} | "
                f"include folders: {len(info.header_dirs)} | defines: {len(info.defines)}"
            )
            self.status_var.set("Project detection complete. " + " | ".join(info.notes[:3]))
        except Exception as exc:
            traceback.print_exc()
            self._show_error(f"Project detection failed:\n{exc}")

    def browse_rules(self) -> None:
        path = filedialog.askopenfilename(
            title="Select ComplyC rules YAML",
            filetypes=[("YAML files", "*.yml *.yaml"), ("All files", "*.*")],
        )
        if path:
            self.rules_path_var.set(path)

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select C files",
            filetypes=[("C source/header", "*.c *.h"), ("All files", "*.*")],
        )
        self._append_files(paths)

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select source folder")
        if not folder:
            return
        paths: List[str] = []
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d.lower() not in {".git", "build", "debug", "release", "out"}]
            for name in files:
                if name.lower().endswith((".c", ".h" if self.scan_headers_var.get() else ".c")):
                    paths.append(os.path.join(root, name))
        self._append_files(paths)

    def _append_files(self, paths) -> None:
        for path in paths:
            if path and path not in self.selected_files:
                self.selected_files.append(path)
        self._refresh_listbox(self.files_listbox, self.selected_files)
        self.status_var.set(f"Selected {len(self.selected_files)} file(s).")

    def remove_selected_files(self) -> None:
        selected = list(self.files_listbox.curselection())
        for idx in reversed(selected):
            del self.selected_files[idx]
        self._refresh_listbox(self.files_listbox, self.selected_files)

    def clear_files(self) -> None:
        self.selected_files.clear()
        self._refresh_listbox(self.files_listbox, self.selected_files)

    def add_include_dir(self) -> None:
        folder = filedialog.askdirectory(title="Select include folder")
        if folder and folder not in self.include_dirs:
            self.include_dirs.append(folder)
            self._refresh_listbox(self.include_listbox, self.include_dirs)

    def remove_selected_include_dirs(self) -> None:
        selected = list(self.include_listbox.curselection())
        for idx in reversed(selected):
            del self.include_dirs[idx]
        self._refresh_listbox(self.include_listbox, self.include_dirs)

    def clear_include_dirs(self) -> None:
        self.include_dirs.clear()
        self._refresh_listbox(self.include_listbox, self.include_dirs)

    def add_define(self) -> None:
        value = simpledialog.askstring(APP_TITLE, "Enter macro, for example: UNIT_TEST or STD_ON=1")
        if value:
            value = value.strip()
            if value and value not in self.defines:
                self.defines.append(value)
                self._refresh_listbox(self.defines_listbox, self.defines)

    def remove_selected_defines(self) -> None:
        selected = list(self.defines_listbox.curselection())
        for idx in reversed(selected):
            del self.defines[idx]
        self._refresh_listbox(self.defines_listbox, self.defines)

    def clear_defines(self) -> None:
        self.defines.clear()
        self._refresh_listbox(self.defines_listbox, self.defines)

    def _refresh_listbox(self, listbox: tk.Listbox, values: List[str]) -> None:
        listbox.delete(0, tk.END)
        for value in values:
            listbox.insert(tk.END, value)

    def run_scan_threaded(self) -> None:
        """Start scan in a background thread without touching Tk widgets from worker."""
        if self._scan_running:
            messagebox.showinfo(APP_TITLE, "A scan is already running. Please wait for it to finish.")
            return

        rules_path = self.rules_path_var.get().strip()
        if not rules_path or not os.path.isfile(rules_path):
            self._show_error("Rules file is missing or invalid.")
            return
        if not self.selected_files:
            self._show_error("Please select a project or add at least one .c file.")
            return

        # Snapshot UI state on the main thread. Worker must not read Tk variables.
        scan_config = {
            "rules_path": rules_path,
            "selected_files": list(self.selected_files),
            "include_dirs": list(self.include_dirs),
            "defines": list(self.defines),
            "use_gcc": self.preprocessor_var.get() == "gcc",
            "report_dir": default_reports_dir(),
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": time.perf_counter(),
        }

        self._scan_running = True
        self._set_busy(True)
        self.status_var.set("Running scan...")
        self.summary_var.set("Scan running...")
        self.progress_var.set(0.0)
        self._clear_tree()

        try:
            while True:
                self._ui_queue.get_nowait()
        except queue.Empty:
            pass

        worker = threading.Thread(
            target=self._run_scan_worker,
            args=(scan_config,),
            daemon=True,
            name="ComplyCScanWorker",
        )
        worker.start()
        self.after(100, self._process_ui_queue)

    def _run_scan_worker(self, scan_config: dict) -> None:
        """Background scan worker. Do not call Tkinter APIs in this method."""
        try:
            rules_path = scan_config["rules_path"]
            selected_files = scan_config["selected_files"]
            include_dirs = scan_config["include_dirs"]
            defines = scan_config["defines"]
            use_gcc = scan_config["use_gcc"]
            report_dir: Path = scan_config["report_dir"]
            timestamp = scan_config["timestamp"]
            start_time = scan_config["start_time"]

            _style, rules = load_rules(rules_path)

            per_file_violations: Dict[str, List[Violation]] = {}
            failed_files: List[dict] = []
            severity_counter: Counter[str] = Counter()

            total_files = len(selected_files)
            for index, file_path in enumerate(selected_files, start=1):
                progress = int((index - 1) * 100 / total_files)
                self._ui_queue.put(("progress", progress))
                
                self._ui_queue.put(("status", f"Scanning {index}/{total_files}: {os.path.basename(file_path)}"))
                
                try:
                    ast = parse_c_file(
                        file_path,
                        use_gcc=use_gcc,
                        include_dirs=include_dirs if use_gcc else [],
                        defines=defines if use_gcc else [],
                    )
                    violations = run_rules(ast, rules, file_path)
                    per_file_violations[file_path] = violations
                    for v in violations:
                        severity_counter[(v.severity or "unspecified").lower()] += 1
                        
                    # progress = int(index * 100 / total_files)
                    # self._ui_queue.put(("progress", progress))
                except Exception as file_exc:
                    tb = traceback.format_exc()
                    failed_files.append({
                        "file": file_path,
                        "error_type": type(file_exc).__name__,
                        "error": str(file_exc),
                        "traceback": tb,
                    })
                    print(f"[ComplyC] Skipping failed file: {file_path}")
                    print(tb)
                finally:
                    progress = int(index * 100 / total_files)
                    self._ui_queue.put(("progress", progress))

            json_report = report_dir / f"complyc_report_{timestamp}.json"
            html_report = report_dir / f"complyc_report_{timestamp}.html"
            csv_report = report_dir / f"complyc_report_{timestamp}.csv"
            error_report = report_dir / f"complyc_scan_errors_{timestamp}.html"

            write_json_report(per_file_violations, str(json_report))
            write_html_report(per_file_violations, str(html_report))
            write_csv_report(per_file_violations, str(csv_report))
            self._write_error_reports(failed_files, report_dir, timestamp)

            data = violations_to_dict(per_file_violations)
            elapsed_seconds = time.perf_counter() - start_time
            self._ui_queue.put(("done", {
                "data": data,
                "failed_files": failed_files,
                "json_report": json_report,
                "html_report": html_report,
                "csv_report": csv_report,
                "error_report": error_report,
                "report_dir": report_dir,
                "elapsed_seconds": elapsed_seconds,
            }))
        except Exception as exc:
            tb = traceback.format_exc()
            print(tb)
            self._ui_queue.put(("fatal", "Scan setup failed:\n" + str(exc)))

    def _process_ui_queue(self) -> None:
        """Apply queued worker messages safely on the Tk main thread."""
        try:
            while True:
                kind, payload = self._ui_queue.get_nowait()

                if kind == "status":
                    self.status_var.set(str(payload))
                elif kind == "progress":
                    self.progress_var.set(float(payload))
                elif kind == "done":
                    self.last_json_report = payload["json_report"]
                    self.last_html_report = payload["html_report"]
                    self.last_csv_report = payload["csv_report"]
                    self.last_error_report = payload["error_report"]

                    self._populate_results(payload["data"], payload["failed_files"])

                    scanned_ok = payload["data"]["summary"]["total_files"]
                    failed = len(payload["failed_files"])
                    
                    elapsed_seconds = payload.get("elapsed_seconds", 0.0)
                    
                    self.status_var.set(
                        f"Scan completed in {elapsed_seconds:.2f}s. "
                        f"Successful: {scanned_ok}, Failed/skipped: {failed}. "
                        f"Reports written to: {payload['report_dir']}"
                    )
                    
                    self.progress_var.set(100.0)
                    if failed:
                        messagebox.showwarning(
                            APP_TITLE,
                            f"Scan completed with {failed} failed/skipped file(s).\n\n"
                            f"Compliance reports were generated for the {scanned_ok} file(s) that parsed successfully.\n"
                            f"Open the Error Report for details."
                        )

                    self._scan_running = False
                    self._set_busy(False)
                    return

                elif kind == "fatal":
                    self._scan_running = False
                    self._set_busy(False)
                    self._show_error(str(payload))
                    self.progress_var.set(0.0)
                    return

        except queue.Empty:
            pass

        if self._scan_running:
            self.after(100, self._process_ui_queue)

    def run_scan(self) -> None:
        """Backward-compatible entry point for any old caller."""
        self.run_scan_threaded()

    def _populate_results(
        self,
        data: dict,
        failed_files: List[dict] | None = None,
    ) -> None:
        """Store scan results and populate the filterable violation view."""
        failed_files = failed_files or []
        summary = data["summary"]

        sev_text = ", ".join(
            f"{severity}: {count}"
            for severity, count in summary["by_severity"].items()
        ) or "none"

        self.summary_var.set(
            f"Parsed: {summary['total_files']} | "
            f"Failed: {len(failed_files)} | "
            f"Violations: {summary['total_violations']} | "
            f"Severity: {sev_text}"
        )

        # Preserve every violation independently of what is currently visible
        # in the Treeview. This makes filtering instantaneous and ensures the
        # existing double-click source navigation still has the original path.
        self._all_violation_rows.clear()

        for file_entry in data["files"]:
            full_file_path = file_entry["file"]
            file_name = os.path.basename(full_file_path)

            for violation in file_entry["violations"]:
                raw_line = violation.get("line")

                try:
                    line_number = int(raw_line) if raw_line else 1
                except (TypeError, ValueError):
                    line_number = 1

                self._all_violation_rows.append({
                    "file_name": file_name,
                    "file_path": full_file_path,
                    "line": line_number,
                    "rule_id": violation.get("rule_id") or "",
                    "severity": (
                        violation.get("severity") or "unspecified"
                    ).lower(),
                    "message": violation.get("message") or "",
                    "reference": violation.get("reference") or "",
                })

        self._refresh_violation_filter_options()
        self.clear_violation_filters()

    def _refresh_violation_filter_options(self) -> None:
        """Refresh File and Rule ID filter choices from current scan results."""
        file_names = sorted({
            row["file_name"]
            for row in self._all_violation_rows
            if row["file_name"]
        })
        rule_ids = sorted({
            row["rule_id"]
            for row in self._all_violation_rows
            if row["rule_id"]
        })

        self.violation_file_filter.configure(
            values=("All", *file_names),
        )
        self.violation_rule_filter.configure(
            values=("All", *rule_ids),
        )

    def _on_violation_filter_changed(self, event=None) -> None:
        """Apply current filter controls to the in-memory violation set."""
        self._apply_violation_filters()

    def clear_violation_filters(self) -> None:
        """Reset all violation filters and show the complete scan result."""
        self.violation_file_filter_var.set("All")
        self.violation_rule_filter_var.set("All")
        self.violation_severity_filter_var.set("All")
        self.violation_search_var.set("")
        self._apply_violation_filters()

    def _apply_violation_filters(self) -> None:
        """Filter violations without rerunning preprocessing or analysis."""
        selected_file = self.violation_file_filter_var.get().strip()
        selected_rule = self.violation_rule_filter_var.get().strip()
        selected_severity = (
            self.violation_severity_filter_var.get().strip().lower()
        )
        search_text = self.violation_search_var.get().strip().lower()

        filtered_rows = []

        for row in self._all_violation_rows:
            if selected_file not in ("", "All"):
                if row["file_name"] != selected_file:
                    continue

            if selected_rule not in ("", "All"):
                if row["rule_id"] != selected_rule:
                    continue

            if selected_severity not in ("", "all"):
                if row["severity"] != selected_severity:
                    continue

            if search_text:
                searchable_text = " ".join((
                    row["file_name"],
                    str(row["line"]),
                    row["rule_id"],
                    row["severity"],
                    row["message"],
                    row["reference"],
                )).lower()

                if search_text not in searchable_text:
                    continue

            filtered_rows.append(row)

        self._render_violation_rows(filtered_rows)

    def _render_violation_rows(self, rows: List[dict]) -> None:
        """Render only the requested rows and rebuild navigation mapping."""
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        self._violation_locations.clear()

        for row in rows:
            item_id = self.tree.insert(
                "",
                tk.END,
                values=(
                    row["file_name"],
                    row["line"],
                    row["rule_id"],
                    row["severity"],
                    row["message"],
                    row["reference"],
                ),
            )

            self._violation_locations[item_id] = (
                row["file_path"],
                row["line"],
            )

        total = len(self._all_violation_rows)
        visible = len(rows)

        if visible == total:
            self.violation_filter_count_var.set(
                f"Showing all {total} violations"
            )
        else:
            self.violation_filter_count_var.set(
                f"Showing {visible} of {total} violations"
            )

    def open_selected_violation(self, event=None) -> None:
        item_id = self.tree.focus()

        if not item_id:
            selected_items = self.tree.selection()
            if not selected_items:
                return
            item_id = selected_items[0]

        location = self._violation_locations.get(item_id)

        if location is None:
            return

        file_path, line_number = location

        if not os.path.isfile(file_path):
            self._show_error(
                f"Source file was not found:\n{file_path}"
            )
            return

        self._open_source_at_line(file_path, line_number)

    def _open_source_at_line(
        self,
        file_path: str,
        line_number: int,
    ) -> None:
        try:
            if sys.platform.startswith("win"):
                vscode_path = shutil.which("code")

                if vscode_path:
                    subprocess.Popen(
                        [
                            vscode_path,
                            "--goto",
                            f"{file_path}:{line_number}:1",
                        ],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    return

                notepad_plus_plus_path = shutil.which("notepad++")

                if notepad_plus_plus_path:
                    subprocess.Popen(
                        [
                            notepad_plus_plus_path,
                            f"-n{line_number}",
                            file_path,
                        ],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    return

                os.startfile(file_path)  # type: ignore[attr-defined]
                return

            if sys.platform == "darwin":
                vscode_path = shutil.which("code")

                if vscode_path:
                    subprocess.Popen(
                        [
                            vscode_path,
                            "--goto",
                            f"{file_path}:{line_number}:1",
                        ]
                    )
                else:
                    subprocess.Popen(["open", file_path])

                return

            vscode_path = shutil.which("code")

            if vscode_path:
                subprocess.Popen(
                    [
                        vscode_path,
                        "--goto",
                        f"{file_path}:{line_number}:1",
                    ]
                )
            else:
                subprocess.Popen(["xdg-open", file_path])

        except Exception as exc:
            self._show_error(
                f"Unable to open source file:\n"
                f"{file_path}\n\n"
                f"{exc}"
            )
        
    def _write_error_reports(self, failed_files: List[dict], report_dir: Path, timestamp: str) -> None:
        """Write separate reports for files that could not be preprocessed, parsed, or scanned."""
        json_path = report_dir / f"complyc_scan_errors_{timestamp}.json"
        html_path = report_dir / f"complyc_scan_errors_{timestamp}.html"
        self.last_error_report = html_path

        payload = {
            "summary": {
                "failed_files": len(failed_files),
            },
            "files": failed_files,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        parts = [
            "<!DOCTYPE html>",
            "<html><head><meta charset='UTF-8'>",
            "<title>ComplyC Scan Error Report</title>",
            """
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
h1, h2 { color: #333; }
table { border-collapse: collapse; width: 100%; margin-top: 16px; }
th, td { border: 1px solid #ccc; padding: 7px 9px; font-size: 14px; vertical-align: top; }
th { background: #f2f2f2; }
.error { color: #b30000; font-weight: bold; }
pre { white-space: pre-wrap; background: #f8f8f8; border: 1px solid #ddd; padding: 8px; }
</style>
""",
            "</head><body>",
            "<h1>ComplyC Scan Error Report</h1>",
            f"<p><b>Failed / skipped files:</b> {len(failed_files)}</p>",
        ]

        if not failed_files:
            parts.append("<p>No scan errors. All selected files were parsed successfully.</p>")
        else:
            parts.append("<table>")
            parts.append("<tr><th>#</th><th>File</th><th>Error Type</th><th>Error</th><th>Traceback</th></tr>")
            for i, item in enumerate(failed_files, start=1):
                parts.append(
                    "<tr>"
                    f"<td>{i}</td>"
                    f"<td>{html.escape(item.get('file', ''))}</td>"
                    f"<td class='error'>{html.escape(item.get('error_type', ''))}</td>"
                    f"<td><pre>{html.escape(item.get('error', ''))}</pre></td>"
                    f"<td><pre>{html.escape(item.get('traceback', ''))}</pre></td>"
                    "</tr>"
                )
            parts.append("</table>")

        parts.append("</body></html>")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))

        print(f"[ComplyC] Scan error JSON written to {json_path}")
        print(f"[ComplyC] Scan error HTML written to {html_path}")

    def _clear_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._violation_locations.clear()
        self._all_violation_rows.clear()

        self.violation_file_filter_var.set("All")
        self.violation_rule_filter_var.set("All")
        self.violation_severity_filter_var.set("All")
        self.violation_search_var.set("")

        self.violation_file_filter.configure(values=("All",))
        self.violation_rule_filter.configure(values=("All",))
        self.violation_filter_count_var.set("Showing 0 of 0 violations")
    
    def _set_busy(self, busy: bool) -> None:
        def apply():
            self.run_button.configure(
                state=tk.DISABLED if busy else tk.NORMAL,
                text="Scanning..." if busy else "Run Scan",
            )
            self.config(cursor="watch" if busy else "")
        self.after(0, apply)

    
    def _show_error(self, message: str) -> None:
        self.after(0, lambda: messagebox.showerror(APP_TITLE, message))
        self.status_var.set("Error")

    def open_html_report(self) -> None:
        if self.last_html_report and self.last_html_report.exists():
            webbrowser.open(self.last_html_report.as_uri())
        else:
            messagebox.showinfo(APP_TITLE, "No HTML report is available yet. Run a scan first.")


    def open_csv_report(self) -> None:
        if self.last_csv_report and self.last_csv_report.exists():
            if sys.platform.startswith("win"):
                os.startfile(self.last_csv_report)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(self.last_csv_report)], check=False)
            else:
                subprocess.run(["xdg-open", str(self.last_csv_report)], check=False)
        else:
            messagebox.showinfo(APP_TITLE, "No CSV report is available yet. Run a scan first.")

    def clear_results(self) -> None:
        self._clear_tree()

        self.summary_var.set("No scan has been run yet.")
        self.status_var.set("Results cleared.")

        self.last_json_report = None
        self.last_html_report = None
        self.last_csv_report = None
        self.last_error_report = None
    
    def open_error_report(self) -> None:
        if self.last_error_report and self.last_error_report.exists():
            webbrowser.open(self.last_error_report.as_uri())
        else:
            messagebox.showinfo(APP_TITLE, "No scan error report is available yet. Run a scan first.")

    def open_reports_folder(self) -> None:
        folder = default_reports_dir()
        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder)], check=False)
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)


def main() -> None:
    app = ComplyCGui()
    app.mainloop()


if __name__ == "__main__":
    main()

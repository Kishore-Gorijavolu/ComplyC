# ComplyC GUI EXE Build Instructions

## 1. Install Python
Install Python 3.11 or 3.12 for Windows.

During installation, check:

- Add Python to PATH

## 2. Test GUI from source
Double-click:

```text
RUN_FROM_SOURCE.bat
```

Or run:

```bat
python -m pip install -r requirements.txt
python complyc_gui.py
```

## 3. Build Windows EXE
Double-click:

```text
build_windows_exe.bat
```

Or run manually:

```bat
python -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --name ComplyC-GUI --add-data "rules;rules" --add-data "fake_libc_include;fake_libc_include" complyc_gui.py
```

## 4. Final EXE location
After build, your executable will be here:

```text
dist\ComplyC-GUI.exe
```

You can share this `.exe` with Windows users.

## 5. How to use the GUI

1. Open `ComplyC-GUI.exe`.
2. Select the YAML rules file. The default bundled file is:

```text
rules\complyc_style.yml
```

3. Add one or more `.c` or `.h` files.
4. Choose preprocessor mode:
   - Built-in: recommended for simple embedded C files.
   - GCC: use only if GCC is installed and needed for preprocessing.
5. Click `Run Compliance Scan`.
6. Review violations in the table.
7. Click `Open HTML Report` or `Open Reports Folder`.

## Notes

- The `.exe` is Windows-only.
- The Python source remains portable across Windows/Linux/macOS.
- For Linux/macOS, run from source using `python complyc_gui.py`.
- If you use GCC mode, GCC must be installed and available on PATH.

# Antigravity 2.0 - Diagnostics & Troubleshooting Playbook

This document details the configuration checks, compilation diagnostics, and platform compatibility issues that may arise when running the Q&A Generator locally.

---

## 1. Verifying Polars Data Compilation

Polars is compiled in Rust and can occasionally run into execution or data alignment issues on specific systems.

### Validation Test
To verify that Polars is properly compiling and operating on your local Python installation, run this simple script from your shell:

```powershell
python -c "import polars as pl; df = pl.DataFrame({'a': [1, 2], 'b': [3, 4]}); print('Polars verified! Version:', pl.__version__)"
```

### Potential Failure Modes
* **DLL Load Failed / Import Error**: If Polars fails to import, your Python installation might not match the architecture of the downloaded package (e.g. running 32-bit Python on 64-bit Windows). Re-install standard 64-bit Python (>= 3.9).
* **AVX Feature Support**: Polars relies on modern CPU features. If you are on an extremely old CPU, you might need to install a non-AVX version of polars or force build from source:
  ```cmd
  pip install polars --no-binary polars
  ```

---

## 2. Scikit-learn on Older CPU Architectures

Scikit-learn utilizes binary extensions that require SIMD instruction sets (such as AVX or AVX2). On older hardware, imports of `sklearn` may result in a crash, segmentation fault, or `Illegal Instruction` error.

### Troubleshooting Steps
1. **Force re-compilation of packages** to bypass pre-compiled wheel incompatibilities:
   ```cmd
   pip install --no-binary :all: scikit-learn
   ```
2. **Check for missing C++ Redistributable libraries**: Scikit-learn on Windows requires the Microsoft Visual C++ Redistributable. Download and install the latest [MSVC Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
3. **Fallback to native Python**: If scikit-learn cannot compile, the deduplication analyzer in `app/pipeline.py` will gracefully catch the import error and fallback to token/character-based duplicate matching.

---

## 3. ReportLab Canvas Generation & Layout Errors

ReportLab is sensitive to canvas height, page boundaries, and styling flowable constraints.

### Common Layout Issues
* **LayoutError (Flowable too large)**: Occurs when a single `KeepTogether` block contains too many items and exceeds the height of a printable page (792 pt for Letter).
  * **Fix**: Ensure your chunks are restricted to `chunk_size=1200` to prevent the generated questions/answers from overflowing the page canvas.
* **Header/Footer Overlaps**: If the running header overlaps your text, adjust the page margins.
  * In `app/utils.py`, the `SimpleDocTemplate` is configured with `topMargin=72` and `bottomMargin=72`, which cleanly bounds content inside [54, 738] height. The header is drawn at `750` and the footer at `36`, preventing any overlap.

---

## 4. Multi-Platform ZIP Password Extraction

The `PackageCryptographyAgent` wraps outputs into a password-protected zip file using the `pyzipper` library.

### Encryption Type and Tool Compatibility
There are two main encryption modes in ZIP files:
1. **Legacy ZipCrypto (Default)**: Weak security, but **universally supported** by all native OS extraction utilities (including built-in Windows Explorer, macOS Archive Utility, and Linux `unzip`).
2. **AES Encryption (SECURE_KEY)**: High security (AES-128/256), but **not natively supported** by legacy Windows Explorer or macOS Archive Utility. Opening AES-encrypted ZIPs on these platforms requires third-party tools like 7-Zip, WinRAR, or PeaZip.

### Implementation Setup
We configure the Package Cryptography Agent to use **Legacy ZipCrypto** by default in `app/pipeline.py` to ensure that users can double-click and extract the ZIP file natively in Windows and macOS Explorer using their mobile number as the plain-text password.

If you require high-grade cryptographic security and intend to use 7-Zip for extraction, you can switch the encryption flag inside `app/pipeline.py` to disable legacy mode.

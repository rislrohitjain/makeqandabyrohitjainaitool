import os
import sys
import shutil
import zipfile
import polars as pl

# Add project root directory to path to allow importing app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils import build_pdf_reportlab, create_encrypted_zip

def run_test():
    print("[*] Starting ZIP and PDF generation tests...")
    
    # Create test output directory
    mobile = "9876543210"
    session_id = "test_verify"
    out_dir = f"storage/outputs/{mobile}/{session_id}"
    os.makedirs(out_dir, exist_ok=True)
    
    zip_path = os.path.join(out_dir, "output.zip")
    xlsx_path = os.path.join(out_dir, "questions.xlsx")
    
    # 1. Create a mock Polars DataFrame with 2 sets of questions
    data = [
        {"Set": "Set A", "Question ID": "1", "Section": "Section A", "Question Stem": "What is 1+1?", "Options": "A) 1 | B) 2 | C) 3 | D) 4", "Option A": "1", "Option B": "2", "Option C": "3", "Option D": "4", "Correct Answer": "B"},
        {"Set": "Set A", "Question ID": "2", "Section": "Section A", "Question Stem": "What is 2+2?", "Options": "A) 2 | B) 4 | C) 6 | D) 8", "Option A": "2", "Option B": "4", "Option C": "6", "Option D": "8", "Correct Answer": "B"},
        {"Set": "Set B", "Question ID": "1", "Section": "Section B", "Question Stem": "What is 3+3?", "Options": "A) 3 | B) 6 | C) 9 | D) 12", "Option A": "3", "Option B": "6", "Option C": "9", "Option D": "12", "Correct Answer": "B"},
        {"Set": "Set B", "Question ID": "2", "Section": "Section B", "Question Stem": "What is 4+4?", "Options": "A) 4 | B) 8 | C) 12 | D) 16", "Option A": "4", "Option B": "8", "Option C": "12", "Option D": "16", "Correct Answer": "B"},
    ]
    df = pl.DataFrame(data)
    
    print("[*] Mock DataFrame created.")
    
    # 2. Generate PDF files for each set separately
    unique_sets = df["Set"].unique().sort().to_list()
    generated_pdfs = []
    
    for set_name in unique_sets:
        set_df = df.filter(pl.col("Set") == set_name)
        set_filename = f"{set_name.replace(' ', '_')}.pdf"
        set_pdf_path = os.path.join(out_dir, set_filename)
        
        print(f"[*] Generating PDF for {set_name} -> {set_pdf_path}")
        build_pdf_reportlab(set_df, f"Test Exam - {set_name}", set_pdf_path)
        
        if os.path.exists(set_pdf_path):
            print(f"[+] PDF generated successfully: {set_pdf_path}")
            generated_pdfs.append(set_filename)
        else:
            print(f"[-] ERROR: PDF not generated: {set_pdf_path}")
            sys.exit(1)
            
    # 3. Write Excel spreadsheet
    excel_cols = ["Set", "Question ID", "Section", "Question Stem", "Option A", "Option B", "Option C", "Option D", "Correct Answer"]
    excel_df = df.select(excel_cols)
    print(f"[*] Generating Excel spreadsheet -> {xlsx_path}")
    excel_df.write_excel(xlsx_path)
    if os.path.exists(xlsx_path):
        print(f"[+] Excel sheet generated successfully.")
    else:
        print(f"[-] ERROR: Excel sheet not generated: {xlsx_path}")
        sys.exit(1)
        
    # 4. Create encrypted ZIP file using ZipCrypto (Legacy)
    print(f"[*] Packaging directory into password-protected ZIP -> {zip_path}")
    create_encrypted_zip(out_dir, zip_path, mobile, use_legacy_crypto=True)
    
    if os.path.exists(zip_path):
        print(f"[+] ZIP package generated successfully.")
    else:
        print(f"[-] ERROR: ZIP package not generated: {zip_path}")
        sys.exit(1)
        
    # 5. Programmatically verify ZIP decryptability with standard zipfile.ZipFile
    print("[*] Verifying ZIP package integrity & password protection...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Set plain-text mobile number password (as bytes)
            zf.setpassword(mobile.encode('utf-8'))
            
            # Print files in ZIP
            infolist = zf.infolist()
            print("[*] Files contained in ZIP:")
            for info in infolist:
                print(f"  - {info.filename} (Size: {info.file_size} bytes)")
                
            # Attempt reading files (which triggers decryption)
            for info in infolist:
                data = zf.read(info.filename)
                print(f"[+] Successfully decrypted and read: {info.filename} ({len(data)} bytes)")
                
        print("[+] SUCCESS: ZIP file is fully valid, not corrupted, and successfully decrypted using standard ZipCrypto!")
    except Exception as e:
        print(f"[-] Verification failed with error: {e}")
        sys.exit(1)
        
    # Clean up output directory after test
    print("[*] Cleaning up test outputs...")
    try:
        shutil.rmtree(f"storage/outputs/{mobile}")
        print("[+] Cleanup complete.")
    except Exception as err:
        print(f"[!] Warning: cleanup failed: {err}")

if __name__ == "__main__":
    run_test()

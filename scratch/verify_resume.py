import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils import generate_developer_resume

def main():
    print("[*] Generating developer resume PDF...")
    output_path = "storage/rohit_jain_resume.pdf"
    os.makedirs("storage", exist_ok=True)
    try:
        generate_developer_resume(output_path)
        if os.path.exists(output_path):
            print(f"[+] Resume successfully generated at: {output_path} ({os.path.getsize(output_path)} bytes)")
        else:
            print("[-] Error: Resume PDF file not found after generation.")
            sys.exit(1)
    except Exception as e:
        print(f"[-] Execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

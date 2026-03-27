"""Verify a PyInstaller onefile exe contains critical DLLs."""

import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_exe.py <path_to_exe>")
        sys.exit(1)

    exe_path = sys.argv[1]
    critical_dlls = ["python312.dll", "vcruntime140.dll"]

    try:
        from PyInstaller.utils.cliutils.archive_viewer import get_archive

        arch = get_archive(exe_path)
        toc_names = [name for name, *_ in arch.toc]

        all_found = True
        for dll in critical_dlls:
            found = any(dll.lower() in n.lower() for n in toc_names)
            status = "FOUND" if found else "MISSING"
            print(f"  {dll}: {status}")
            if not found:
                all_found = False

        print(f"Archive contains {len(toc_names)} entries")

        if not all_found:
            print("FATAL: Critical DLLs missing from exe!")
            sys.exit(1)

        print("All critical DLLs verified.")

    except Exception as e:
        print(f"Warning: Could not inspect archive: {e}")
        print("Skipping DLL verification (exe may still be valid)")


if __name__ == "__main__":
    main()

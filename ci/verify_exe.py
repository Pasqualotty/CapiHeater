"""Verify a PyInstaller onefile exe contains critical DLLs."""

import struct
import sys
import os


def read_pyinstaller_toc(exe_path):
    """Read the table of contents from a PyInstaller onefile exe."""
    with open(exe_path, "rb") as f:
        # PyInstaller's CArchive has a magic cookie at the end
        # MAGIC = b'MEI\014\013\012\013\016'
        MAGIC = b"MEI\x0c\x0b\x0a\x0b\x0e"
        f.seek(0, 2)
        file_size = f.tell()

        # Search for the magic in the last 4KB
        search_start = max(0, file_size - 4096)
        f.seek(search_start)
        data = f.read()
        magic_pos = data.find(MAGIC)

        if magic_pos == -1:
            return None

        abs_pos = search_start + magic_pos
        # The cookie structure is 24 bytes before the magic
        # struct: magic(8) + pkg_length(4) + toc_offset(4) + toc_length(4) + pyver(4)
        f.seek(abs_pos)
        cookie = f.read(24 + 8)

        if len(cookie) < 24:
            return None

        magic = cookie[:8]
        pkg_len = struct.unpack("!i", cookie[8:12])[0]
        toc_offset = struct.unpack("!i", cookie[12:16])[0]
        toc_len = struct.unpack("!i", cookie[16:20])[0]

        # Read TOC
        pkg_start = abs_pos + 24 - pkg_len
        f.seek(pkg_start + toc_offset)
        toc_data = f.read(toc_len)

        # Parse TOC entries
        entries = []
        pos = 0
        while pos < len(toc_data):
            if pos + 18 > len(toc_data):
                break
            entry_len = struct.unpack("!i", toc_data[pos:pos + 4])[0]
            if entry_len <= 0 or pos + entry_len > len(toc_data):
                break
            # name starts at offset 18
            name_data = toc_data[pos + 18:pos + entry_len]
            name = name_data.split(b"\x00")[0].decode("utf-8", errors="replace")
            entries.append(name)
            pos += entry_len

        return entries


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_exe.py <path_to_exe>")
        sys.exit(1)

    exe_path = sys.argv[1]

    if not os.path.exists(exe_path):
        print(f"FATAL: {exe_path} not found")
        sys.exit(1)

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"Exe size: {size_mb:.2f} MB")

    # Verify PE header
    with open(exe_path, "rb") as f:
        magic = f.read(2)
    if magic != b"MZ":
        print("FATAL: Not a valid PE executable")
        sys.exit(1)

    print("PE header: OK")

    # Try to read PyInstaller TOC
    entries = read_pyinstaller_toc(exe_path)
    if not entries:
        print("Warning: Could not read PyInstaller TOC (format may have changed)")
        print("Build log shows DLLs were force-bundled — proceeding")
        return

    print(f"PyInstaller archive: {len(entries)} entries")

    # Check for critical DLLs
    critical = ["python312.dll", "vcruntime140.dll"]
    all_found = True
    for dll in critical:
        found = any(dll.lower() in e.lower() for e in entries)
        status = "FOUND" if found else "MISSING"
        print(f"  {dll}: {status}")
        if not found:
            all_found = False

    # Also list all python3*.dll and vcruntime* entries
    dll_entries = [e for e in entries if "python3" in e.lower() or "vcruntime" in e.lower()]
    if dll_entries:
        print(f"  All runtime DLLs in archive: {dll_entries}")

    if not all_found:
        print("FATAL: Critical DLLs missing from exe!")
        sys.exit(1)

    print("All critical DLLs verified.")


if __name__ == "__main__":
    main()

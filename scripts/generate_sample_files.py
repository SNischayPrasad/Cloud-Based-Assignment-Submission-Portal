"""
Create the files in sample_files/ used for manual testing.

    python scripts/generate_sample_files.py           # small test files
    python scripts/generate_sample_files.py --large   # also a 12 MB file (not committed)
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.utils.pdf_builder import build_pdf  # noqa: E402

OUT = ROOT / "sample_files"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--large", action="store_true", help="also create a 12 MB PDF for the size-limit test")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)

    files = {
        "sample_assignment.pdf": build_pdf([
            "CC401 Cloud Computing - Sample Assignment Submission",
            "Student: Demo Student (fictional)",
            "Topic: Three-tier cloud architecture",
            "1. Presentation tier: static React app on a CDN",
            "2. Application tier: FastAPI on a managed container service",
            "3. Data tier: managed PostgreSQL + private object storage",
        ]),
        "sample_assignment_v2.pdf": build_pdf([
            "CC401 Cloud Computing - Sample Assignment (REVISED)",
            "Used to demonstrate resubmission (attempt 2).",
        ]),
        # Text content with a .pdf name: must be rejected by the magic-byte check.
        "fake_renamed.pdf": b"This is plain text pretending to be a PDF.\n",
        # Extension that no assignment allows: must be rejected.
        "unsupported_file.exe": b"Not a real program - used to test the extension whitelist.\n",
        "notes.txt": b"Plain-text notes for assignments that accept .txt files.\n",
    }
    for name, data in files.items():
        (OUT / name).write_bytes(data)
        print(f"created sample_files/{name} ({len(data)} bytes)")

    if args.large:
        big = OUT / "large_file.pdf"
        big.write_bytes(b"%PDF-1.4\n" + b"0" * (12 * 1024 * 1024))
        print(f"created sample_files/large_file.pdf ({big.stat().st_size} bytes) - ignored by git")


if __name__ == "__main__":
    main()

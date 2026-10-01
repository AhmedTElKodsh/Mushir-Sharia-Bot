"""Isolated PDF text worker. No network or credentials; input/output are bounded."""
from __future__ import annotations

import io
import json
import os
import sys


def resource_limits():
    if os.name != "nt":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        return
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
                    ("flags", wintypes.DWORD), ("min_working", ctypes.c_size_t),
                    ("max_working", ctypes.c_size_t), ("active_processes", wintypes.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                    ("scheduling", wintypes.DWORD)]

    class Io(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in
                    ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

    class Extended(ctypes.Structure):
        _fields_ = [("basic", Basic), ("io", Io), ("process_memory", ctypes.c_size_t),
                    ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                    ("peak_job", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    job = kernel.CreateJobObjectW(None, None)
    limits = Extended()
    limits.basic.flags = 0x100 | 0x2  # per-process committed memory and CPU time
    limits.basic.process_time = 8 * 10_000_000
    limits.process_memory = 512 * 1024 * 1024
    if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise OSError("PDF worker resource limits unavailable")
    # Retain the open job handle for this worker's lifetime.
    resource_limits.job = job


def extract(body, limit):
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(body))
        if reader.is_encrypted:
            return {"status": "pdf_encrypted", "pages": []}
        if len(reader.pages) > 100:
            return {"status": "pdf_page_limit", "pages": []}
        pages, size = [], 0
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            size += len(text.encode("utf-8"))
            if size > limit:
                return {"status": "extraction_too_large", "pages": []}
            pages.append({"page": i + 1, "text": text})
        missing = [page["page"] for page in pages if not page["text"].strip()]
        status = "ocr_needed" if len(missing) == len(pages) else ("partial_page_text" if missing else "page_text")
        return {"status": status, "pages": pages, "ocr_needed_pages": missing}
    except MemoryError:
        return {"status": "pdf_resource_limit", "pages": []}
    except Exception:
        return {"status": "pdf_parse_failed", "pages": []}


def main():
    limit = int(sys.argv[1])
    if limit <= 0:
        return 1
    try:
        resource_limits()
    except OSError:
        print(json.dumps({"status": "pdf_limits_unavailable", "pages": []}))
        return 0
    body = sys.stdin.buffer.read(limit + 1)
    if len(body) > limit:
        return 1
    result = json.dumps(extract(body, limit), ensure_ascii=False).encode("utf-8")
    if len(result) > limit:
        result = b'{"status":"extraction_too_large","pages":[]}'
    sys.stdout.buffer.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

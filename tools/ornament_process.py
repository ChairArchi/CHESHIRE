"""Task-local serial worker guard, including Windows venv redirector descendants."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic, sleep

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"rhino")); sys.path.insert(0,str(ROOT/"tools"))
from worker_process import worker_environment
from morphology import windows_memory


def descendants(root, parents):
    found={root}
    while True:
        added={pid for pid,parent in parents.items() if parent in found}-found
        if not added: return found
        found.update(added)


def process_parents():
    class Entry(ctypes.Structure):
        _fields_=[("size",wintypes.DWORD),("usage",wintypes.DWORD),("pid",wintypes.DWORD),
            ("heap",ctypes.c_size_t),("module",wintypes.DWORD),("threads",wintypes.DWORD),
            ("parent",wintypes.DWORD),("priority",wintypes.LONG),("flags",wintypes.DWORD),("exe",wintypes.WCHAR*260)]
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]; kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle==ctypes.c_void_p(-1).value: raise OSError("Process tree snapshot unavailable")
    result={}; entry=Entry(); entry.size=ctypes.sizeof(entry)
    try:
        success=kernel.Process32FirstW(handle,ctypes.byref(entry))
        while success:
            result[entry.pid]=entry.parent
            success=kernel.Process32NextW(handle,ctypes.byref(entry))
    finally: kernel.CloseHandle(handle)
    return result


def terminate_tree(root, known):
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]; kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    current=descendants(root,process_parents())|known
    for pid in sorted(current-{root})+[root]:
        handle=kernel.OpenProcess(1,False,pid)
        if handle:
            try: kernel.TerminateProcess(handle,1)
            finally: kernel.CloseHandle(handle)


def bounded_worker(args, directory, seconds=900):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    peak=0; seen=set(); reason=None; started=monotonic()
    with (directory/"stdout.txt").open("w") as out,(directory/"stderr.txt").open("w") as err:
        child=subprocess.Popen([str(ROOT/".venv/Scripts/python.exe"),"-E","-s",*map(str,args)],
            shell=False,cwd=ROOT,env=worker_environment(),stdout=out,stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            while child.poll() is None:
                pids=descendants(child.pid,process_parents()); seen.update(pids)
                own=windows_memory(); total=own.get("combined_resident_bytes",0)
                if own["status"]!="MEASURED": reason="MEMORY MEASUREMENT UNAVAILABLE"
                for pid in pids:
                    measurement=windows_memory(pid)
                    if measurement["status"]=="MEASURED": total+=measurement["combined_resident_bytes"]-own["combined_resident_bytes"]
                    elif child.poll() is None and pid in process_parents(): reason="DESCENDANT MEMORY UNAVAILABLE"
                peak=max(peak,total)
                if monotonic()-started>seconds: reason="TIMEOUT"
                if peak>4*1024**3: reason="PROCESS TREE 4 GiB LIMIT"
                if own.get("available_bytes",0)<own.get("available_floor_bytes",0): reason="AVAILABLE MEMORY FLOOR"
                if reason:
                    terminate_tree(child.pid,pids); child.wait(timeout=10); break
                sleep(.5)
        finally:
            if child.poll() is None:
                terminate_tree(child.pid,descendants(child.pid,process_parents())); child.wait(timeout=10)
    return dict(exit_code=child.returncode,stop=reason,seconds=monotonic()-started,
        peak_process_tree_plus_driver_bytes=peak,observed_worker_pids=sorted(seen),
        memory_scope="Driver plus venv redirector and recursively discovered descendants; 0.5s working-set samples.")

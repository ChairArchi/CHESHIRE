"""Task-20 guard: descendants and cancellation verify process creation identity."""
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


def born_descendants(root, parents, births):
    """Parent PID alone is insufficient after Windows reuses a process ID."""
    found={root}
    while True:
        added={pid for pid,parent in parents.items() if parent in found and pid not in found
            and births.get(pid) is not None and births.get(parent) is not None and births[pid]>=births[parent]}
        if not added: return found
        found.update(added)


def process_birth(handle):
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
    kernel.GetProcessTimes.restype=wintypes.BOOL
    values=[wintypes.FILETIME() for _ in range(4)]
    if not kernel.GetProcessTimes(handle,*(ctypes.byref(v) for v in values)): return None
    return (values[0].dwHighDateTime<<32)|values[0].dwLowDateTime


def birth_of_pid(pid):
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle: return None
    try: return process_birth(handle)
    finally: kernel.CloseHandle(handle)


def scoped_family(root,root_birth):
    parents=process_parents(); births={root:root_birth}; unknown=set(); scanned={root}
    while True:
        candidates={pid for pid,parent in parents.items() if parent in born_descendants(root,parents,births)}-scanned
        if not candidates: break
        for pid in candidates:
            scanned.add(pid); birth=birth_of_pid(pid)
            if birth is None:
                if pid in process_parents(): unknown.add(pid)
            else: births[pid]=birth
    found=born_descendants(root,parents,births)
    return {pid:births[pid] for pid in found},unknown


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
    for pid in sorted(set(known)-{root})+[root]:
        handle=kernel.OpenProcess(1|0x1000,False,pid)
        if handle:
            try:
                # Use the queried handle for termination too, preventing a
                # second PID lookup from accidentally targeting a new process.
                if process_birth(handle)==known.get(pid): kernel.TerminateProcess(handle,1)
            finally: kernel.CloseHandle(handle)


def bounded_worker(args, directory, seconds=900):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    peak=0; seen={}; reason=None; started=monotonic(); unknown_seen=set()
    with (directory/"stdout.txt").open("w") as out,(directory/"stderr.txt").open("w") as err:
        child=subprocess.Popen([str(ROOT/".venv/Scripts/python.exe"),"-E","-s",*map(str,args)],
            shell=False,cwd=ROOT,env=worker_environment(),stdout=out,stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW)
        root_birth=process_birth(int(child._handle))
        if root_birth is None:
            child.terminate(); child.wait(timeout=10); raise OSError("Worker creation identity unavailable")
        seen[child.pid]=root_birth
        try:
            while child.poll() is None:
                pids,unknown=scoped_family(child.pid,root_birth); seen.update(pids); unknown_seen.update(unknown)
                if unknown: reason="DESCENDANT CREATION IDENTITY UNAVAILABLE"
                own=windows_memory(); total=own.get("combined_resident_bytes",0)
                if own["status"]!="MEASURED": reason="MEMORY MEASUREMENT UNAVAILABLE"
                for pid in pids:
                    if birth_of_pid(pid)!=pids[pid]: continue
                    measurement=windows_memory(pid)
                    if measurement["status"]=="MEASURED": total+=measurement["combined_resident_bytes"]-own["combined_resident_bytes"]
                    elif child.poll() is None and birth_of_pid(pid)==pids[pid]: reason="DESCENDANT MEMORY UNAVAILABLE"
                peak=max(peak,total)
                if monotonic()-started>seconds: reason="TIMEOUT"
                if peak>4*1024**3: reason="PROCESS TREE 4 GiB LIMIT"
                if own.get("available_bytes",0)<own.get("available_floor_bytes",0): reason="AVAILABLE MEMORY FLOOR"
                if reason:
                    terminate_tree(child.pid,seen)
                    if child.poll() is None: child.terminate()
                    child.wait(timeout=10); break
                sleep(.5)
        finally:
            if child.poll() is None:
                terminate_tree(child.pid,seen)
                if child.poll() is None: child.terminate()
                child.wait(timeout=10)
    return dict(exit_code=child.returncode,stop=reason,seconds=monotonic()-started,
        peak_process_tree_plus_driver_bytes=peak,observed_worker_pids=sorted(seen),
        verified_process_births=seen,unknown_creation_pids=sorted(unknown_seen),
        memory_scope="Driver plus creation-time-verified worker descendants; 0.5s samples; same-handle identity checked before cancellation.")

#!/usr/bin/env python3
"""Qualify the JETOS/Python standard-library surface and CPython regression suite."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

LINUX_INAPPLICABLE = frozenset({"_ios_support", "_msi", "_overlapped", "_scproxy", "_winapi", "_wmi", "msvcrt", "nt", "winreg", "winsound"})
IMPORT_CODE = "import importlib,sys; importlib.import_module(sys.argv[1])"
INVENTORY_CODE = r'''import importlib, inspect, json, sys
name=sys.argv[1]
module=importlib.import_module(name)
items=[]
def signature(obj):
    try: return str(inspect.signature(obj))
    except Exception: return None
def add(path,obj,kind): items.append({"path":path,"kind":kind,"signature":signature(obj)})
for attr,obj in sorted(vars(module).items()):
    if not callable(obj): continue
    if inspect.isclass(obj):
        add(attr,obj,"class")
        try: members=vars(obj)
        except TypeError: members={}
        for member_name,raw in sorted(members.items()):
            candidate=raw.__func__ if isinstance(raw,(staticmethod,classmethod)) else raw
            if callable(candidate): add(f"{attr}.{member_name}",candidate,"method")
    else: add(attr,obj,"builtin" if inspect.isbuiltin(obj) else "function")
print(json.dumps(items,sort_keys=True,separators=(",",":")))'''
PROBES={
"asyncio":"import asyncio; assert asyncio.run(asyncio.sleep(0,result='jetos'))=='jetos'",
"compression":"import bz2,lzma,zlib; d=b'jetos'; assert bz2.decompress(bz2.compress(d))==d; assert lzma.decompress(lzma.compress(d))==d; assert zlib.decompress(zlib.compress(d))==d",
"ctypes":"import ctypes; assert ctypes.CDLL(None)",
"filesystem":"import pathlib,tempfile; t=tempfile.TemporaryDirectory(); p=pathlib.Path(t.name)/'x'; p.write_bytes(b'jetos'); assert p.read_bytes()==b'jetos'; t.cleanup()",
"hashing":"import hashlib; assert hashlib.sha256(b'jetos').digest()",
"json":"import json; x={'jetos':[1,True,None]}; assert json.loads(json.dumps(x))==x",
"mmap":"import mmap; m=mmap.mmap(-1,4096); m[:5]=b'jetos'; assert m[:5]==b'jetos'; m.close()",
"selectors":"import selectors; s=selectors.DefaultSelector(); s.close()",
"socket":"import socket; a=socket.socket(); a.bind(('127.0.0.1',0)); a.close()",
"sqlite3":"import sqlite3; c=sqlite3.connect(':memory:'); assert c.execute('select 1').fetchone()==(1,); c.close()",
"ssl":"import ssl; assert ssl.OPENSSL_VERSION and ssl.create_default_context()",
"subprocess":"import subprocess,sys; subprocess.run([sys.executable,'-c','pass'],check=True)",
"threading":"import threading; x=[]; t=threading.Thread(target=lambda:x.append(1)); t.start(); t.join(); assert x==[1]",
}

def child(code:str,*args:str,timeout:int=10):
    try: return subprocess.run([sys.executable,"-I","-c",code,*args],text=True,capture_output=True,timeout=timeout,env=dict(os.environ,PYTHONNOUSERSITE="1"))
    except subprocess.TimeoutExpired: return None

def detail(result):
    if result is None:return "timeout"
    text=(result.stderr or result.stdout).strip().splitlines(); return text[-1] if text else ""
def ok(result): return result is not None and result.returncode==0

def inventory(name:str):
    result=child(INVENTORY_CODE,name,timeout=15)
    if not ok(result): return False,[],detail(result)
    lines=[line for line in result.stdout.splitlines() if line.strip()]
    try:return True,json.loads(lines[-1]),""
    except Exception as exc:return False,[],f"inventory JSON error: {exc}"

def surface(manifest:dict[str,Any])->dict[str,Any]:
    """Return the stable callable surface used for baseline comparisons."""
    return {
        name: entry.get("callables", [])
        for name, entry in sorted(manifest.get("modules", {}).items())
        if entry.get("import") == "PASS" and entry.get("inventory") == "PASS"
    }

def regression_counts(output:str)->dict[str,int|None]:
    """Extract CPython regrtest summary counts without treating skips as passes."""
    counts={"passed":None,"failed":None,"skipped":None}
    patterns={
        "passed":r"(?mi)^\s*(\d+)\s+tests?\s+OK\b|^\s*(\d+)\s+tests?\s+passed\b",
        "failed":r"(?mi)^\s*(\d+)\s+tests?\s+failed\b|^\s*(\d+)\s+tests?\s+failed:\s*",
        "skipped":r"(?mi)^\s*(\d+)\s+tests?\s+skipped\b",
    }
    for key,pattern in patterns.items():
        matches=list(re.finditer(pattern,output))
        if matches:
            groups=[g for g in matches[-1].groups() if g is not None]
            if groups: counts[key]=int(groups[0])
    return counts

def run_full_suite():
    """Run regrtest while teeing progress to the JetOS console.

    ARMv7/HC1 qualification can take hours.  Buffering the complete regression
    suite hid the last test reached when a guest hung or was killed.  Stream a
    single combined stdout/stderr pipe while retaining the text needed for the
    existing summary parser.
    """
    process=subprocess.Popen(
        [sys.executable,"-I","-m","test","-j1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    assert process.stdout is not None
    lines=[]
    for line in process.stdout:
        print(line,end="",flush=True)
        lines.append(line)
    returncode=process.wait()
    output="".join(lines)
    return returncode==0,{"exit_code":returncode,**regression_counts(output)}

def applicable_modules(requested):
    modules=set(requested or sys.stdlib_module_names)
    if sys.platform.startswith("linux"): modules-=LINUX_INAPPLICABLE
    return sorted(modules)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--module",action="append",dest="modules"); parser.add_argument("--manifest",type=Path); parser.add_argument("--baseline",type=Path); parser.add_argument("--full",action="store_true"); parser.add_argument("--strict",action="store_true"); args=parser.parse_args()
    modules=applicable_modules(args.modules); failures=[]; manifest={"implementation":sys.implementation.name,"python":sys.version,"platform":sys.platform,"executable":sys.executable,"modules":{},"probes":{}}
    callable_total=0
    for name in modules:
        imported=child(IMPORT_CODE,name)
        if not ok(imported): manifest["modules"][name]={"import":"FAIL","detail":detail(imported),"callables":[]}; failures.append(f"import {name}"); continue
        good,callables,message=inventory(name)
        manifest["modules"][name]={"import":"PASS","inventory":"PASS" if good else "FAIL","detail":message,"callables":callables}
        if not good: failures.append(f"inventory {name}")
        else: callable_total+=len(callables)
    if not args.modules:
        for name,code in PROBES.items():
            result=child(code); passed=ok(result); manifest["probes"][name]="PASS" if passed else f"FAIL: {detail(result)}"
            if not passed: failures.append(f"capability {name}")
    if args.baseline:
        try:
            baseline=json.loads(args.baseline.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc:
            print(f"FAIL baseline: {exc}")
            failures.append("language surface baseline")
        else:
            if surface(baseline)!=surface(manifest):
                print("FAIL language surface differs from baseline")
                failures.append("language surface baseline")
            else:
                print("PASS language surface matches baseline")
    if args.full:
        passed,summary=run_full_suite(); manifest["cpython_regression_suite"]={"status":"PASS" if passed else "FAIL",**summary}; print("CPython regression counts: "+" ".join(f"{k}={v if v is not None else 'unknown'}" for k,v in summary.items() if k!="exit_code"))
        if not passed: failures.append("CPython regression suite")
    if args.manifest:
        args.manifest.parent.mkdir(parents=True,exist_ok=True); args.manifest.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    passed_modules=sum(e.get("import")=="PASS" and e.get("inventory")=="PASS" for e in manifest["modules"].values()); print(f"stdlib qualification: {passed_modules}/{len(modules)} modules; {callable_total} callable symbols inventoried; {len(failures)} failures")
    return int(args.strict and bool(failures))
if __name__=="__main__": raise SystemExit(main())

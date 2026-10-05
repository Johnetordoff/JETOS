#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from jetos.storage import EncryptionOverride, StoragePolicy, encryption_from_cmdline

def write(path:Path,text:str):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text,encoding='utf-8')

def main()->int:
    checks=0
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        write(root/'proc/self/mountinfo','20 1 8:1 / / rw - ext4 /dev/vda1 rw\n21 20 8:2 / /scratch rw - ext4 /dev/vda2 rw\n22 20 8:3 / /secure rw - ext4 /dev/vda3 rw\n')
        off=StoragePolicy(root=root,encryption_enabled=False)
        assert off.inspect('/file').disposition=='plaintext-authorized'; checks+=1
        on=StoragePolicy(root=root,encryption_enabled=True)
        assert on.inspect('/file').disposition=='unprotected'; checks+=1
        mixed=StoragePolicy(root=root,encryption_enabled=True,overrides=(EncryptionOverride('/scratch',False,'test'),))
        assert mixed.inspect('/scratch/cache').disposition=='plaintext-authorized'; checks+=1
        inverse=StoragePolicy(root=root,encryption_enabled=False,overrides=(EncryptionOverride('/secure',True,'test'),))
        assert inverse.inspect('/secure/data').disposition=='unprotected'; checks+=1
        assert encryption_from_cmdline('quiet jetos.encryption=off') is False; checks+=1
        assert encryption_from_cmdline('jetos.encryption=on') is True; checks+=1
    print(f'JETOS storage modes: {checks} checks passed')
    return 0
if __name__=='__main__': raise SystemExit(main())

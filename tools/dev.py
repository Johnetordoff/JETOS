#!/usr/bin/env python3
"""Reproducible JETOS development build and VM runner."""
from __future__ import annotations
import argparse, os, platform, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; BUILD=ROOT/'.build'; LINUX_SOURCE=BUILD/'linux'; LANGUAGE_SOURCE=BUILD/'jetos-language-src'; LANGUAGE_BUILD=BUILD/'jetos-language-build'; LANGUAGE_PREFIX=BUILD/'jetos-language-install'; ROOTFS=BUILD/'rootfs'; INITRAMFS=BUILD/'jetos-initramfs.cpio.gz'
LINUX_REPOSITORY='https://github.com/gregkh/linux.git'; LINUX_VERSION='6.12.96'; LINUX_COMMIT='6d15a1029d425b15c59463910ebdccc4afe760d6'; CPYTHON_REPOSITORY='https://github.com/python/cpython.git'; CPYTHON_VERSION='3.14.8'; CPYTHON_COMMIT='8e6e75d9102e39bed2a2b279203a396741180f12'

def run(args:list[str],cwd:Path|None=None,capture:bool=False):
    print('+',' '.join(args),flush=True); return subprocess.run(args,cwd=cwd or ROOT,check=True,text=True,capture_output=capture)

def arch():
    m=platform.machine().lower();
    if m in {'x86_64','amd64'}: return 'x86_64'
    if m in {'aarch64','arm64'}: return 'arm64'
    raise SystemExit(f'unsupported host architecture {m!r}')

def ensure_checkout(url:str,commit:str,destination:Path,branch:str|None=None):
    if destination.exists(): return
    destination.parent.mkdir(parents=True,exist_ok=True); run(['git','init',str(destination)]); run(['git','remote','add','origin',url],cwd=destination); run(['git','fetch','--depth','1','origin',commit],cwd=destination); run(['git','checkout','--detach','FETCH_HEAD'],cwd=destination)
    if branch: run(['git','switch','-c',branch],cwd=destination)

def prepare_sources():
    ensure_checkout(LINUX_REPOSITORY,LINUX_COMMIT,LINUX_SOURCE); ensure_checkout(CPYTHON_REPOSITORY,CPYTHON_COMMIT,LANGUAGE_SOURCE,'jetos-language'); run([sys.executable,'tools/language.py','patch',str(LANGUAGE_SOURCE)])

def runtime_paths():
    candidates=[p for p in (LANGUAGE_PREFIX/'bin').glob('python3.*') if p.is_file() and 'config' not in p.name]
    if not candidates: raise SystemExit('JETOS Language runtime missing')
    runtime=sorted(candidates)[-1]; stdlib=Path(run([str(runtime),'-c',"import sysconfig; print(sysconfig.get_path('stdlib'))"],capture=True).stdout.strip()); return runtime,stdlib

def build_language():
    if not (LANGUAGE_PREFIX/'bin').exists() or not list((LANGUAGE_PREFIX/'bin').glob('python3.*')):
        run([sys.executable,'tools/language.py','build',str(LANGUAGE_SOURCE),'--build',str(LANGUAGE_BUILD),'--prefix',str(LANGUAGE_PREFIX)]); run([sys.executable,'tools/language.py','smoke','--build',str(LANGUAGE_BUILD)]); run([sys.executable,'tools/language.py','install','--build',str(LANGUAGE_BUILD)])
    return runtime_paths()

def kernel_image(a:str): return LINUX_SOURCE/('arch/x86/boot/bzImage' if a=='x86_64' else 'arch/arm64/boot/Image')
def build_kernel(a:str):
    image=kernel_image(a)
    if not image.exists(): run([sys.executable,'tools/build.py','kernel',str(LINUX_SOURCE),'--arch',a])
    return image

def tests():
    for s in ('test.py','test_unicode.py','test_language.py','test_bootstrap.py','test_desktop.py','test_capabilities.py','test_policy.py','test_interpreters.py','test_storage.py','test_storage_modes.py'): run([sys.executable,f'tools/{s}'])

def build_all(profile:str):
    if platform.system()!='Linux': raise SystemExit('native build requires Linux; use python jetos.py dev')
    tests(); prepare_sources(); runtime,stdlib=build_language(); a=arch(); kernel=build_kernel(a); run([sys.executable,'tools/image.py','--python',str(runtime),'--stdlib',str(stdlib),'--rootfs',str(ROOTFS),'--output',str(INITRAMFS),'--profile',profile]); run([sys.executable,'tools/size_report.py','--strict']); return kernel,INITRAMFS

def main()->int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    for name in ('build','run'):
        q=sub.add_parser(name); q.add_argument('--profile',choices=('lean','full'),default='lean'); q.add_argument('--encryption',choices=('on','off'),default='on'); q.add_argument('--display',choices=('serial','window','vnc'),default='serial'); q.add_argument('--vnc-bind',default='127.0.0.1')
    sub.add_parser('prepare'); sub.add_parser('status'); args=p.parse_args()
    if args.cmd=='prepare': prepare_sources(); return 0
    if args.cmd=='status': print(f'Linux {LINUX_VERSION}: {LINUX_COMMIT}\nPython {CPYTHON_VERSION}: {CPYTHON_COMMIT}\narch: {arch()}'); return 0
    kernel,initramfs=build_all(args.profile)
    if args.cmd=='build': return 0
    os.execv(sys.executable,[sys.executable,'tools/vm.py','--arch',arch(),'--kernel',str(kernel),'--initramfs',str(initramfs),'--encryption',args.encryption,'--display',args.display,'--vnc-bind',args.vnc_bind])
    return 0
if __name__=='__main__': raise SystemExit(main())

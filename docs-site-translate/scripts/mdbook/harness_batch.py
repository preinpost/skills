#!/usr/bin/env python3
"""usage: harness_batch.py rebuild   -> build + verify + validate(번역된 문서만)"""
import subprocess, sys, os, json
if sys.argv[1:]==["rebuild"]:
    subprocess.run([sys.executable,"build_site.py"],check=True)
    subprocess.run([sys.executable,"verify.py"])
    docs=[d["docname"] for d in json.load(open("manifest.json")) if os.path.exists(f"translated/{d['docname']}.json")]
    if docs: subprocess.run([sys.executable,"validate_only.py",*docs])

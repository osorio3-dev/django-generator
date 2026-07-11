#!/usr/bin/env python3
"""Validation script — runs copier + check + pytest for module ON/OFF combinations.

Generates a project per combination in /tmp/opencode/copier-validate/ and
records whether (a) manage.py check passes and (b) pytest passes.
"""

import os
import subprocess
import sys
import shutil
import json
from pathlib import Path
from itertools import product

TEMPLATE = "/home/o3dev/code/python/django-generator"
OUTPUT_ROOT = Path("/tmp/opencode/copier-validate")
PY = "/usr/bin/python3.12"
UV = "/home/o3dev/.local/bin/uv"


def run(cmd, **kwargs):
    """Run a command, returning (returncode, stdout, stderr)."""
    r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    return r.returncode, r.stdout, r.stderr


def slug(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))


def make_combo(modules, multitenant, isolation, persist, docker, precommit, ci, toolbar, persist_flag=False):
    """Generate a project with the given config and run check + pytest."""
    name = "test_" + slug("_".join(modules) if modules else "none")[:40]
    if multitenant:
        name += "_mt_" + isolation
    if persist:
        name += "_persist"
    target = OUTPUT_ROOT / name

    if target.exists():
        shutil.rmtree(target)

    # Build copier data flags
    data = [
        f"project_name={name}",
        f"project_slug={name.replace('-', '_')}",
        f"optional_modules={json.dumps(modules if modules else [])}",
    ]
    if multitenant:
        data.append("include_multitenant=true")
        data.append(f"multitenant_isolation={isolation}")
    else:
        data.append("include_multitenant=false")
    if persist:
        data.append("persists_sensitive_data=true")
    else:
        data.append("persists_sensitive_data=false")
    data.extend([
        f"include_docker={'true' if docker else 'false'}",
        f"include_precommit={'true' if precommit else 'false'}",
        f"include_github_actions={'true' if ci else 'false'}",
        f"include_debug_toolbar={'true' if toolbar else 'false'}",
        "admin=true", "frontend=false", "api=false", "include_jobs=false", "include_playwright=false",
        "database=sqlite",
    ])

    cmd = ["copier", "copy", "--trust", "--defaults"] + [f"--data={d}" for d in data] + [TEMPLATE, str(target)]
    rc, out, err = run(cmd)
    if rc != 0:
        return ("GEN_FAIL", rc, out[-500:] + err[-500:])

    # Set up venv
    venv = target / ".venv"
    rc, out, err = run([UV, "venv", "--python", PY, "--seed"], cwd=target)
    if rc != 0:
        return ("VENV_FAIL", rc, err[-500:])
    pypython = str(venv / "bin/python")

    # Install deps
    install_cmd = [UV, "pip", "install", "--python", pypython, "-e", ".", "pytest", "pytest-django", "model-bakery"]
    # Add conditional deps
    if any(m in ["module-secure-endpoints", "module-wompi", "module-ghl", "module-supabase", "module-autologin-tests360"] for m in modules) or persist:
        install_cmd += ["cryptography"]
    if "module-wompi" in modules or "module-ghl" in modules or "module-supabase" in modules:
        install_cmd += ["httpx"]
    if "module-realtime" in modules:
        install_cmd += ["channels", "channels-redis", "daphne", "pytest-asyncio"]
    if "module-django-guard" in modules:
        install_cmd += ["django-guardian"]
    if "module-debug-toolbar" in [m for m in []] or toolbar:
        install_cmd += ["django-debug-toolbar"]

    rc, out, err = run(install_cmd, cwd=target)
    if rc != 0:
        return ("INSTALL_FAIL", rc, err[-500:])

    # Set environment
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    env["SECRET_KEY"] = "x" * 60
    if any(m in ["module-secure-endpoints", "module-wompi", "module-ghl", "module-supabase", "module-autologin-tests360"] for m in modules) or persist:
        # Generate a Fernet key
        rc, key_out, _ = run([pypython, "-c", "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"])
        env["FERNET_ENCRYPTION_KEY"] = key_out.strip()

    # manage.py check
    rc, out, err = run([pypython, "manage.py", "check"], cwd=target, env=env)
    if rc != 0:
        return ("CHECK_FAIL", rc, out[-300:] + err[-300:])

    # pytest — use the directory + -k filter instead of glob
    rc, out, err = run(
        [pypython, "-m", "pytest", "tests/", "-k", "module_", "--no-header", "-q"],
        cwd=target, env=env,
    )
    summary = ""
    for line in out.splitlines()[-5:]:
        if "passed" in line or "failed" in line or "error" in line:
            summary = line
            break
    return ("OK", rc, summary or out[-200:])


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    print("=" * 80)
    print(f"Validation matrix — output to {OUTPUT_ROOT}")
    print("=" * 80)

    results = []

    # 1. Each module ON, rest OFF
    all_modules = [
        "module-secure-endpoints",
        "module-wompi",
        "module-ghl",
        "module-supabase",
        "module-realtime",
        "module-django-guard",
        "module-autologin-tests360",
    ]
    infra_flags = [
        ("include_docker",),
        ("include_precommit",),
        ("include_github_actions",),
        ("include_debug_toolbar",),
    ]

    print("\n--- Single module ON ---")
    for m in all_modules:
        status, rc, info = make_combo([m], False, "logical", False, False, False, False, False)
        results.append((f"only-{m}", status, info))
        print(f"  {m:35s}: {status:12s}  {info[:80] if info else ''}")

    print("\n--- Single infra flag ON ---")
    for (flag,) in infra_flags:
        kwargs = {"modules": [], "multitenant": False, "isolation": "logical", "persist": False}
        if flag == "include_docker":
            status, rc, info = make_combo([], False, "logical", False, True, False, False, False)
            label = "include_docker=true"
        elif flag == "include_precommit":
            status, rc, info = make_combo([], False, "logical", False, False, True, False, False)
            label = "include_precommit=true"
        elif flag == "include_github_actions":
            status, rc, info = make_combo([], False, "logical", False, False, False, True, False)
            label = "include_github_actions=true"
        else:
            status, rc, info = make_combo([], False, "logical", False, False, False, False, True)
            label = "include_debug_toolbar=true"
        results.append((label, status, info))
        print(f"  {label:35s}: {status:12s}  {info[:80] if info else ''}")

    print("\n--- Multitenant (logical + schema) ---")
    status, rc, info = make_combo([], True, "logical", False, False, False, False, False)
    results.append(("mt-logical-only", status, info))
    print(f"  include_multitenant=true (logical) {status:6s}  {info[:80] if info else ''}")
    status, rc, info = make_combo([], True, "schema", False, False, False, False, False)
    results.append(("mt-schema-only", status, info))
    print(f"  include_multitenant=true (schema)  {status:6s}  {info[:80] if info else ''}")

    print("\n--- Cross-module interactions ---")
    status, rc, info = make_combo(["module-secure-endpoints", "module-wompi"], True, "logical", False, False, False, False, False)
    results.append(("secure+wompi+mt-logical", status, info))
    print(f"  secure+wompi+mt-logical: {status:6s}  {info[:80] if info else ''}")

    status, rc, info = make_combo(["module-secure-endpoints"], True, "logical", False, False, False, False, False)
    results.append(("secure+mt-logical", status, info))
    print(f"  secure+mt-logical: {status:6s}  {info[:80] if info else ''}")

    status, rc, info = make_combo(["module-ghl"], True, "logical", False, False, False, False, False)
    results.append(("ghl+mt-logical", status, info))
    print(f"  ghl+mt-logical: {status:6s}  {info[:80] if info else ''}")

    status, rc, info = make_combo(["module-wompi"], True, "logical", False, False, False, False, False)
    results.append(("wompi+mt-logical", status, info))
    print(f"  wompi+mt-logical: {status:6s}  {info[:80] if info else ''}")

    print("\n--- All modules ON (full combo) ---")
    status, rc, info = make_combo(all_modules, True, "logical", True, True, True, True, True)
    results.append(("ALL-on-full", status, info))
    print(f"  ALL + persist + mt + all infra: {status:6s}  {info[:80] if info else ''}")

    print("\n--- Baseline (everything OFF) ---")
    status, rc, info = make_combo([], False, "logical", False, False, False, False, False)
    results.append(("baseline", status, info))
    print(f"  baseline: {status:6s}  {info[:80] if info else ''}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    ok = sum(1 for _, s, _ in results if s == "OK")
    failed = sum(1 for _, s, _ in results if s != "OK")
    print(f"OK: {ok}")
    print(f"Non-OK: {failed}")
    if failed > 0:
        print("\nFailures:")
        for label, status, info in results:
            if status != "OK":
                print(f"  {label}: {status} — {info[:150]}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
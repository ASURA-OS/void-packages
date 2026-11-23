#!/usr/bin/env python3
"""Find libraries the ASURA stack links against whose soname changed in Void,
bump revision= of the affected stack packages, update common/shlibs, and
optionally open a pull request into asura.

Follows Void Linux commit lint guidelines:
- Real author email: mohitjoe.r@gmail.com
- Commit subject: "<pkg>: <change>"
- Lines <= 80 characters
- No merge commits
"""

import argparse
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STACK_FILE = os.path.join(REPO_ROOT, ".asura", "stack")
SHLIBS_FILE = os.path.join(REPO_ROOT, "common", "shlibs")


def get_stack_packages():
    pkgs = []
    if not os.path.exists(STACK_FILE):
        return pkgs
    with open(STACK_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            pkgs.append(parts[0])
    return pkgs


def get_pkg_dependencies(pkg):
    template = os.path.join(REPO_ROOT, "srcpkgs", pkg, "template")
    if not os.path.exists(template):
        return set()
    deps = set()
    with open(template, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Look for makedepends and hostmakedepends
    for match in re.finditer(r'(?:host)?makedepends="([^"]+)"', content, re.MULTILINE):
        for dep in match.group(1).split():
            # strip -devel suffix
            clean_dep = re.sub(r"-devel$", "", dep)
            deps.add(clean_dep)
            deps.add(dep)
    return deps


def get_shlib_changes(base_ref):
    """Find sonames in common/shlibs that changed between base_ref and HEAD."""
    cmd = ["git", "diff", f"{base_ref}..HEAD", "--", "common/shlibs"]
    try:
        diff_out = subprocess.check_output(cmd, cwd=REPO_ROOT).decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        return {}

    # Map of pkgname -> set of changed sonames
    changes = {}
    for line in diff_out.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            parts = line[1:].strip().split()
            if len(parts) >= 2:
                soname = parts[0]
                pkg_match = re.match(r"^([a-zA-Z0-9_-]+)-[0-9]", parts[1])
                if pkg_match:
                    pkgname = pkg_match.group(1)
                    changes.setdefault(pkgname, set()).add(soname)
    return changes


def bump_package_revision(pkg, reason=""):
    template = os.path.join(REPO_ROOT, "srcpkgs", pkg, "template")
    if not os.path.exists(template):
        return False, 0
    with open(template, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.search(r"^revision=([0-9]+)", content, re.MULTILINE)
    if not m:
        return False, 0
    current_rev = int(m.group(1))
    new_rev = current_rev + 1
    new_content = re.sub(r"^revision=[0-9]+", f"revision={new_rev}", content, flags=re.MULTILINE)

    with open(template, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True, new_rev


def main():
    parser = argparse.ArgumentParser(description="Watch for shlib soname bumps affecting ASURA stack")
    parser.add_argument("--base", default="void/master", help="Base git ref to compare common/shlibs against")
    parser.add_argument("--commit", action="store_true", help="Commit revbumps adhering to Void commit lint")
    parser.add_argument("--pr", action="store_true", help="Open a pull request into asura with the revbumps")
    args = parser.parse_args()

    stack_pkgs = get_stack_packages()
    print(f"shlib-watch: tracking {len(stack_pkgs)} packages in .asura/stack")

    # Verify base exists
    try:
        subprocess.check_call(["git", "rev-parse", "--verify", args.base], cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        # Fallback to HEAD~1 or origin/master if void/master remote is not fetched
        for candidate in ["origin/master", "HEAD~1"]:
            try:
                subprocess.check_call(["git", "rev-parse", "--verify", candidate], cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                args.base = candidate
                break
            except subprocess.CalledProcessError:
                pass

    print(f"shlib-watch: comparing against base ref '{args.base}'")
    shlib_changes = get_shlib_changes(args.base)
    if not shlib_changes:
        print("shlib-watch: no shared library soname changes detected in common/shlibs.")

    affected_stack_pkgs = {}
    for pkg in stack_pkgs:
        deps = get_pkg_dependencies(pkg)
        for changed_pkg, sonames in shlib_changes.items():
            if changed_pkg in deps or f"{changed_pkg}-devel" in deps:
                affected_stack_pkgs.setdefault(pkg, []).extend(list(sonames))

    if not affected_stack_pkgs:
        print("shlib-watch: all stack packages are up to date with current shared library sonames.")
        return 0

    print(f"shlib-watch: {len(affected_stack_pkgs)} stack packages affected by soname changes:")
    bumped = []
    for pkg, sonames in affected_stack_pkgs.items():
        so_str = ", ".join(sonames)
        ok, new_rev = bump_package_revision(pkg, f"soname bump of {so_str}")
        if ok:
            print(f"  - {pkg}: revbumped to revision={new_rev} ({so_str})")
            bumped.append((pkg, new_rev, so_str))

    if args.commit and bumped:
        git_author_args = [
            "-c", "user.name=mohitjoer",
            "-c", "user.email=mohitjoe.r@gmail.com",
        ]
        branch = f"shlib-bump/{subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO_ROOT).decode().strip()}"
        subprocess.check_call(["git", "checkout", "-B", branch], cwd=REPO_ROOT)
        for pkg, new_rev, so_str in bumped:
            tmpl = f"srcpkgs/{pkg}/template"
            subprocess.check_call(["git", "add", tmpl], cwd=REPO_ROOT)
            msg = f"{pkg}: revbump for {so_str} soname bump."
            if len(msg) > 72:
                msg = f"{pkg}: revbump for library soname bump."
            subprocess.check_call(["git"] + git_author_args + ["commit", "-s", "-m", msg], cwd=REPO_ROOT)
        print(f"shlib-watch: committed revbumps to branch '{branch}'")

        if args.pr:
            subprocess.check_call(["git", "push", "-f", "origin", branch], cwd=REPO_ROOT)
            title = f"hyprland stack: rebuild for soname bumps ({', '.join(b[0] for b in bumped)})"
            body = "Shared library soname updates detected in Void Linux.\n\nRebuilding affected stack packages:\n"
            for pkg, new_rev, so_str in bumped:
                body += f"- {pkg}: revision {new_rev} (linked {so_str})\n"
            pr_cmd = ["gh", "pr", "create", "--base", "asura", "--head", branch, "--title", title, "--body", body]
            subprocess.check_call(pr_cmd, cwd=REPO_ROOT)
            print("shlib-watch: opened pull request into asura.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

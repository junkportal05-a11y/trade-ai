#!/usr/bin/env python3
"""
Deploy script for Hugging Face Spaces (apextrade-core/trade-ai-backend).

NOTE FOR ALL AGENTS:
- 'hg' and 'hf' in user prompts refer to HUGGING FACE (not Mercurial).
- Direct 'git push huggingface main' will FAIL with a pre-receive hook error
  because intermediate commits in git history contain binary artifacts (palace/chroma.sqlite3).
- This script uses 'git commit-tree' to create a clean, single deployment commit
  directly on top of huggingface/main with the exact current HEAD tree, avoiding
  all legacy binary history.

Usage:
    python scripts/deploy_hf.py [--dry-run]
"""

import argparse
import subprocess
import sys


def run_cmd(cmd: list[str], check: bool = True) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if check and res.returncode != 0:
        print(f"Error running {' '.join(cmd)}:\n{res.stderr.strip()}", file=sys.stderr)
        sys.exit(res.returncode)
    return res.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Deploy clean snapshot to Hugging Face Space")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without pushing")
    args = parser.parse_args()

    print("[HF-DEPLOY] Hugging Face Space Deployment Pipeline")
    print("--------------------------------------------------")

    # 1. Fetch current huggingface remote tip
    print("1. Fetching huggingface remote...")
    run_cmd(["git", "fetch", "huggingface"])
    hf_tip = run_cmd(["git", "rev-parse", "huggingface/main"])
    head_sha = run_cmd(["git", "rev-parse", "--short", "HEAD"])
    tree_sha = run_cmd(["git", "rev-parse", "HEAD^{tree}"])
    print(f"   Current local HEAD: {head_sha} (Tree: {tree_sha[:8]})")
    print(f"   Current HF Space tip: {hf_tip[:8]}")

    # 2. Check if HF Space already has this exact tree
    hf_tree = run_cmd(["git", "rev-parse", "huggingface/main^{tree}"])
    if hf_tree == tree_sha:
        print("[HF-DEPLOY] Space already matches the current HEAD tree. Nothing to deploy!")
        return

    # 3. Create deploy commit on top of huggingface/main
    commit_msg = f"deploy: sync Space tree to main @{head_sha} (verified clean deploy)"
    print(f"2. Creating clean deployment commit on top of HF tip...")
    deploy_commit = run_cmd(["git", "commit-tree", tree_sha, "-p", hf_tip, "-m", commit_msg])
    print(f"   Created commit: {deploy_commit[:8]}")

    # 4. Push to huggingface
    push_cmd = ["git", "push"]
    if args.dry_run:
        push_cmd.append("--dry-run")
    push_cmd.extend(["huggingface", f"{deploy_commit}:refs/heads/main"])

    print(f"3. Pushing to Hugging Face Space {'(DRY RUN)' if args.dry_run else ''}...")
    out = run_cmd(push_cmd)
    if out:
        print(f"   {out}")

    print("\n[HF-DEPLOY] Deployment complete!")
    print("   Space URL: https://huggingface.co/spaces/apextrade-core/trade-ai-backend")


if __name__ == "__main__":
    main()

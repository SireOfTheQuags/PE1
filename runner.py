import os
import shutil
import subprocess
import sys

# Extra "-c" options added to every git call (used for the safe.directory fix).
EXTRA_ARGS = []


# ---------------------------------------------------------------- helpers
def say(msg=""):
    """print() that never crashes on consoles that can't show odd characters."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(str(msg).encode("ascii", "replace").decode("ascii"))


def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        say("\nCancelled.")
        sys.exit(1)


def fail(msg):
    say("[ERROR] " + msg)
    sys.exit(1)


def git(args, cwd, capture=True):
    """Run git. Returns (returncode, stdout, stderr).

    capture=False lets git talk to the terminal directly. Use this for anything
    that touches the network (fetch/pull/push/clone) so login prompts and
    progress are visible instead of the script silently hanging or failing.
    """
    cmd = ["git"] + EXTRA_ARGS + args
    try:
        if capture:
            p = subprocess.run(
                cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", errors="replace",
            )
            return p.returncode, p.stdout.strip(), p.stderr.strip()
        p = subprocess.run(cmd, cwd=cwd)
        return p.returncode, "", ""
    except FileNotFoundError:
        fail("Git is not installed or not on PATH. Install it from "
             "https://git-scm.com/downloads (or ask IT), then reopen the terminal.")


# ----------------------------------------------------------- repo location
def find_repo():
    """Return the repo root, offering to fix/clone when the folder isn't usable."""
    if shutil.which("git") is None:
        fail("Git is not installed or not on PATH. Install it from "
             "https://git-scm.com/downloads (or ask IT), then reopen the terminal.")

    start = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())

    while True:
        if not os.path.isdir(start):
            say("[ERROR] Folder not found: " + start)
        else:
            code, out, err = git(["rev-parse", "--show-toplevel"], start)
            if code == 0:
                return os.path.normpath(out)

            # Shared/school computers often trigger this when the folder is owned
            # by a different Windows user (USB stick, network drive, etc.).
            if "dubious ownership" in err or "safe.directory" in err:
                say("[WARN] Git doesn't trust this folder (it's owned by another user).")
                if ask("Trust it for this run only? (y/n): ").lower() == "y":
                    EXTRA_ARGS[:] = ["-c", "safe.directory=" + start.replace("\\", "/")]
                    continue
                fail("Can't continue without trusting the folder.")

            say("[INFO] '%s' is not a git repository." % start)

        choice = ask("Enter a path to an existing repo, paste a GitHub URL to "
                     "clone, or press Enter to quit: ")
        if not choice:
            sys.exit(1)
        if choice.startswith(("http://", "https://", "git@", "ssh://")):
            return clone(choice)
        start = os.path.abspath(os.path.expanduser(choice))


def clone(url, parent=None):
    parent = parent or os.getcwd()
    name = url.rstrip("/").split("/")[-1].split(":")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    target = os.path.join(parent, name)
    say("\nCloning into %s ..." % target)
    code, _, _ = git(["clone", url, target], parent, capture=False)
    if code != 0:
        fail("Clone failed. Check the URL, your internet/proxy, and your login.")
    say("[OK] Cloned.")
    return target


# ------------------------------------------------------------ small queries
def current_branch(repo):
    code, out, _ = git(["symbolic-ref", "--short", "HEAD"], repo)
    return out if code == 0 else None  # None = detached HEAD


def has_upstream(repo):
    code, _, _ = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], repo)
    return code == 0


def get_remotes(repo):
    code, out, _ = git(["remote"], repo)
    return out.split() if code == 0 and out else []


def porcelain(repo):
    return git(["status", "--porcelain"], repo)[1]


def conflicted_files(repo):
    return git(["diff", "--name-only", "--diff-filter=U"], repo)[1]


def ensure_remote(repo):
    remotes = get_remotes(repo)
    if remotes:
        return "origin" if "origin" in remotes else remotes[0]
    url = ask("This repo has no remote. Paste the GitHub URL to use (Enter to quit): ")
    if not url:
        sys.exit(1)
    code, _, err = git(["remote", "add", "origin", url], repo)
    if code != 0:
        fail(err)
    return "origin"


def ensure_identity(repo):
    """Commits need a name/email. Set them for THIS repo only (not the whole PC)."""
    for key, label in (("user.name", "your name"), ("user.email", "your email")):
        code, out, _ = git(["config", key], repo)
        if code != 0 or not out:
            value = ask("Git needs %s for commits: " % label)
            if not value:
                fail("%s is required to commit." % key)
            git(["config", "--local", key, value], repo)


# ------------------------------------------------------------------- sync
def sync_repository(repo):
    say("\nChecking repository state...")
    branch = current_branch(repo)
    if branch is None:
        fail("You're in 'detached HEAD' state. Switch to a branch first "
             "(e.g. `git checkout main`).")
    remote = ensure_remote(repo)

    stashed = False
    if porcelain(repo):
        say("[WARN] You have uncommitted local changes.")
        choice = ask("  [s] stash them, pull, then restore them\n"
                     "  [a] abort\nChoice: ").lower()
        if choice != "s":
            say("Aborted. Commit or stash your changes first.")
            return
        code, out, err = git(["stash", "-u"], repo)
        if code != 0:
            fail("Couldn't stash changes:\n" + err)
        stashed = "No local changes" not in out
        say("Changes stashed.")

    say("Fetching latest remote changes...")
    code, _, _ = git(["fetch", remote], repo, capture=False)
    if code != 0:
        say("[ERROR] Fetch failed. Common causes: no internet, school firewall/proxy, "
            "wrong login, or the repo URL is wrong.")
        restore_stash(repo, stashed)
        sys.exit(1)

    say("Pulling latest updates...")
    # --no-rebase avoids "Need to specify how to reconcile divergent branches".
    args = ["pull", "--no-rebase"]
    if not has_upstream(repo):
        args += [remote, branch]
    code, _, _ = git(args, repo, capture=False)

    if code != 0:
        conflicts = conflicted_files(repo)
        if conflicts:
            say("\n[ERROR] Merge conflicts in:\n" + conflicts)
            say("Fix those files, then run `git add .` and `git commit`.\n"
                "Or undo the merge with `git merge --abort`.")
            if stashed:
                say("Your stashed changes are safe; restore later with `git stash pop`.")
            sys.exit(1)
        say("[ERROR] Pull failed (see message above).")
        restore_stash(repo, stashed)
        sys.exit(1)

    restore_stash(repo, stashed)
    say("\n[OK] Synced.")


def restore_stash(repo, stashed):
    if not stashed:
        return
    code, _, err = git(["stash", "pop"], repo)
    if code == 0:
        say("Restored your stashed changes.")
    else:
        say("[WARN] Couldn't auto-restore your changes (conflict?). They're safe in "
            "the stash; run `git stash pop` after resolving.\n" + err)


# ----------------------------------------------------------- commit & push
def commit_and_push(repo):
    say("\nPreparing to commit and push...")
    branch = current_branch(repo)
    if branch is None:
        fail("You're in 'detached HEAD' state. Switch to a branch first.")
    remote = ensure_remote(repo)

    status = porcelain(repo)
    if status:
        say("Changes:\n" + status + "\n")
        msg = ask("Enter commit message: ")
        if not msg:
            fail("Commit message cannot be empty.")
        ensure_identity(repo)

        say("Staging changes...")
        code, _, err = git(["add", "-A"], repo)
        if code != 0:
            fail(err)

        say("Committing...")
        code, out, err = git(["commit", "-m", msg], repo)
        if code != 0:
            fail("Commit failed:\n" + (err or out))
    else:
        say("Nothing new to commit. Checking whether there's anything to push...")

    say("Pushing to remote...")
    args = ["push"] if has_upstream(repo) else ["push", "-u", remote, branch]
    code, _, _ = git(args, repo, capture=False)
    if code != 0:
        say("\n[ERROR] Push failed. If it says 'rejected' or 'non-fast-forward', "
            "run option 1 (Sync) first and then push again. Otherwise check your "
            "login/permissions and internet connection.")
        sys.exit(1)
    say("\n[OK] Pushed.")


# ------------------------------------------------------------------- main
def main():
    say("=== Git Automation Tool ===")
    repo = find_repo()
    say("Repo: " + repo)

    say("\n1. Sync (Pull from GitHub)")
    say("2. Commit & Push (Send to GitHub)")
    say("3. Clone a repo into the current folder")
    choice = ask("\nSelect an option (1, 2 or 3): ")

    if choice == "1":
        sync_repository(repo)
    elif choice == "2":
        commit_and_push(repo)
    elif choice == "3":
        url = ask("GitHub URL to clone: ")
        if not url:
            fail("No URL given.")
        clone(url)
    else:
        say("[ERROR] Invalid option. Run the script again and select 1, 2 or 3.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\nCancelled.")
        sys.exit(1)
import subprocess
import sys


def run_command(cmd):
  """Run a shell command and return output, exiting on failure."""
  result = subprocess.run(
      cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True
  )
  if result.returncode != 0:
    print(f"❌ Command failed: {cmd}\n{result.stderr.strip()}")
    sys.exit(1)
  return result.stdout.strip()


def main():
  print("🔍 Checking repository state...")

  # Ensure we are inside a git repository
  is_git = run_command(
      "git rev-parse --is-inside-work-tree"
  )  # pylint: disable=unused-variable

  # Check for uncommitted changes to prevent overwrite disasters
  status = run_command("git status --porcelain")
  if status:
    print(
        "❌ Aborting sync: You have uncommitted local changes. Commit, stash,"
        " or discard them before pulling."
    )
    sys.exit(1)

  print("📥 Fetching latest remote changes...")
  run_command("git fetch")

  print("🔄 Pulling latest updates...")
  output = run_command("git pull")

  print(f"✅ Successfully synced:\n{output}")


if __name__ == "__main__":
  main()
import subprocess
import sys


def run_command(cmd, shell=True):
  """Run a shell command and return output, exiting on failure."""
  result = subprocess.run(
      cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=shell
  )
  if result.returncode != 0:
    print(f"❌ Command failed:\n{result.stderr.strip()}")
    sys.exit(1)
  return result.stdout.strip()


def sync_repository():
  print("\n🔍 Checking repository state...")
  run_command("git rev-parse --is-inside-work-tree")

  # Check for uncommitted changes before pulling
  status = run_command("git status --porcelain")
  if status:
    print(
        "❌ Aborting sync: You have uncommitted local changes. Commit them"
        " first."
    )
    sys.exit(1)

  print("📥 Fetching latest remote changes...")
  run_command("git fetch")

  print("🔄 Pulling latest updates...")
  output = run_command("git pull")
  print(f"✅ Successfully synced:\n{output}")


def commit_and_push():
  print("\n📦 Preparing to commit and push...")
  run_command("git rev-parse --is-inside-work-tree")

  msg = input("Enter commit message: ").strip()
  if not msg:
    print("❌ Error: Commit message cannot be empty.")
    sys.exit(1)

  try:
    print("Staging changes...")
    subprocess.run(["git", "add", "."], check=True)

    print(f"Committing with message: '{msg}'...")
    subprocess.run(["git", "commit", "-m", msg], check=True)

    print("Pushing to remote...")
    subprocess.run(["git", "push"], check=True)

    print("✅ Successfully committed and pushed.")
  except subprocess.CalledProcessError as e:
    print(f"❌ Git command failed: {e}")
    sys.exit(1)


def main():
  print("=== Git Automation Tool ===")
  print("1. Sync (Pull from GitHub)")
  print("2. Commit & Push (Send to GitHub)")

  choice = input("\nSelect an option (1 or 2): ").strip()

  if choice == "1":
    sync_repository()
  elif choice == "2":
    commit_and_push()
  else:
    print("❌ Invalid option. Run the script again and select 1 or 2.")


if __name__ == "__main__":
  main()
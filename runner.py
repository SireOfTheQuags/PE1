import subprocess

def main():
    # Prompt for the commit message
    msg = input("Enter commit message: ")
    
    if not msg.strip():
        print("Error: Commit message cannot be empty.")
        return

    try:
        # Run the git pipeline
        print("Staging changes...")
        subprocess.run(["git", "add", "."], check=True)
        
        print(f"Committing with message: '{msg}'...")
        subprocess.run(["git", "commit", "-m", msg], check=True)
        
        print("Pushing to remote...")
        subprocess.run(["git", "push"], check=True)
        
        print("Successfully committed and pushed.")
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")

if __name__ == "__main__":
    main()
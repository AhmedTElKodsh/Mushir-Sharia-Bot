"""Deploy Mushir Sharia Bot to Hugging Face Space using the Hub API."""
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from huggingface_hub import HfApi, login, HfHubHTTPError
    from dotenv import load_dotenv
except ImportError:
    print("❌ Required packages not installed")
    print("\nInstall with:")
    print("  pip install huggingface_hub python-dotenv")
    sys.exit(1)

# Constants
SEPARATOR = "=" * 60
DEFAULT_REPO_ID = "AElKodsh/mushir-sharia-bot"
REPO_TYPE = "space"
HF_TOKEN_URL = "https://huggingface.co/settings/tokens"

IGNORE_PATTERNS = [
    "*.pyc",
    "__pycache__",
    ".env",
    ".git",
    ".venv",
    "*.log",
    ".pytest_cache",
    "*.egg-info",
    ".DS_Store",
    "*.swp",
    "*.swo",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_hf_token() -> str:
    """Load Hugging Face token from environment.
    
    Returns:
        str: The Hugging Face token.
        
    Raises:
        SystemExit: If token is not found.
    """
    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")
    
    if not hf_token:
        logger.error("HF_TOKEN not found in .env file")
        print("\nPlease add your Hugging Face token to .env:")
        print("  HF_TOKEN=your_token_here")
        print(f"\nGet your token from: {HF_TOKEN_URL}")
        sys.exit(1)
    
    return hf_token


def authenticate_hf(token: str) -> None:
    """Authenticate with Hugging Face.
    
    Args:
        token: Hugging Face API token.
        
    Raises:
        SystemExit: If authentication fails.
    """
    logger.info("Authenticating with Hugging Face...")
    try:
        login(token=token, add_to_git_credential=False)
        logger.info("✅ Authenticated successfully")
    except HfHubHTTPError as e:
        logger.error(f"Authentication failed: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your token is valid")
        print(f"2. Generate a new token at: {HF_TOKEN_URL}")
        print("3. Ensure the token has 'write' permissions")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}", exc_info=True)
        sys.exit(1)


def get_project_root() -> Path:
    """Get the project root directory.
    
    Returns:
        Path: Project root directory.
    """
    return Path(__file__).parent.parent


def upload_to_space(
    api: HfApi,
    repo_id: str,
    project_root: Path,
    commit_message: str,
    dry_run: bool = False
) -> None:
    """Upload project files to Hugging Face Space.
    
    Args:
        api: Hugging Face API instance.
        repo_id: Repository ID (e.g., 'username/space-name').
        project_root: Path to project root directory.
        commit_message: Git commit message for the upload.
        dry_run: If True, only show what would be uploaded without uploading.
        
    Raises:
        SystemExit: If upload fails.
    """
    logger.info(f"Uploading files to {repo_id}...")
    logger.info(f"  From: {project_root}")
    logger.info(f"  Commit: {commit_message}")
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No files will be uploaded")
        logger.info(f"Would upload from: {project_root}")
        logger.info(f"Ignore patterns: {', '.join(IGNORE_PATTERNS)}")
        return
    
    try:
        api.upload_folder(
            folder_path=str(project_root),
            repo_id=repo_id,
            repo_type=REPO_TYPE,
            ignore_patterns=IGNORE_PATTERNS,
            commit_message=commit_message,
        )
        logger.info("✅ Upload successful!")
        
    except HfHubHTTPError as e:
        logger.error(f"Upload failed: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your HF_TOKEN has write access")
        print(f"2. Check the Space exists: https://huggingface.co/spaces/{repo_id}")
        print("3. Verify you have permission to write to this Space")
        print("4. Try manually: git push huggingface main")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected upload error: {e}", exc_info=True)
        sys.exit(1)


def print_success_message(repo_id: str) -> None:
    """Print deployment success message with helpful links.
    
    Args:
        repo_id: Repository ID.
    """
    print()
    print(SEPARATOR)
    print("✅ Deployment Complete!")
    print(SEPARATOR)
    print()
    print("Your Space is updating at:")
    print(f"  https://huggingface.co/spaces/{repo_id}")
    print()
    print("Check build logs:")
    print(f"  https://huggingface.co/spaces/{repo_id}?logs=container")
    print()
    print("Note: It may take 2-5 minutes for the Space to rebuild.")
    print(SEPARATOR)


def deploy_to_space(
    repo_id: Optional[str] = None,
    commit_message: Optional[str] = None,
    dry_run: bool = False
) -> None:
    """Deploy the current code to Hugging Face Space.
    
    Args:
        repo_id: Repository ID (defaults to DEFAULT_REPO_ID).
        commit_message: Custom commit message (defaults to generic message).
        dry_run: If True, show what would be uploaded without uploading.
    """
    print(SEPARATOR)
    print("🚀 Deploying Mushir Sharia Bot to Hugging Face Space")
    print(SEPARATOR)
    print()
    
    # Use defaults if not provided
    repo_id = repo_id or DEFAULT_REPO_ID
    commit_message = commit_message or "feat: update Space with latest code and improvements"
    
    # Load token and authenticate
    hf_token = load_hf_token()
    authenticate_hf(hf_token)
    
    # Initialize API
    api = HfApi()
    project_root = get_project_root()
    
    # Upload files
    upload_to_space(api, repo_id, project_root, commit_message, dry_run)
    
    # Print success message
    if not dry_run:
        print_success_message(repo_id)


def main() -> None:
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Deploy Mushir Sharia Bot to Hugging Face Space",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy with default settings
  python deploy_to_hf_space.py
  
  # Deploy to a different Space
  python deploy_to_hf_space.py --repo-id username/my-space
  
  # Deploy with custom commit message
  python deploy_to_hf_space.py --message "fix: resolve authentication bug"
  
  # Dry run to preview what would be uploaded
  python deploy_to_hf_space.py --dry-run
        """
    )
    
    parser.add_argument(
        "--repo-id",
        type=str,
        default=DEFAULT_REPO_ID,
        help=f"Hugging Face Space repository ID (default: {DEFAULT_REPO_ID})"
    )
    
    parser.add_argument(
        "--message", "-m",
        type=str,
        help="Custom commit message for the deployment"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Deploy
    deploy_to_space(
        repo_id=args.repo_id,
        commit_message=args.message,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()

"""
Backup and recovery system for timetables.
Provides versioning, backup creation, and recovery capabilities.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class BackupInfo:
    """Information about a backup file."""
    filename: str
    timestamp: datetime
    version: str
    description: str
    file_size: int
    checksum: str

class TimetableBackupManager:
    """Manages backup and recovery of timetable data."""

    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = backup_dir
        self.ensure_backup_dir()

    def ensure_backup_dir(self):
        """Create backup directory if it doesn't exist."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def create_backup(self, input_file: str, output_file: str, description: str = "") -> str:
        """Create a backup of input and output files."""
        timestamp = datetime.now()
        version = timestamp.strftime("%Y%m%d_%H%M%S")

        # Create backup filenames
        input_backup = os.path.join(self.backup_dir, f"input_{version}.json")
        output_backup = os.path.join(self.backup_dir, f"output_{version}.json")
        metadata_file = os.path.join(self.backup_dir, f"metadata_{version}.json")

        # Copy files
        if os.path.exists(input_file):
            shutil.copy2(input_file, input_backup)

        if os.path.exists(output_file):
            shutil.copy2(output_file, output_backup)

        # Create metadata
        metadata = {
            "version": version,
            "timestamp": timestamp.isoformat(),
            "description": description or f"Backup created on {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "input_file": input_backup,
            "output_file": output_backup if os.path.exists(output_file) else None,
            "original_input": input_file,
            "original_output": output_file
        }

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Backup created: {version}")
        print(f"   Input: {input_backup}")
        if os.path.exists(output_file):
            print(f"   Output: {output_backup}")
        print(f"   Metadata: {metadata_file}")

        return version

    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []

        for filename in os.listdir(self.backup_dir):
            if filename.startswith("metadata_") and filename.endswith(".json"):
                metadata_path = os.path.join(self.backup_dir, filename)
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    backups.append(metadata)
                except Exception as e:
                    print(f"⚠️ Error reading backup metadata {filename}: {e}")

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups

    def restore_backup(self, version: str, target_dir: str = ".") -> bool:
        """Restore a backup to target directory."""
        metadata_file = os.path.join(self.backup_dir, f"metadata_{version}.json")

        if not os.path.exists(metadata_file):
            print(f"❌ Backup version {version} not found")
            return False

        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Restore input file
            input_backup = metadata["input_file"]
            if os.path.exists(input_backup):
                target_input = os.path.join(target_dir, "restored_input.json")
                shutil.copy2(input_backup, target_input)
                print(f"✅ Input restored to: {target_input}")

            # Restore output file if it exists
            output_backup = metadata.get("output_file")
            if output_backup and os.path.exists(output_backup):
                target_output = os.path.join(target_dir, "restored_output.json")
                shutil.copy2(output_backup, target_output)
                print(f"✅ Output restored to: {target_output}")

            print(f"✅ Backup {version} restored successfully")
            print(f"   Description: {metadata.get('description', 'N/A')}")
            print(f"   Original timestamp: {metadata['timestamp']}")

            return True

        except Exception as e:
            print(f"❌ Error restoring backup {version}: {e}")
            return False

    def delete_backup(self, version: str) -> bool:
        """Delete a specific backup."""
        files_to_delete = [
            f"input_{version}.json",
            f"output_{version}.json",
            f"metadata_{version}.json"
        ]

        deleted_count = 0
        for filename in files_to_delete:
            filepath = os.path.join(self.backup_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                deleted_count += 1

        if deleted_count > 0:
            print(f"✅ Backup {version} deleted ({deleted_count} files)")
            return True
        else:
            print(f"❌ No files found for backup {version}")
            return False

    def cleanup_old_backups(self, keep_count: int = 10):
        """Keep only the most recent N backups."""
        backups = self.list_backups()

        if len(backups) <= keep_count:
            print(f"ℹ️ Only {len(backups)} backups found, nothing to clean up")
            return

        # Delete oldest backups
        to_delete = backups[keep_count:]
        deleted_count = 0

        for backup in to_delete:
            version = backup['version']
            if self.delete_backup(version):
                deleted_count += 1

        print(f"🧹 Cleaned up {deleted_count} old backups, kept {keep_count} most recent")

    def export_backup_summary(self, output_file: str = "backup_summary.json"):
        """Export summary of all backups."""
        backups = self.list_backups()

        summary = {
            "backup_directory": self.backup_dir,
            "total_backups": len(backups),
            "export_timestamp": datetime.now().isoformat(),
            "backups": backups
        }

        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"📄 Backup summary exported to: {output_file}")

def auto_backup_wrapper(func):
    """Decorator to automatically create backups before running timetable operations."""
    def wrapper(*args, **kwargs):
        # Extract input/output paths from arguments
        input_path = args[0] if args else None
        output_path = args[1] if len(args) > 1 else kwargs.get('output_path', 'timetable_output.json')

        if input_path:
            backup_manager = TimetableBackupManager()
            backup_manager.create_backup(
                input_path,
                output_path,
                f"Auto-backup before running {func.__name__}"
            )

        # Run the original function
        result = func(*args, **kwargs)

        # Create backup of results if successful
        if input_path and os.path.exists(output_path):
            backup_manager.create_backup(
                input_path,
                output_path,
                f"Results from {func.__name__} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        return result

    return wrapper

class VersionControl:
    """Simple version control for timetable configurations."""

    def __init__(self, project_dir: str = "."):
        self.project_dir = project_dir
        self.versions_dir = os.path.join(project_dir, "versions")
        self.ensure_versions_dir()

    def ensure_versions_dir(self):
        """Create versions directory if it doesn't exist."""
        if not os.path.exists(self.versions_dir):
            os.makedirs(self.versions_dir)

    def commit_version(self, files: List[str], message: str) -> str:
        """Commit a new version of timetable files."""
        timestamp = datetime.now()
        version_id = timestamp.strftime("%Y%m%d_%H%M%S")
        version_dir = os.path.join(self.versions_dir, version_id)

        os.makedirs(version_dir)

        # Copy files to version directory
        copied_files = []
        for file_path in files:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                target_path = os.path.join(version_dir, filename)
                shutil.copy2(file_path, target_path)
                copied_files.append(filename)

        # Create version metadata
        metadata = {
            "version_id": version_id,
            "timestamp": timestamp.isoformat(),
            "message": message,
            "files": copied_files,
            "commit_author": os.getenv('USERNAME', 'unknown')
        }

        metadata_file = os.path.join(version_dir, "version.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Version {version_id} committed")
        print(f"   Message: {message}")
        print(f"   Files: {', '.join(copied_files)}")

        return version_id

    def list_versions(self) -> List[Dict]:
        """List all committed versions."""
        versions = []

        for version_dir in os.listdir(self.versions_dir):
            version_path = os.path.join(self.versions_dir, version_dir)
            if os.path.isdir(version_path):
                metadata_file = os.path.join(version_path, "version.json")
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    versions.append(metadata)

        versions.sort(key=lambda x: x['timestamp'], reverse=True)
        return versions

    def checkout_version(self, version_id: str, target_dir: str = ".") -> bool:
        """Checkout a specific version."""
        version_dir = os.path.join(self.versions_dir, version_id)

        if not os.path.exists(version_dir):
            print(f"❌ Version {version_id} not found")
            return False

        metadata_file = os.path.join(version_dir, "version.json")
        if not os.path.exists(metadata_file):
            print(f"❌ Version metadata not found for {version_id}")
            return False

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        # Copy files from version directory
        for filename in metadata['files']:
            source_path = os.path.join(version_dir, filename)
            target_path = os.path.join(target_dir, filename)

            if os.path.exists(source_path):
                shutil.copy2(source_path, target_path)
                print(f"✅ Restored: {filename}")

        print(f"✅ Checked out version {version_id}")
        print(f"   Message: {metadata['message']}")
        print(f"   Date: {metadata['timestamp']}")

        return True

def print_backup_help():
    """Print help information for backup system."""
    help_text = """
🔄 BACKUP SYSTEM USAGE

Basic Commands:
  backup_manager = TimetableBackupManager()
  
  # Create backup
  backup_manager.create_backup("input.json", "output.json", "My backup")
  
  # List backups
  backups = backup_manager.list_backups()
  
  # Restore backup
  backup_manager.restore_backup("20251231_143022")
  
  # Clean up old backups
  backup_manager.cleanup_old_backups(keep_count=5)

Version Control:
  vc = VersionControl()
  
  # Commit version
  vc.commit_version(["input.json", "output.json"], "Initial timetable")
  
  # List versions
  versions = vc.list_versions()
  
  # Checkout version
  vc.checkout_version("20251231_143022")

Auto-backup Decorator:
  @auto_backup_wrapper
  def solve_from_json(input_path, output_path):
      # Function automatically backed up
      pass
"""
    print(help_text)

if __name__ == "__main__":
    print_backup_help()

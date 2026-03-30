from os import makedirs, remove, listdir, urandom, fsync
from os.path import exists, join, basename, getsize
from sqlite3 import connect, Error as SQLiteError
from uuid import uuid4
from zipfile import ZipFile
from datetime import datetime
from crypto_service import CryptoService


class VaultManager:
    def __init__(self, db_path="vault_metadata.db", storage_dir="vault_data"):
        self.db_path = db_path
        self.storage_dir = storage_dir

        # Using 'makedirs' from os
        makedirs(self.storage_dir, exist_ok=True)
        self._initialise_database()

    def _initialise_database(self):
        try:
            with connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vault_entries (
                        entry_id TEXT PRIMARY KEY,
                        site_name TEXT NOT NULL,
                        username TEXT,
                        json_file_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
        except SQLiteError as e:
            print(f"Database error during init: {e}")

    def add_entry(
        self, site_name: str, username: str, password: str, master_password: str
    ):
        """Encrypts the password and logs metadata."""
        entry_id = str(uuid4())
        json_filename = join(self.storage_dir, f"entry_{entry_id}.json")

        encrypted_data = CryptoService.encrypt_entry(password, master_password)
        CryptoService.save_to_file(encrypted_data, json_filename)

        try:
            with connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO vault_entries (entry_id, site_name, username, json_file_path) VALUES (?, ?, ?, ?)",
                    (entry_id, site_name, username, json_filename),
                )
            print(f"[*] Secured entry for: {site_name}")
        except SQLiteError as e:
            print(f"Failed to write to database: {e}")

    def get_all_entries(self):
        with connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT site_name, username, entry_id FROM vault_entries")
            return cursor.fetchall()

    def decrypt_vault_entry(self, entry_id: str, master_password: str):
        """Finds the JSON file and decrypts it using 'exists'."""
        with connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT json_file_path FROM vault_entries WHERE entry_id = ?",
                (entry_id,),
            )
            result = cursor.fetchone()

        if result and exists(result[0]):
            encrypted_blob = CryptoService.load_from_file(result[0])
            return CryptoService.decrypt_entry(encrypted_blob, master_password)
        else:
            raise FileNotFoundError(f"Entry {entry_id} not found on disk.")

    def delete_entry(self, entry_id: str):
        """Securely overwrites (shreds) the physical file before removing the SQL record."""
        with connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 1. Locate the file path
            cursor.execute(
                "SELECT json_file_path FROM vault_entries WHERE entry_id = ?",
                (entry_id,),
            )
            result = cursor.fetchone()

            if result:
                file_path = result[0]

                # 2. PHYSICAL SHREDDING
                if exists(file_path):
                    try:
                        file_size = getsize(file_path)
                        # Open in 'r+b' to overwrite existing bytes from the start
                        with open(file_path, "r+b", buffering=0) as f:
                            # Overwrite with cryptographically secure random noise
                            f.write(urandom(file_size))
                            f.flush()
                            # Force the OS/Hardware to commit the write immediately
                            fsync(f.fileno())

                        # Now that the data is garbage, remove the file name
                        remove(file_path)
                    except Exception as e:
                        print(f"[!] Warning: Could not shred file {file_path}: {e}")

                # 3. DATABASE CLEANUP
                cursor.execute(
                    "DELETE FROM vault_entries WHERE entry_id = ?", (entry_id,)
                )
                print(f"[*] Securely shredded and deleted entry {entry_id}.")

    def create_backup(self, backup_folder="backups"):
        """Creates a ZIP archive using 'ZipFile', 'datetime', and 'basename'."""
        makedirs(backup_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = join(backup_folder, f"backup_{timestamp}.zip")

        with ZipFile(backup_path, "w") as backup_zip:
            # Backup DB
            if exists(self.db_path):
                backup_zip.write(self.db_path, arcname=basename(self.db_path))
            # Backup all JSON files
            for file in listdir(self.storage_dir):
                f_path = join(self.storage_dir, file)
                backup_zip.write(f_path, arcname=join(self.storage_dir, file))

        print(f"[*] Backup created at {backup_path}")
        return backup_path


if __name__ == "__main__":
    manager = VaultManager()
    master_pass = "StrongMasterPassword!"

    # Add an entry to test
    # manager.add_entry("GitHub", "murai_dev", "git_secret_pass", master_pass)

    print("\n--- Listing Entries ---")
    entries = manager.get_all_entries()
    for site, user, eid in entries:
        print(f"Site: {site} | User: {user} | ID: {eid}")

    if entries:
        print("\n--- Testing Decryption ---")
        latest_id = entries[-1][2]
        try:
            pw = manager.decrypt_vault_entry(latest_id, master_pass)
            print(f"Decrypted: {pw}")
        except Exception as e:
            print(f"Error: {e}")
    # Delete an entry to test
    manager.delete_entry("7209a4c2-613f-4161-89c4-c9a0512b0bb2")

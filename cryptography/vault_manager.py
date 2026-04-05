from os import makedirs, remove, listdir, urandom, fsync
from os.path import exists, join, basename, getsize
from sqlite3 import connect, Error as SQLiteError
from uuid import uuid4
from zipfile import ZipFile
from datetime import datetime
import logging
from crypto_service import CryptoService

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class VaultManager:
    def __init__(self, db_path="vault_metadata.db", storage_dir="vault_data"):
        self.db_path = db_path
        self.storage_dir = storage_dir

        makedirs(self.storage_dir, exist_ok=True)
        self._initialise_database()

    def _initialise_database(self):
        try:
            with connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL")  # Concurrency safe
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
            raise RuntimeError(f"Database initialization failed: {e}")

    def add_entry(
        self, site_name: str, username: str, password: str, master_password: str
    ):
        entry_id = str(uuid4())
        json_filename = join(self.storage_dir, f"entry_{entry_id}.json")

        try:
            encrypted_data = CryptoService.encrypt_entry(password, master_password)
            CryptoService.save_to_file(encrypted_data, json_filename)

            with connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO vault_entries (entry_id, site_name, username, json_file_path) VALUES (?, ?, ?, ?)",
                    (entry_id, site_name, username, json_filename),
                )
            logging.info(f"Secured entry for: {site_name}")

        except Exception as e:
            raise RuntimeError(f"Failed to add entry: {e}")

    def get_all_entries(self):
        try:
            with connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT site_name, username, entry_id FROM vault_entries"
                )
                return cursor.fetchall()
        except SQLiteError as e:
            raise RuntimeError(f"Failed to retrieve entries: {e}")

    def decrypt_vault_entry(self, entry_id: str, master_password: str):
        try:
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

        except Exception as e:
            raise RuntimeError(f"Decryption failed: {e}")

    def delete_entry(self, entry_id: str):
        try:
            with connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT json_file_path FROM vault_entries WHERE entry_id = ?",
                    (entry_id,),
                )
                result = cursor.fetchone()

                if not result:
                    logging.warning(f"Entry {entry_id} does not exist.")
                    return

                file_path = result[0]

                if exists(file_path):
                    file_size = getsize(file_path)
                    with open(file_path, "r+b", buffering=0) as f:
                        f.write(urandom(file_size))
                        f.flush()
                        fsync(f.fileno())
                    remove(file_path)

                cursor.execute(
                    "DELETE FROM vault_entries WHERE entry_id = ?", (entry_id,)
                )
                logging.info(f"Securely shredded and deleted entry {entry_id}.")

        except Exception as e:
            raise RuntimeError(f"Failed to delete entry {entry_id}: {e}")

    def create_backup(self, backup_folder="backups", master_password=None):
        makedirs(backup_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = join(backup_folder, f"backup_{timestamp}.zip")

        try:
            with ZipFile(backup_path, "w") as backup_zip:
                if exists(self.db_path):
                    backup_zip.write(self.db_path, arcname=basename(self.db_path))
                for file in listdir(self.storage_dir):
                    f_path = join(self.storage_dir, file)
                    backup_zip.write(f_path, arcname=join(self.storage_dir, file))

            logging.info(f"Backup created at {backup_path}")

            if master_password:
                encrypted_backup = CryptoService.encrypt_entry(
                    open(backup_path, "rb").read(), master_password
                )
                encrypted_backup_path = backup_path + ".enc"
                CryptoService.save_to_file(encrypted_backup, encrypted_backup_path)
                remove(backup_path)
                backup_path = encrypted_backup_path
                logging.info(f"Backup encrypted at {backup_path}")

            return backup_path

        except Exception as e:
            raise RuntimeError(f"Backup creation failed: {e}")

    def restore_from_backup(
        self, backup_path: str, master_password: str, restore_dir="restored_vault"
    ):
        try:
            # 1. Load the encrypted hex/dict data from the .enc file
            encrypted_data = CryptoService.load_from_file(backup_path)

            # 2. Decrypt back to raw ZIP bytes
            decrypted_zip_bytes = CryptoService.decrypt_entry(
                encrypted_data, master_password
            )

            if isinstance(decrypted_zip_bytes, str):
                raise ValueError(
                    "Decrypted data is text, but a binary ZIP was expected."
                )

            # 3. Save the decrypted bytes to a temporary ZIP file
            temp_zip = "temp_restore.zip"
            with open(temp_zip, "wb") as f:
                f.write(decrypted_zip_bytes)

            # 4. Extract the ZIP contents
            makedirs(restore_dir, exist_ok=True)
            with ZipFile(temp_zip, "r") as zip_ref:
                zip_ref.extractall(restore_dir)

            # 5. Cleanup the temporary unencrypted ZIP
            remove(temp_zip)

            logging.info(f"Vault successfully restored to: {restore_dir}")
            return restore_dir

        except Exception as e:
            raise RuntimeError(f"Restore failed: {e}")


if __name__ == "__main__":
    manager = VaultManager()
    master_pass = "StrongMasterPassword!"

    # Add a test entry
    manager.add_entry("GitHub", "murai_dev", "git_secret_pass", master_pass)

    logging.info("--- Listing Entries ---")
    entries = manager.get_all_entries()
    for site, user, eid in entries:
        logging.info(f"Site: {site} | User: {user} | ID: {eid}")

    if entries:
        latest_id = entries[-1][2]
        logging.info("--- Testing Decryption ---")
        try:
            pw = manager.decrypt_vault_entry(latest_id, master_pass)
            logging.info(f"Decrypted: {pw}")
        except Exception as e:
            logging.error(e)

    # Test creating encrypted backup and decrypting it
    backup_path = manager.create_backup(master_password=master_pass)
    logging.info(f"--- Testing Backup Decryption ---")
    try:
        encrypted_backup_data = CryptoService.load_from_file(backup_path)
        decrypted_backup_bytes = CryptoService.decrypt_entry(
            encrypted_backup_data, master_pass
        )

        temp_backup_path = "temp_backup.zip"
        with open(temp_backup_path, "wb") as f:
            f.write(decrypted_backup_bytes)

        # List contents of the decrypted backup
        with ZipFile(temp_backup_path, "r") as zip_ref:
            logging.info("Backup contents:")
            for name in zip_ref.namelist():
                logging.info(f" - {name}")

        remove(temp_backup_path)
    except Exception as e:
        logging.error(f"Backup decryption test failed: {e}")

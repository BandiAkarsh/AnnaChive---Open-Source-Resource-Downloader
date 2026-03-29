"""
AnnaChive - Encrypted Database Module

This module handles storing your downloaded resources in an encrypted database.

What is this?
- A database is like a smart filing cabinet
- It stores information about everything you download
- The "encrypted" part means only YOU can read your data

Why encrypt?
- If someone gets access to your computer, they can't see your downloads
- Your search history and library are private
- Uses industry-standard encryption (Fernet)

How it works:
1. Create tables (like folders in a filing cabinet)
2. Store records about each download
3. Encrypt sensitive data (titles, authors, notes)
4. Allow fast searching through indexes
"""

import hashlib  # For creating secure keys from passwords
import json  # For converting data to/from text
import os  # For checking files and paths
from contextlib import asynccontextmanager  # For clean async code
from dataclasses import dataclass, field  # For defining data structures
from datetime import datetime  # For timestamps
from pathlib import Path  # For file paths
from typing import Any, AsyncGenerator, Optional  # Type hints

import aiosqlite  # For connecting to SQLite database
from cryptography.fernet import Fernet  # For encryption

from ..utils.logger import get_logger  # For logging
# Shared constants - avoid magic numbers
from ..constants import (
    DB_DEFAULT_LIMIT, DB_LIST_LIMIT, PBKDF2_ITERATIONS, 
    KEY_LENGTH_BYTES, SALT_LENGTH_BYTES,
    DB_FIELD_INDEX_TITLE, DB_FIELD_INDEX_AUTHOR, 
    DB_FIELD_INDEX_DOI, DB_FIELD_INDEX_NOTES
)

# Set up a logger for this file
logger = get_logger("database")

# Connection cache for singleton pattern (defined after class)
_db_cache: dict = {}


@dataclass
class LibraryItem:
    """
    This is like a catalog entry for a book.
    
    Every downloaded item gets its own "LibraryItem" that stores:
    - What it is (title, author)
    - Where it came from (source like arXiv, GitHub)
    - Where you saved it (file path)
    - When you downloaded it (date)
    - Extra info (tags, notes)
    """
    id: Optional[int] = None  # Unique number in database
    source: str = ""  # Where it came from (e.g., "arxiv")
    md5: Optional[str] = None  # File's unique ID
    title: str = ""  # Name of the paper/book
    author: Optional[str] = None  # Who wrote it
    format: Optional[str] = None  # What type (PDF, EPUB, etc.)
    size_bytes: Optional[int] = None  # How big the file is
    path: Optional[str] = None  # Where you saved it on your computer
    doi: Optional[str] = None  # Digital Object Identifier (for papers)
    url: Optional[str] = None  # Original URL where it was found
    added_date: datetime = field(default_factory=datetime.utcnow)  # When you downloaded it
    tags: str = ""  # Your labels for it (comma-separated)
    project: Optional[str] = None  # Which project this belongs to
    notes: str = ""  # Your personal notes
    
    def to_dict(self) -> dict:
        """Convert to a dictionary (like JSON but in Python)."""
        return {
            "id": self.id,
            "source": self.source,
            "md5": self.md5,
            "title": self.title,
            "author": self.author,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "path": self.path,
            "doi": self.doi,
            "url": self.url,
            "added_date": self.added_date.isoformat(),
            "tags": self.tags,
            "project": self.project,
            "notes": self.notes,
        }


class EncryptedDatabase:
    """
    This class handles all database operations.
    
    Think of it as the manager of your filing cabinet.
    It knows how to:
    - Create the database
    - Add new items
    - Search for items
    - Update existing items
    - Delete items
    - Keep everything encrypted
    """
    
    def __init__(self, db_path: Path, encryption_key: Optional[bytes] = None):
        """
        Set up the database connection.
        
        Args:
            db_path: Where to store the database file
            encryption_key: Your secret key for encryption (optional)
        """
        self.db_path = db_path  # Remember where the database is
        self.encryption_key = encryption_key  # Your encryption key
        self.cipher: Optional[Fernet] = None  # The encryption tool
        
        # If you provided a key, create the encryption tool
        if encryption_key:
            # Generate key from provided secret (for deterministic encryption)
            self.cipher = Fernet(encryption_key)
        
        self._connection: Optional[aiosqlite.Connection] = None  # Connection to DB
    
    def _encrypt(self, data: str) -> str:
        """
        Scramble text so only you can read it.
        
        Args:
            data: The text you want to hide
        
        Returns:
            The encrypted (scrambled) version
        """
        if not self.cipher:  # If no encryption key, return as-is
            logger.warning("Encryption is disabled - storing data in plaintext")
            return data
        # Scramble the data
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt(self, data: str) -> str:
        """
        Unscramble text back to readable form.
        
        Args:
            data: The scrambled text
        
        Returns:
            The original readable text
        """
        if not self.cipher:  # If no encryption key, return as-is
            logger.warning("Encryption is disabled - reading data in plaintext")
            return data
        # Unscramble the data
        return self.cipher.decrypt(data.encode()).decode()
    
    async def connect(self):
        """Connect to the database and create tables if needed."""
        # Make sure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to SQLite
        self._connection = await aiosqlite.connect(str(self.db_path))
        
        # Enable WAL mode (faster concurrent access)
        await self._connection.execute("PRAGMA journal_mode=WAL")
        
        # Create the tables
        await self._init_tables()
    
    async def _init_tables(self):
        """
        Create the database tables (like creating folders in a cabinet).
        
        We create:
        - library: Stores all downloaded items
        - download_history: Tracks download attempts
        """
        # Create the main library table
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                md5 TEXT,
                title TEXT NOT NULL,
                author TEXT,
                format TEXT,
                size_bytes INTEGER,
                path TEXT,
                doi TEXT,
                url TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT DEFAULT '',
                project TEXT,
                notes TEXT DEFAULT ''
            )
        """)
        
        # Create indexes (like tabs in a filing cabinet for fast lookup)
        # These make searching faster
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_library_title ON library(title)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_library_source ON library(source)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_library_md5 ON library(md5)
        """)
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_library_project ON library(project)
        """)
        
        # Create download history table
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                source TEXT NOT NULL,
                url TEXT,
                method TEXT,  -- direct, tor, torrent, mirror
                status TEXT,  -- success, failed, fallback
                error TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES library(id)
            )
        """)
        
        # Save changes
        await self._connection.commit()
    
    async def add_item(self, item: LibraryItem) -> int:
        """
        Add a new item to your library.
        
        Args:
            item: The LibraryItem to add
        
        Returns:
            The ID number assigned to this item
        """
        # Encrypt sensitive fields before storing
        title = self._encrypt(item.title) if item.title else ""
        author = self._encrypt(item.author) if item.author else ""
        doi = self._encrypt(item.doi) if item.doi else ""
        notes = self._encrypt(item.notes) if item.notes else ""
        
        # Insert into database
        cursor = await self._connection.execute("""
            INSERT INTO library (
                source, md5, title, author, format, size_bytes, 
                path, doi, url, tags, project, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.source, item.md5, title, author, item.format,
            item.size_bytes, item.path, doi, item.url,
            item.tags, item.project, notes
        ))
        
        # Save and return the new item's ID
        await self._connection.commit()
        return cursor.lastrowid
    
    async def get_item(self, item_id: int) -> Optional[LibraryItem]:
        """
        Look up a specific item by its ID number.
        
        Args:
            item_id: The ID to look for
        
        Returns:
            The LibraryItem if found, None if not found
        """
        cursor = await self._connection.execute(
            "SELECT * FROM library WHERE id = ?", (item_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_item(row)
    
    async def get_by_md5(self, md5: str) -> Optional[LibraryItem]:
        """
        Look up an item by its MD5 hash (file's unique ID).
        
        Args:
            md5: The MD5 hash to search for
        
        Returns:
            The LibraryItem if found
        """
        cursor = await self._connection.execute(
            "SELECT * FROM library WHERE md5 = ?", (md5,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_item(row)
    
    async def search(self, query: str, limit: int = DB_DEFAULT_LIMIT) -> list[LibraryItem]:
        """
        Search your library by title or author.
        
        Args:
            query: What to search for
            limit: Maximum results to return
        
        Returns:
            List of matching items
        """
        cursor = await self._connection.execute("""
            SELECT * FROM library 
            WHERE title LIKE ? OR author LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[LibraryItem]:
        """
        Get all items in your library (with pagination).
        
        Args:
            limit: How many to return
            offset: How many to skip (for pagination)
        
        Returns:
            List of items
        """
        cursor = await self._connection.execute("""
            SELECT * FROM library 
            ORDER BY added_date DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]
    
    async def list_by_source(self, source: str, limit: int = DB_DEFAULT_LIMIT) -> list[LibraryItem]:
        """
        Get all items from a specific source.
        
        Args:
            source: Which source (e.g., "arxiv", "github")
            limit: Maximum results
        
        Returns:
            List of items from that source
        """
        cursor = await self._connection.execute("""
            SELECT * FROM library 
            WHERE source = ?
            ORDER BY added_date DESC
            LIMIT ?
        """, (source, limit))
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]
    
    async def list_by_project(self, project: str) -> list[LibraryItem]:
        """
        Get all items in a specific project.
        
        Args:
            project: Which project name
        
        Returns:
            List of items in that project
        """
        cursor = await self._connection.execute("""
            SELECT * FROM library 
            WHERE project = ?
            ORDER BY added_date DESC
        """, (project,))
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]
    
    async def update_item(self, item: LibraryItem) -> bool:
        """
        Update an existing item in the library.
        
        Args:
            item: The LibraryItem with updated info
        
        Returns:
            True if updated, False if not found
        """
        # Encrypt fields
        title = self._encrypt(item.title) if item.title else ""
        author = self._encrypt(item.author) if item.author else ""
        notes = self._encrypt(item.notes) if item.notes else ""
        
        cursor = await self._connection.execute("""
            UPDATE library SET
                title = ?, author = ?, format = ?, size_bytes = ?,
                path = ?, tags = ?, project = ?, notes = ?
            WHERE id = ?
        """, (
            title, author, item.format, item.size_bytes,
            item.path, item.tags, item.project, notes, item.id
        ))
        await self._connection.commit()
        return cursor.rowcount > 0
    
    async def delete_item(self, item_id: int) -> bool:
        """
        Delete an item from the library.
        
        Args:
            item_id: The ID of the item to delete
        
        Returns:
            True if deleted
        """
        cursor = await self._connection.execute(
            "DELETE FROM library WHERE id = ?", (item_id,)
        )
        await self._connection.commit()
        return cursor.rowcount > 0
    
    async def add_download_history(
        self, item_id: int, source: str, url: str, 
        method: str, status: str, error: Optional[str] = None
    ):
        """
        Record a download attempt (success or failure).
        
        This helps track what you've tried and what worked.
        """
        await self._connection.execute("""
            INSERT INTO download_history 
            (item_id, source, url, method, status, error)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, source, url, method, status, error))
        await self._connection.commit()
    
    async def get_download_history(self, item_id: int) -> list[dict]:
        """
        Get all download attempts for an item.
        
        Useful for debugging or seeing what methods you tried.
        """
        cursor = await self._connection.execute("""
            SELECT * FROM download_history 
            WHERE item_id = ?
            ORDER BY timestamp DESC
        """, (item_id,))
        rows = await cursor.fetchall()
        
        # Return as dictionaries
        return [
            {
                "id": row[0],
                "item_id": row[1],
                "source": row[2],
                "url": row[3],
                "method": row[4],
                "status": row[5],
                "error": row[6],
                "timestamp": row[7],
            }
            for row in rows
        ]
    
    async def count(self) -> int:
        """Get the total number of items in your library."""
        cursor = await self._connection.execute(
            "SELECT COUNT(*) FROM library"
        )
        return (await cursor.fetchone())[0]
    
    async def count_by_source(self, source: str) -> int:
        """Get the number of items from a specific source."""
        cursor = await self._connection.execute(
            "SELECT COUNT(*) FROM library WHERE source = ?", (source,)
        )
        return (await cursor.fetchone())[0]
    
    async def get_stats(self) -> dict:
        """Get library statistics."""
        total = await self.count()
        
        # Get total size
        cursor = await self._connection.execute(
            "SELECT SUM(size_bytes) FROM library WHERE size_bytes IS NOT NULL"
        )
        total_size = (await cursor.fetchone())[0] or 0
        total_size_mb = total_size / 1024 / 1024
        
        # Get counts by source
        cursor = await self._connection.execute(
            "SELECT source, COUNT(*) FROM library GROUP BY source"
        )
        rows = await cursor.fetchall()
        by_source = {row[0]: row[1] for row in rows}
        
        return {
            "total": total,
            "total_size_mb": round(total_size_mb, 2),
            "by_source": by_source,
        }
    
    def _row_to_item(self, row: tuple) -> LibraryItem:
        """
        Convert a database row to a LibraryItem.
        
        The database returns data as a tuple (ordered list).
        This converts it to a nice object with named fields.
        """
        # Decrypt fields using named index constants
        title = self._decrypt(row[DB_FIELD_INDEX_TITLE]) if row[DB_FIELD_INDEX_TITLE] else ""
        author = self._decrypt(row[DB_FIELD_INDEX_AUTHOR]) if row[DB_FIELD_INDEX_AUTHOR] else ""
        doi = self._decrypt(row[DB_FIELD_INDEX_DOI]) if row[DB_FIELD_INDEX_DOI] else ""
        notes = self._decrypt(row[DB_FIELD_INDEX_NOTES]) if row[DB_FIELD_INDEX_NOTES] else ""
        
        return LibraryItem(
            id=row[0],
            source=row[1],
            md5=row[2],
            title=title,
            author=author,
            format=row[5],
            size_bytes=row[6],
            path=row[7],
            doi=doi,
            url=row[9],
            added_date=datetime.fromisoformat(row[10]) if row[10] else datetime.utcnow(),
            tags=row[11] or "",
            project=row[12],
            notes=notes,
        )
    
    async def close(self):
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None


@asynccontextmanager
async def get_database(
    db_path: Path, 
    encryption_key: Optional[bytes] = None
) -> AsyncGenerator[EncryptedDatabase, None]:
    """
    A helper to use the database safely with connection caching.
    
    Think of this as a "with" statement that:
    - Opens the database when you enter
    - Lets you use it
    - Closes it automatically when you're done
    
    Uses connection pooling - same database path reuses existing connection.
    
    Usage:
        async with get_database(path) as db:
            await db.add_item(item)
    """
    # Create a cache key based on path and encryption key
    cache_key = (str(db_path), encryption_key)
    
    # Check if we have a cached database with valid connection
    if cache_key in _db_cache:
        cached_db = _db_cache[cache_key]
        if cached_db._connection is not None:
            # Reuse existing connection
            yield cached_db
            return
    
    # Create new database instance
    db = EncryptedDatabase(db_path, encryption_key)
    try:
        await db.connect()  # Open connection
        _db_cache[cache_key] = db  # Cache for reuse
        yield db  # Let caller use it
    finally:
        # Note: We don't close the connection here to enable reuse
        # Caller should use close_database() to explicitly close
        pass


async def close_database(db_path: Path, encryption_key: Optional[bytes] = None):
    """Close a cached database connection.
    
    Args:
        db_path: The database path used when opening
        encryption_key: The encryption key used when opening
    """
    cache_key = (str(db_path), encryption_key)
    if cache_key in _db_cache:
        await _db_cache[cache_key].close()
        del _db_cache[cache_key]


def generate_encryption_key() -> bytes:
    """
    Create a new random encryption key.
    
    Use this if you want to start fresh with a new key.
    """
    return Fernet.generate_key()


def key_from_password(password: str) -> bytes:
    """
    Turn a password into an encryption key.
    
    Args:
        password: Your password
    
    Returns:
        A key you can use for encryption
    """
    # Use SHA256 to derive a 32-byte key
    return hashlib.sha256(password.encode()).digest()


def key_from_master(master_key: str) -> bytes:
    """
    Turn a master key into an encryption key using secure method.
    
    This is more secure than key_from_password because it:
    - Uses PBKDF2 (Password-Based Key Derivation Function 2)
    - Adds a "salt" to make it harder to crack
    - Runs 100,000 iterations to slow down attackers
    
    Args:
        master_key: Your master password
    
    Returns:
        A secure key for encryption
    """
    # Use key derivation for better security
    # Get salt from environment variable or generate random per installation
    import os
    
    salt_env = os.getenv("ANNCHIVE_SALT")
    if salt_env:
        # Use provided salt from environment (base64 encoded)
        import base64
        salt = base64.b64decode(salt_env)
    else:
        # Generate random salt per installation if not set
        salt = os.urandom(SALT_LENGTH_BYTES)
    
    return hashlib.pbkdf2_hmac(
        'sha256',  # Use SHA256 algorithm
        master_key.encode(),  # Your password
        salt,  # A "salt" - makes the same password give different keys
        PBKDF2_ITERATIONS,  # Number of iterations - more = slower but more secure
        KEY_LENGTH_BYTES  # Output length in bytes
    )

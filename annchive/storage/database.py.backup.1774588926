"""Encrypted SQLite database for annchive library."""
import hashlib
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

import aiosqlite
from cryptography.fernet import Fernet

from .logger import get_logger

logger = get_logger("database")


@dataclass
class LibraryItem:
    """Represents a resource in the library."""
    id: Optional[int] = None
    source: str = ""
    md5: Optional[str] = None
    title: str = ""
    author: Optional[str] = None
    format: Optional[str] = None
    size_bytes: Optional[int] = None
    path: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    added_date: datetime = field(default_factory=datetime.utcnow)
    tags: str = ""  # comma-separated
    project: Optional[str] = None  # project this belongs to
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
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
    """SQLite database with optional encryption for the library.
    
    Security features:
    - Optional Fernet encryption for sensitive fields
    - No external connections - local only
    - Encrypted at rest
    """
    
    def __init__(self, db_path: Path, encryption_key: Optional[bytes] = None):
        self.db_path = db_path
        self.encryption_key = encryption_key
        self.cipher: Optional[Fernet] = None
        
        if encryption_key:
            # Generate key from provided secret (for deterministic encryption)
            self.cipher = Fernet(encryption_key)
        
        self._connection: Optional[aiosqlite.Connection] = None
    
    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        if not self.cipher:
            return data
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt(self, data: str) -> str:
        """Decrypt sensitive data."""
        if not self.cipher:
            return data
        return self.cipher.decrypt(data.encode()).decode()
    
    async def connect(self):
        """Connect to the database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(str(self.db_path))
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._init_tables()
    
    async def _init_tables(self):
        """Initialize database tables."""
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
        
        # Index for searching
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
        
        # Download history table
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
        
        await self._connection.commit()
    
    async def add_item(self, item: LibraryItem) -> int:
        """Add a new item to the library."""
        # Encrypt sensitive fields if encryption enabled
        title = self._encrypt(item.title) if item.title else ""
        author = self._encrypt(item.author) if item.author else ""
        doi = self._encrypt(item.doi) if item.doi else ""
        notes = self._encrypt(item.notes) if item.notes else ""
        
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
        await self._connection.commit()
        return cursor.lastrowid
    
    async def get_item(self, item_id: int) -> Optional[LibraryItem]:
        """Get an item by ID."""
        cursor = await self._connection.execute(
            "SELECT * FROM library WHERE id = ?", (item_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_item(row)
    
    async def get_by_md5(self, md5: str) -> Optional[LibraryItem]:
        """Get an item by MD5 hash."""
        cursor = await self._connection.execute(
            "SELECT * FROM library WHERE md5 = ?", (md5,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_item(row)
    
    async def search(self, query: str, limit: int = 50) -> list[LibraryItem]:
        """Search library by title or author."""
        cursor = await self._connection.execute("""
            SELECT * FROM library 
            WHERE title LIKE ? OR author LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[LibraryItem]:
        """List all items with pagination."""
        cursor = await self._connection.execute("""
            SELECT * FROM library 
            ORDER BY added_date DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]
    
    async def list_by_source(self, source: str, limit: int = 50) -> list[LibraryItem]:
        """List items filtered by source."""
        cursor = await self._connection.execute("""
            SELECT * FROM library 
            WHERE source = ?
            ORDER BY added_date DESC
            LIMIT ?
        """, (source, limit))
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]
    
    async def list_by_project(self, project: str) -> list[LibraryItem]:
        """List items belonging to a project."""
        cursor = await self._connection.execute("""
            SELECT * FROM library 
            WHERE project = ?
            ORDER BY added_date DESC
        """, (project,))
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]
    
    async def update_item(self, item: LibraryItem) -> bool:
        """Update an existing item."""
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
        """Delete an item."""
        cursor = await self._connection.execute(
            "DELETE FROM library WHERE id = ?", (item_id,)
        )
        await self._connection.commit()
        return cursor.rowcount > 0
    
    async def add_download_history(
        self, item_id: int, source: str, url: str, 
        method: str, status: str, error: Optional[str] = None
    ):
        """Log a download attempt."""
        await self._connection.execute("""
            INSERT INTO download_history 
            (item_id, source, url, method, status, error)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, source, url, method, status, error))
        await self._connection.commit()
    
    async def get_download_history(self, item_id: int) -> list[dict]:
        """Get download history for an item."""
        cursor = await self._connection.execute("""
            SELECT * FROM download_history 
            WHERE item_id = ?
            ORDER BY timestamp DESC
        """, (item_id,))
        rows = await cursor.fetchall()
        
        # Return as dicts (no decryption needed - metadata only)
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
        """Get total number of items."""
        cursor = await self._connection.execute(
            "SELECT COUNT(*) FROM library"
        )
        return (await cursor.fetchone())[0]
    
    async def count_by_source(self, source: str) -> int:
        """Get count of items by source."""
        cursor = await self._connection.execute(
            "SELECT COUNT(*) FROM library WHERE source = ?", (source,)
        )
        return (await cursor.fetchone())[0]
    
    def _row_to_item(self, row: tuple) -> LibraryItem:
        """Convert database row to LibraryItem."""
        # Decrypt fields if needed
        title = self._decrypt(row[3]) if row[3] else ""
        author = self._decrypt(row[4]) if row[4] else ""
        doi = self._decrypt(row[8]) if row[8] else ""
        notes = self._decrypt(row[13]) if row[13] else ""
        
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
    """Context manager for database access."""
    db = EncryptedDatabase(db_path, encryption_key)
    try:
        await db.connect()
        yield db
    finally:
        await db.close()


def generate_encryption_key() -> bytes:
    """Generate a new encryption key."""
    return Fernet.generate_key()


def key_from_password(password: str) -> bytes:
    """Derive encryption key from password."""
    # Use SHA256 to derive a 32-byte key
    return hashlib.sha256(password.encode()).digest()


def key_from_master(master_key: str) -> bytes:
    """Derive encryption key from master key."""
    # Use key derivation for better security
    return hashlib.pbkdf2_hmac(
        'sha256', 
        master_key.encode(), 
        b'annchive_salt_v1',  # Static salt (in production, use secure storage)
        100000, 
        32
    )
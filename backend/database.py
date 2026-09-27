"""
Database module for BIS RAG chat history storage.
Handles SQLite database operations for storing chat sessions and messages.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path


class ChatDatabase:
    """Manages SQLite database for chat history storage."""

    def __init__(self, db_path: str = "storage/chat_history.db"):
        """
        Initialize the database connection and create tables if needed.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        # Ensure storage directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def init_database(self):
        """Initialize database tables if they don't exist."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT  -- JSON string for additional metadata
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,  -- 'user' or 'assistant'
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,  -- JSON string for additional metadata
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp);
            """)
            conn.commit()

    def create_session(self, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new chat session.

        Args:
            session_id: Optional session ID (will generate UUID if not provided)
            metadata: Optional metadata to store with the session

        Returns:
            The session ID
        """
        import uuid
        if session_id is None:
            session_id = str(uuid.uuid4())

        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_sessions (id, metadata) VALUES (?, ?)",
                (session_id, json.dumps(metadata) if metadata else None)
            )
            conn.commit()
        return session_id

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM chat_sessions WHERE id = ?",
                (session_id,)
            )
            return cursor.fetchone() is not None

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Add a message to a chat session.

        Args:
            session_id: The session ID
            role: 'user' or 'assistant'
            content: The message content
            metadata: Optional metadata to store with the message

        Returns:
            The message ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO chat_messages (session_id, role, content, metadata)
                   VALUES (?, ?, ?, ?)""",
                (session_id, role, content, json.dumps(metadata) if metadata else None)
            )
            conn.commit()
            return cursor.lastrowid

    def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve messages for a chat session.

        Args:
            session_id: The session ID
            limit: Optional maximum number of messages to return (most recent first)

        Returns:
            List of message dictionaries
        """
        with self.get_connection() as conn:
            if limit:
                cursor = conn.execute(
                    """SELECT id, session_id, role, content, timestamp, metadata
                       FROM chat_messages
                       WHERE session_id = ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (session_id, limit)
                )
            else:
                cursor = conn.execute(
                    """SELECT id, session_id, role, content, timestamp, metadata
                       FROM chat_messages
                       WHERE session_id = ?
                       ORDER BY timestamp ASC""",
                    (session_id,)
                )

            messages = []
            for row in cursor.fetchall():
                message = {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                }
                messages.append(message)

            # If we used DESC order for limit, reverse to get chronological order
            if limit:
                messages.reverse()

            return messages

    def get_recent_messages_for_context(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent messages for use as context in query understanding.

        Args:
            session_id: The session ID
            limit: Number of recent messages to retrieve

        Returns:
            List of recent message dictionaries (oldest first)
        """
        return self.get_session_messages(session_id, limit=limit)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a chat session and all its messages.

        Args:
            session_id: The session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all chat sessions (most recently updated first).

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, updated_at, metadata
                   FROM chat_sessions
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (limit,)
            )

            sessions = []
            for row in cursor.fetchall():
                session = {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                }
                sessions.append(session)
            return sessions


# Global database instance
chat_database = ChatDatabase()
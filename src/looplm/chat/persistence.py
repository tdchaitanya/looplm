# src/looplm/chat/persistence.py
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .session import ChatSession


class SessionManager:
    """Manages chat session persistence and operations"""

    def __init__(self):
        """Initialize session manager"""
        self.sessions_dir = Path.home() / ".looplm" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.active_session: Optional[ChatSession] = None

    def create_session(self, name: Optional[str] = None) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(name=name or "New Chat")
        self.active_session = session
        return session

    def save_session(self, session: ChatSession) -> bool:
        """
        Save a chat session to disk

        Args:
            session: ChatSession to save

        Returns:
            bool: True if save was successful
        """
        try:
            # Update session timestamp
            session.updated_at = datetime.now()

            # Convert session to JSON
            session_data = session.to_dict()

            # Save to file
            session_file = self.sessions_dir / f"{session.id}.json"
            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)

            # Also save an index file for quick listing
            self._update_session_index(session)

            return True

        except Exception as e:
            print(f"Error saving session: {str(e)}")
            return False

    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Load a chat session from disk

        Args:
            session_id: ID of session to load

        Returns:
            ChatSession if found, None otherwise
        """
        try:
            session_file = self.sessions_dir / f"{session_id}.json"
            if not session_file.exists():
                return None

            with open(session_file, "r") as f:
                session_data = json.load(f)

            session = ChatSession.from_dict(session_data)
            self.active_session = session
            return session

        except Exception as e:
            print(f"Error loading session: {str(e)}")
            return None

    def get_session_list(self) -> List[Dict]:
        """
        Get list of available sessions

        Returns:
            List of session metadata dicts with id, name, and timestamps
        """
        try:
            index_file = self.sessions_dir / "index.json"
            if not index_file.exists():
                return []

            with open(index_file, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _update_session_index(self, session: ChatSession):
        """Update the sessions index file"""
        index_file = self.sessions_dir / "index.json"

        try:
            # Load existing index
            if index_file.exists():
                with open(index_file, "r") as f:
                    sessions = json.load(f)
            else:
                sessions = []

            # Update session entry
            session_entry = {
                "id": session.id,
                "name": session.name,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": len(session.messages),
                "total_tokens": session.total_usage.total_tokens,
                "cost": session.total_usage.cost,
            }

            # Remove existing entry if present
            sessions = [s for s in sessions if s["id"] != session.id]
            sessions.append(session_entry)

            # Sort by updated_at
            sessions.sort(key=lambda x: x["updated_at"], reverse=True)

            # Save updated index
            with open(index_file, "w") as f:
                json.dump(sessions, f, indent=2)

        except Exception as e:
            print(f"Error updating session index: {str(e)}")

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a chat session

        Args:
            session_id: ID of session to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            # Remove session file
            session_file = self.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()

            # Update index
            index_file = self.sessions_dir / "index.json"
            if index_file.exists():
                with open(index_file, "r") as f:
                    sessions = json.load(f)

                sessions = [s for s in sessions if s["id"] != session_id]

                with open(index_file, "w") as f:
                    json.dump(sessions, f, indent=2)

            # Clear active session if it was deleted
            if self.active_session and self.active_session.id == session_id:
                self.active_session = None

            return True

        except Exception as e:
            print(f"Error deleting session: {str(e)}")
            return False

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_NAME = "chat_history.db"

def init_db():
    """Initializes the database with the necessary tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table for conversations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted BOOLEAN DEFAULT 0
        )
    ''')
    
    # Check if is_deleted column exists (for existing databases)
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [info[1] for info in cursor.fetchall()]
    if "is_deleted" not in columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
    
    # Table for messages
    # content can be text, and we'll store chart data as a JSON string if present
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            sender TEXT,
            content TEXT,
            chart_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_conversation(title: str = "Nova Conversa") -> int:
    """Creates a new conversation and returns its ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO conversations (title) VALUES (?)', (title,))
    conversation_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return conversation_id

def add_message(conversation_id: int, sender: str, content: str, chart_data: Optional[Dict[str, Any]] = None):
    """Adds a message to a conversation."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    chart_json = json.dumps(chart_data) if chart_data else None
    
    cursor.execute('''
        INSERT INTO messages (conversation_id, sender, content, chart_data)
        VALUES (?, ?, ?, ?)
    ''', (conversation_id, sender, content, chart_json))
    
    conn.commit()
    conn.close()

def get_conversations() -> List[Dict[str, Any]]:
    """Retrieves all active conversations ordered by creation date (descending)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM conversations WHERE is_deleted = 0 ORDER BY created_at DESC')
    rows = cursor.fetchall()
    
    conversations = []
    for row in rows:
        conversations.append(dict(row))
        
    conn.close()
    return conversations

def get_messages(conversation_id: int) -> List[Dict[str, Any]]:
    """Retrieves all messages for a specific conversation."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC', (conversation_id,))
    rows = cursor.fetchall()
    
    messages = []
    for row in rows:
        msg = dict(row)
        if msg['chart_data']:
            msg['chart_data'] = json.loads(msg['chart_data'])
        messages.append(msg)
        
    conn.close()
    return messages

def update_conversation_title(conversation_id: int, title: str):
    """Updates the title of a conversation."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE conversations SET title = ? WHERE id = ?', (title, conversation_id))
    conn.commit()
    conn.close()

def delete_conversation(conversation_id: int):
    """Soft deletes a conversation."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE conversations SET is_deleted = 1 WHERE id = ?', (conversation_id,))
    conn.commit()
    conn.close()

import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS audio_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL UNIQUE,
    duration REAL,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_audio TEXT NOT NULL,
    segment_audio TEXT NOT NULL,
    language TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_segments_source ON segments(source_audio);
CREATE INDEX IF NOT EXISTS idx_segments_start ON segments(start_time);

CREATE TABLE IF NOT EXISTS language_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audio_file_id INTEGER NOT NULL,
    legacy_segment_id INTEGER,
    language TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    text TEXT NOT NULL,
    report_path TEXT,
    segment_audio TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(audio_file_id) REFERENCES audio_files(id) ON DELETE CASCADE,
    FOREIGN KEY(legacy_segment_id) REFERENCES segments(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_lang_segments_audio ON language_segments(audio_file_id);
CREATE INDEX IF NOT EXISTS idx_lang_segments_language ON language_segments(language);
"""


def ensure_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    return conn


def get_or_create_audio_file(
    conn: sqlite3.Connection, source_path: str, duration: Optional[float]
) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM audio_files WHERE source_path = ?", (source_path,))
    row = cur.fetchone()
    if row:
        audio_file_id = row[0]
        if duration is not None:
            cur.execute(
                "UPDATE audio_files SET duration = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (duration, audio_file_id),
            )
            conn.commit()
        return audio_file_id

    cur.execute(
        "INSERT INTO audio_files (source_path, duration) VALUES (?, ?)",
        (source_path, duration),
    )
    conn.commit()
    return cur.lastrowid



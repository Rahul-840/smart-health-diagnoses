import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import bcrypt


class HealthDB:
    def __init__(self, db_name: str = "health_suite.db"):
        self.db_path = os.path.join(os.path.dirname(__file__), db_name)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self) -> None:
        self.cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                age INTEGER DEFAULT 0,
                blood_group TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                report_text TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS health_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                weight REAL DEFAULT 0,
                bp_systolic INTEGER DEFAULT 0,
                bp_diastolic INTEGER DEFAULT 0,
                blood_sugar REAL DEFAULT 0,
                heart_rate INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def register_user(self, username: str, email: str, password: str) -> Tuple[bool, Any]:
        username = (username or "").strip()
        email = (email or "").strip().lower()
        password = password or ""
        if len(username) < 3:
            return False, "Username must be at least 3 characters long."
        if "@" not in email or "." not in email:
            return False, "Please enter a valid email address."
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        try:
            pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            self.cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", (username, email, pw_hash))
            self.conn.commit()
            return True, "Registration successful. Please log in."
        except sqlite3.IntegrityError:
            return False, "Username or email already exists."
        except Exception as exc:
            return False, f"Registration failed: {exc}"

    def login_user(self, identifier: str, password: str) -> Tuple[bool, Any]:
        identifier = (identifier or "").strip()
        password = password or ""
        if not identifier or not password:
            return False, "Please enter username/email and password."
        self.cursor.execute("SELECT id, username, email, password_hash FROM users WHERE username=? OR email=?", (identifier, identifier.lower()))
        user = self.cursor.fetchone()
        if user:
            stored_hash = user[3].encode("utf-8") if isinstance(user[3], str) else user[3]
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
                return True, {"id": user[0], "username": user[1], "email": user[2]}
        return False, "Invalid credentials."

    def save_report(self, user_id: int, filename: str, report_text: str, analysis_json: Dict[str, Any]) -> int:
        self.cursor.execute(
            "INSERT INTO reports (user_id, filename, report_text, analysis_json) VALUES (?, ?, ?, ?)",
            (user_id, filename, report_text, json.dumps(analysis_json, ensure_ascii=False)),
        )
        self.conn.commit()
        return int(self.cursor.lastrowid)

    def get_user_reports(self, user_id: int) -> List[Tuple]:
        self.cursor.execute("SELECT id, filename, uploaded_at FROM reports WHERE user_id=? ORDER BY id DESC", (user_id,))
        return self.cursor.fetchall()

    def get_report_data(self, report_id: int, user_id: int) -> Optional[Tuple]:
        self.cursor.execute("SELECT * FROM reports WHERE id=? AND user_id=?", (report_id, user_id))
        return self.cursor.fetchone()

    def delete_report(self, report_id: int, user_id: int) -> None:
        self.cursor.execute("DELETE FROM chat_history WHERE report_id=? AND user_id=?", (report_id, user_id))
        self.cursor.execute("DELETE FROM reports WHERE id=? AND user_id=?", (report_id, user_id))
        self.conn.commit()

    def save_chat(self, user_id: int, report_id: int, role: str, content: str) -> None:
        self.cursor.execute(
            "INSERT INTO chat_history (user_id, report_id, role, content) VALUES (?, ?, ?, ?)",
            (user_id, report_id, role, content),
        )
        self.conn.commit()

    def get_chat(self, user_id: int, report_id: Optional[int] = None) -> List[Tuple]:
        if report_id is not None:
            self.cursor.execute(
                "SELECT role, content, timestamp FROM chat_history WHERE user_id=? AND report_id=? ORDER BY id ASC",
                (user_id, report_id),
            )
        else:
            self.cursor.execute("SELECT role, content, timestamp FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT 50", (user_id,))
        return self.cursor.fetchall()

    def clear_chat(self, user_id: int, report_id: int) -> None:
        self.cursor.execute("DELETE FROM chat_history WHERE user_id=? AND report_id=?", (user_id, report_id))
        self.conn.commit()

    def add_health_log(self, user_id: int, log_date: str, weight: float, bp_sys: int, bp_dia: int, sugar: float, hr: int, notes: str) -> None:
        self.cursor.execute(
            """INSERT INTO health_logs
               (user_id, log_date, weight, bp_systolic, bp_diastolic, blood_sugar, heart_rate, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, log_date, weight, bp_sys, bp_dia, sugar, hr, notes or ""),
        )
        self.conn.commit()

    def get_health_logs(self, user_id: int) -> List[Tuple]:
        self.cursor.execute(
            "SELECT log_date, weight, bp_systolic, bp_diastolic, blood_sugar, heart_rate FROM health_logs WHERE user_id=? ORDER BY log_date DESC",
            (user_id,),
        )
        return self.cursor.fetchall()

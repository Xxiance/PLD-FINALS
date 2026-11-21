import os
import sqlite3
import threading
from datetime import datetime
from json import dumps


class FixSQL:
    def __init__(self, file: str, machine: str):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, file)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self.machine = machine
        with self.lock:
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA busy_timeout=5000;")
            self.conn.commit()
        self.create_table()

    def create_table(self):
        with self.lock:
            self.conn.execute(f'''CREATE TABLE IF NOT EXISTS "{self.machine}"
             (ID     INTEGER PRIMARY KEY AUTOINCREMENT,
              CPU     JSON_DICT NOT NULL,
              RAM     JSON_DICT NOT NULL,
              DISK    JSON_DICT NOT NULL,
              NETWORK JSON_DICT NOT NULL,
              DEVICE  JSON_DICT NOT NULL,
              TIME    JSON_DICT NOT NULL);''')
            self.conn.commit()

    def new_machine_data(self, CPU: dict, RAM: dict, DISK: dict, NETWORK: dict, DEVICE: dict):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            self.conn.execute(
                f'INSERT OR IGNORE INTO "{self.machine}" (CPU, RAM, DISK, NETWORK, DEVICE, TIME) VALUES (?, ?, ?, ?, ?, ?)',
                (dumps(CPU), dumps(RAM), dumps(DISK), dumps(NETWORK), dumps(DEVICE), time)
            )
            self.conn.commit()

    def show_table(self):
        with self.lock:
            return self.conn.execute(f'SELECT * FROM "{self.machine}"').fetchall()

    def show_recent(self, limit: int = 300):
        with self.lock:
            rows = self.conn.execute(
                f'SELECT * FROM "{self.machine}" ORDER BY ID DESC LIMIT ?',
                (limit,)
            ).fetchall()
            return list(reversed(rows))

    def close_database(self):
        with self.lock:
            self.conn.close()
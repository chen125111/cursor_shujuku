import sqlite3

from backend.config import get_database_path

conn = sqlite3.connect(get_database_path())
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM pending_review WHERE status = 'pending'")
pending = cursor.fetchone()[0]
print(f'pending records: {pending}')

cursor.execute("SELECT COUNT(DISTINCT group_id) FROM pending_review WHERE status = 'pending'")
groups = cursor.fetchone()[0]
print(f'pending groups: {groups}')

cursor.execute("SELECT COUNT(*) FROM gas_mixture")
main = cursor.fetchone()[0]
print(f'main records: {main}')

conn.close()


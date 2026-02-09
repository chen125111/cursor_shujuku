import sqlite3

from backend.config import get_database_path

conn = sqlite3.connect(get_database_path())
cursor = conn.cursor()

# 查找同组分同温度下是否还有多个压力值
cursor.execute('''
    SELECT 
        x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10,
        temperature,
        COUNT(*) as count
    FROM gas_mixture
    GROUP BY x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10, temperature
    HAVING COUNT(*) > 1
''')

duplicates = cursor.fetchall()
print(f'Main table duplicate groups: {len(duplicates)}')

if duplicates:
    print('\nExamples of remaining duplicates:')
    for d in duplicates[:5]:
        print(f'  CH4={d[0]:.3f}, T={d[7]:.2f}K, count={d[8]}')
else:
    print('\nNo duplicates! Each (composition + temperature) has exactly 1 pressure value.')

# 统计总记录数
cursor.execute('SELECT COUNT(*) FROM gas_mixture')
total = cursor.fetchone()[0]
print(f'\nTotal records in main table: {total}')

conn.close()


"""
数据审核模块 - 处理同组分同温度下多压力值的数据
"""

from typing import List, Dict, Any

from backend.db import get_connection, is_mysql


def _ensure_index(cursor, table: str, index_name: str, columns: str) -> None:
    if is_mysql():
        cursor.execute(
            """
            SELECT COUNT(1) as count
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = ?
              AND index_name = ?
            """,
            (table, index_name),
        )
        row = cursor.fetchone()
        if not row or row["count"] == 0:
            cursor.execute(f"CREATE INDEX {index_name} ON {table}({columns})")
    else:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({columns})")


def _ensure_column(cursor, table: str, column: str, ddl: str) -> None:
    if is_mysql():
        cursor.execute(
            """
            SELECT COUNT(1) as count
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = ?
              AND column_name = ?
            """,
            (table, column),
        )
        row = cursor.fetchone()
        if not row or row["count"] == 0:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
    else:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = {row["name"] for row in cursor.fetchall()}
        if column not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_review_tables():
    """初始化审核相关的数据表"""
    id_column = "BIGINT PRIMARY KEY AUTO_INCREMENT" if is_mysql() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    group_id_type = "VARCHAR(32)" if is_mysql() else "TEXT"
    status_type = "VARCHAR(20)" if is_mysql() else "TEXT"
    reviewed_by_type = "VARCHAR(64)" if is_mysql() else "TEXT"
    approved_id_type = "BIGINT" if is_mysql() else "INTEGER"
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        # 待审核数据表
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS pending_review (
                id {id_column},
                group_id {group_id_type} NOT NULL,
                original_id INTEGER,
                temperature REAL NOT NULL,
                x_ch4 REAL DEFAULT 0,
                x_c2h6 REAL DEFAULT 0,
                x_c3h8 REAL DEFAULT 0,
                x_co2 REAL DEFAULT 0,
                x_n2 REAL DEFAULT 0,
                x_h2s REAL DEFAULT 0,
                x_ic4h10 REAL DEFAULT 0,
                pressure REAL NOT NULL,
                status {status_type} DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by {reviewed_by_type},
                approved_record_id {approved_id_type}
            )
        ''')

        _ensure_column(
            cursor,
            "pending_review",
            "approved_record_id",
            f"approved_record_id {approved_id_type}",
        )
        
        # 创建索引
        _ensure_index(cursor, "pending_review", "idx_pending_group", "group_id")
        _ensure_index(cursor, "pending_review", "idx_pending_status", "status")
        _ensure_index(cursor, "pending_review", "idx_pending_group_status", "group_id, status")
        
        conn.commit()
        print("[DataReview] 审核数据表初始化完成")


def find_duplicate_pressure_records() -> List[Dict]:
    """
    查找同组分、同温度下有多个不同压力值的记录
    返回按组分+温度分组的数据
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        # 查找重复的组分+温度组合
        cursor.execute('''
            SELECT 
                x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10,
                temperature,
                COUNT(*) as count,
                GROUP_CONCAT(id) as ids,
                GROUP_CONCAT(pressure) as pressures
            FROM gas_mixture
            GROUP BY x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10, temperature
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'composition': {
                    'x_ch4': row['x_ch4'],
                    'x_c2h6': row['x_c2h6'],
                    'x_c3h8': row['x_c3h8'],
                    'x_co2': row['x_co2'],
                    'x_n2': row['x_n2'],
                    'x_h2s': row['x_h2s'],
                    'x_ic4h10': row['x_ic4h10']
                },
                'temperature': row['temperature'],
                'count': row['count'],
                'ids': [int(x) for x in row['ids'].split(',')],
                'pressures': [float(x) for x in row['pressures'].split(',')]
            })
        
        return results


def move_duplicates_to_review() -> Dict:
    """
    将所有同组分同温度的重复压力数据移到待审核表
    """
    duplicates = find_duplicate_pressure_records()
    
    if not duplicates:
        return {'moved': 0, 'groups': 0}
    
    moved_count = 0
    group_count = 0
    
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()

        group_number = _get_next_group_number(cursor)

        for dup in duplicates:
            # 生成组ID
            group_id = f"G{group_number:04d}"
            
            # 获取这组数据的详细信息
            ids = [int(x) for x in dup["ids"]]
            if not ids:
                continue
            placeholders = ",".join("?" * len(ids))
            cursor.execute(
                f"SELECT * FROM gas_mixture WHERE id IN ({placeholders})",
                ids,
            )
            
            records = cursor.fetchall()
            
            for record in records:
                # 插入到待审核表
                cursor.execute('''
                    INSERT INTO pending_review 
                    (group_id, original_id, temperature, x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10, pressure)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    group_id,
                    record['id'],
                    record['temperature'],
                    record['x_ch4'],
                    record['x_c2h6'],
                    record['x_c3h8'],
                    record['x_co2'],
                    record['x_n2'],
                    record['x_h2s'],
                    record['x_ic4h10'],
                    record['pressure']
                ))
                moved_count += 1
            
            # 从原表删除
            cursor.execute(
                f"DELETE FROM gas_mixture WHERE id IN ({placeholders})",
                ids,
            )
            
            group_count += 1
            group_number += 1
        
        conn.commit()
    
    return {'moved': moved_count, 'groups': group_count}


def move_high_pressure_to_review(threshold: float = 50.0) -> Dict:
    """
    将压力高于阈值的数据移到待审核表
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, temperature, x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10, pressure
            FROM gas_mixture
            WHERE pressure > ?
        ''', (threshold,))

        records = cursor.fetchall()
        if not records:
            return {'moved': 0, 'groups': 0, 'threshold': threshold}

        grouped = {}
        for record in records:
            key = (
                record['temperature'],
                record['x_ch4'],
                record['x_c2h6'],
                record['x_c3h8'],
                record['x_co2'],
                record['x_n2'],
                record['x_h2s'],
                record['x_ic4h10']
            )
            grouped.setdefault(key, []).append(record)

        moved_count = 0
        group_count = 0
        group_number = _get_next_group_number(cursor)

        for _key, group_records in grouped.items():
            group_id = f"G{group_number:04d}"
            for record in group_records:
                cursor.execute('''
                    INSERT INTO pending_review
                    (group_id, original_id, temperature, x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10, pressure)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    group_id,
                    record['id'],
                    record['temperature'],
                    record['x_ch4'],
                    record['x_c2h6'],
                    record['x_c3h8'],
                    record['x_co2'],
                    record['x_n2'],
                    record['x_h2s'],
                    record['x_ic4h10'],
                    record['pressure']
                ))
                moved_count += 1

            group_count += 1
            group_number += 1

        ids = [record['id'] for record in records]
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f'DELETE FROM gas_mixture WHERE id IN ({placeholders})', ids)
        conn.commit()

    return {'moved': moved_count, 'groups': group_count, 'threshold': threshold}


def _get_next_group_number(cursor) -> int:
    cursor.execute('SELECT group_id FROM pending_review')
    max_num = 0
    for row in cursor.fetchall():
        group_id = row['group_id']
        if isinstance(group_id, str) and group_id.startswith('G'):
            suffix = group_id[1:]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return max_num + 1


def get_pending_groups(
    page: int = 1,
    per_page: int = 50,
    group_id: Any = None,
    temp_min: Any = None,
    temp_max: Any = None,
) -> Dict:
    """获取待审核的数据组（分页）"""
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()

        page = max(1, page)
        per_page = max(1, min(per_page, 200))
        offset = (page - 1) * per_page

        filters = ["status = 'pending'"]
        params = []
        if group_id:
            filters.append("group_id LIKE ?")
            params.append(f"%{group_id}%")
        if temp_min is not None:
            filters.append("temperature >= ?")
            params.append(temp_min)
        if temp_max is not None:
            filters.append("temperature <= ?")
            params.append(temp_max)
        where_clause = " AND ".join(filters)

        cursor.execute(
            f'''
            SELECT COUNT(DISTINCT group_id) as total
            FROM pending_review
            WHERE {where_clause}
            ''',
            params,
        )
        total_row = cursor.fetchone()
        total = total_row['total'] if total_row else 0

        # 获取待审核的组
        cursor.execute(
            f'''
            SELECT group_id,
                temperature,
                x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10,
                COUNT(*) as pressure_count
            FROM pending_review
            WHERE {where_clause}
            GROUP BY group_id, temperature, x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10
            ORDER BY group_id
            LIMIT ? OFFSET ?
            ''',
            params + [per_page, offset],
        )
        
        groups = []
        for row in cursor.fetchall():
            group_id = row['group_id']
            
            # 获取这组的所有压力值
            cursor.execute('''
                SELECT id, pressure, original_id FROM pending_review 
                WHERE group_id = ? AND status = 'pending'
                ORDER BY pressure
            ''', (group_id,))
            
            pressures = [{'id': r['id'], 'pressure': r['pressure'], 'original_id': r['original_id']} 
                        for r in cursor.fetchall()]
            
            groups.append({
                'group_id': group_id,
                'temperature': row['temperature'],
                'composition': {
                    'x_ch4': row['x_ch4'],
                    'x_c2h6': row['x_c2h6'],
                    'x_c3h8': row['x_c3h8'],
                    'x_co2': row['x_co2'],
                    'x_n2': row['x_n2'],
                    'x_h2s': row['x_h2s'],
                    'x_ic4h10': row['x_ic4h10']
                },
                'pressures': pressures,
                'pressure_count': row['pressure_count']
            })

        return {
            'groups': groups,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1
        }


def get_pending_stats() -> Dict:
    """获取待审核数据统计"""
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(DISTINCT group_id) as group_count FROM pending_review WHERE status = 'pending'")
        groups = cursor.fetchone()['group_count']
        
        cursor.execute("SELECT COUNT(*) as records FROM pending_review WHERE status = 'pending'")
        records = cursor.fetchone()['records']
        
        cursor.execute("SELECT COUNT(*) as approved FROM pending_review WHERE status = 'approved'")
        approved = cursor.fetchone()['approved']
        
        cursor.execute("SELECT COUNT(*) as rejected FROM pending_review WHERE status = 'rejected'")
        rejected = cursor.fetchone()['rejected']
        
        return {
            'pending_groups': groups,
            'pending_records': records,
            'approved': approved,
            'rejected': rejected
        }


def update_pending_pressure(pending_id: int, new_pressure: float) -> bool:
    """更新待审核记录的压力值"""
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE pending_review SET pressure = ? WHERE id = ?', (new_pressure, pending_id))
        conn.commit()
        return cursor.rowcount > 0


def approve_group(group_id: str, selected_pressures: List[int], username: str = None) -> Dict:
    """
    审核通过一组数据
    selected_pressures: 选择保留的压力记录ID列表
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        # 获取选中的记录
        ids = [int(x) for x in selected_pressures if x is not None]
        if not ids:
            return {"approved": 0, "group_id": group_id}
        placeholders = ",".join("?" * len(ids))
        cursor.execute(
            f"SELECT * FROM pending_review WHERE id IN ({placeholders}) AND group_id = ?",
            ids + [group_id],
        )

        records = cursor.fetchall()
        approved_count = 0
        
        for record in records:
            # 插入到正式数据表
            cursor.execute('''
                INSERT INTO gas_mixture 
                (temperature, x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10, pressure)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record['temperature'],
                record['x_ch4'],
                record['x_c2h6'],
                record['x_c3h8'],
                record['x_co2'],
                record['x_n2'],
                record['x_h2s'],
                record['x_ic4h10'],
                record['pressure']
            ))
            approved_id = cursor.lastrowid
            cursor.execute('''
                UPDATE pending_review
                SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?, approved_record_id = ?
                WHERE id = ?
            ''', (username, approved_id, record['id']))
            approved_count += 1
        
        # 其余记录标记为已拒绝
        cursor.execute('''
            UPDATE pending_review 
            SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
            WHERE group_id = ? AND status = 'pending'
        ''', (username, group_id))
        
        conn.commit()
        
        return {'approved': approved_count, 'group_id': group_id}


def reject_group(group_id: str, username: str = None) -> bool:
    """拒绝整组数据"""
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pending_review 
            SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
            WHERE group_id = ? AND status = 'pending'
        ''', (username, group_id))
        conn.commit()
        return cursor.rowcount > 0


def restore_group(group_id: str) -> Dict:
    """恢复一组数据到待审核状态"""
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT approved_record_id FROM pending_review 
            WHERE group_id = ? AND status = 'approved' AND approved_record_id IS NOT NULL
        ''', (group_id,))
        approved_ids = [row['approved_record_id'] for row in cursor.fetchall() if row['approved_record_id']]
        if approved_ids:
            placeholders = ','.join('?' * len(approved_ids))
            cursor.execute(f'DELETE FROM gas_mixture WHERE id IN ({placeholders})', approved_ids)
        
        # 重置状态
        cursor.execute('''
            UPDATE pending_review 
            SET status = 'pending', reviewed_at = NULL, reviewed_by = NULL, approved_record_id = NULL
            WHERE group_id = ?
        ''', (group_id,))
        
        conn.commit()
        return {'restored': cursor.rowcount}


# 初始化
init_review_tables()

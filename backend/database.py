"""
数据库操作模块
提供气体混合物数据表（gas_mixture）的读写与查询能力。

说明：
- 默认使用 SQLite（文件数据库），也支持通过环境变量切换到 MySQL（详见 `backend/db.py`）
- 本模块函数尽量保持“纯数据访问层”职责：不做认证、不处理 HTTP 细节
"""

from typing import List, Dict, Optional, Any

from backend.db import get_connection, is_mysql


def _ensure_index(cursor, table: str, index_name: str, columns: str) -> None:
    """
    确保索引存在（SQLite 使用 IF NOT EXISTS；MySQL 通过 information_schema 判断）。

    Args:
        cursor: 数据库游标（需要支持 `execute` / `fetchone`）
        table: 表名
        index_name: 索引名
        columns: 索引列定义字符串（例如 `"temperature, pressure"`）
    """
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


def init_database():
    """
    初始化业务数据库，创建 `gas_mixture` 数据表与必要索引。

    Returns:
        None

    Notes:
        - 本函数在模块导入时会被调用一次（见文件末尾），用于确保表结构存在。
        - 若使用 MySQL，会根据不同方言调整主键列定义。
    """
    id_column = "BIGINT PRIMARY KEY AUTO_INCREMENT" if is_mysql() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS gas_mixture (
                id {id_column},
                temperature REAL NOT NULL,
                x_ch4 REAL DEFAULT 0,
                x_c2h6 REAL DEFAULT 0,
                x_c3h8 REAL DEFAULT 0,
                x_co2 REAL DEFAULT 0,
                x_n2 REAL DEFAULT 0,
                x_h2s REAL DEFAULT 0,
                x_ic4h10 REAL DEFAULT 0,
                pressure REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        _ensure_index(cursor, "gas_mixture", "idx_gas_temperature", "temperature")
        _ensure_index(cursor, "gas_mixture", "idx_gas_pressure", "pressure")
        _ensure_index(cursor, "gas_mixture", "idx_gas_temp_pressure", "temperature, pressure")
        _ensure_index(cursor, "gas_mixture", "idx_gas_x_ch4", "x_ch4")
        _ensure_index(cursor, "gas_mixture", "idx_gas_x_c2h6", "x_c2h6")
        _ensure_index(cursor, "gas_mixture", "idx_gas_x_c3h8", "x_c3h8")
        _ensure_index(cursor, "gas_mixture", "idx_gas_x_co2", "x_co2")
        _ensure_index(cursor, "gas_mixture", "idx_gas_x_n2", "x_n2")
        _ensure_index(cursor, "gas_mixture", "idx_gas_x_h2s", "x_h2s")
        _ensure_index(cursor, "gas_mixture", "idx_gas_x_ic4h10", "x_ic4h10")
        conn.commit()


# ==================== 增 (Create) ====================
def create_record(data: Dict[str, Any]) -> int:
    """
    创建一条气体混合物记录。

    Args:
        data: 记录字段字典。常用字段包括：
            - temperature: 温度（K）
            - pressure: 压力（MPa）
            - x_ch4/x_c2h6/x_c3h8/x_co2/x_n2/x_h2s/x_ic4h10: 各组分摩尔分数

    Returns:
        新插入记录的自增 ID。
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO gas_mixture 
            (temperature, x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10, pressure)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('temperature', 0),
            data.get('x_ch4', 0),
            data.get('x_c2h6', 0),
            data.get('x_c3h8', 0),
            data.get('x_co2', 0),
            data.get('x_n2', 0),
            data.get('x_h2s', 0),
            data.get('x_ic4h10', 0),
            data.get('pressure', 0)
        ))
        conn.commit()
        return cursor.lastrowid


# ==================== 删 (Delete) ====================
def delete_record(record_id: int) -> bool:
    """
    删除指定 ID 的记录。

    Args:
        record_id: 记录 ID

    Returns:
        是否删除成功（当记录存在且被删除时返回 True）。
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM gas_mixture WHERE id = ?', (record_id,))
        conn.commit()
        return cursor.rowcount > 0


# ==================== 改 (Update) ====================
def update_record(record_id: int, data: Dict[str, Any]) -> bool:
    """
    更新指定 ID 的记录（仅更新传入且非 None 的字段）。

    Args:
        record_id: 记录 ID
        data: 待更新字段字典（仅允许更新白名单字段）。

    Returns:
        是否更新成功（当记录存在且至少一个字段被更新时返回 True）。
    """
    fields = []
    values = []
    
    field_mapping = {
        'temperature': 'temperature',
        'x_ch4': 'x_ch4',
        'x_c2h6': 'x_c2h6',
        'x_c3h8': 'x_c3h8',
        'x_co2': 'x_co2',
        'x_n2': 'x_n2',
        'x_h2s': 'x_h2s',
        'x_ic4h10': 'x_ic4h10',
        'pressure': 'pressure'
    }
    
    for key, db_field in field_mapping.items():
        if key in data and data[key] is not None:
            fields.append(f"{db_field} = ?")
            values.append(data[key])
    
    if not fields:
        return False
    
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(record_id)
    
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        query = f"UPDATE gas_mixture SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0


# ==================== 查 (Read) ====================
def get_record_by_id(record_id: int) -> Optional[Dict]:
    """
    根据 ID 获取单条记录。

    Args:
        record_id: 记录 ID

    Returns:
        记录字典；若不存在返回 None。
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM gas_mixture WHERE id = ?', (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_records(
    page: int = 1, 
    per_page: int = 15,
    temp_min: Optional[float] = None,
    temp_max: Optional[float] = None,
    pressure_min: Optional[float] = None,
    pressure_max: Optional[float] = None
) -> Dict:
    """
    获取记录列表（分页 + 温度/压力范围筛选）。

    Args:
        page: 页码（从 1 开始）
        per_page: 每页数量
        temp_min: 温度下限（K）
        temp_max: 温度上限（K）
        pressure_min: 压力下限（MPa）
        pressure_max: 压力上限（MPa）

    Returns:
        分页结果字典，包含：
        - records: 当前页记录列表
        - total: 总记录数
        - page/per_page/total_pages: 分页信息
    """
    conditions = []
    values = []
    
    if temp_min is not None:
        conditions.append("temperature >= ?")
        values.append(temp_min)
    if temp_max is not None:
        conditions.append("temperature <= ?")
        values.append(temp_max)
    if pressure_min is not None:
        conditions.append("pressure >= ?")
        values.append(pressure_min)
    if pressure_max is not None:
        conditions.append("pressure <= ?")
        values.append(pressure_max)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    offset = (page - 1) * per_page
    
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        # 获取总数
        cursor.execute(f'SELECT COUNT(*) as count FROM gas_mixture WHERE {where_clause}', values)
        total = cursor.fetchone()['count']
        
        # 获取分页数据
        cursor.execute(f'''
            SELECT * FROM gas_mixture 
            WHERE {where_clause}
            ORDER BY id ASC 
            LIMIT ? OFFSET ?
        ''', values + [per_page, offset])
        
        records = [dict(row) for row in cursor.fetchall()]
        
        return {
            'records': records,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1
        }


def get_statistics() -> Dict:
    """
    获取数据统计信息（记录数、温度/压力 min/max/avg）。

    Returns:
        统计信息字典；当表为空时返回空字典。
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_records,
                MIN(temperature) as min_temperature,
                MAX(temperature) as max_temperature,
                AVG(temperature) as avg_temperature,
                MIN(pressure) as min_pressure,
                MAX(pressure) as max_pressure,
                AVG(pressure) as avg_pressure
            FROM gas_mixture
        ''')
        row = cursor.fetchone()
        return dict(row) if row else {}


def get_all_records_no_pagination() -> List[Dict]:
    """
    获取全部记录（不分页，用于导出）。

    Returns:
        全量记录列表（按 id 升序）。
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM gas_mixture ORDER BY id ASC')
        return [dict(row) for row in cursor.fetchall()]


def batch_create_records(records: List[Dict[str, Any]]) -> int:
    """
    批量插入记录（用于导入场景）。

    Args:
        records: 记录字典列表（字段含义同 `create_record`）

    Returns:
        实际插入的行数（由数据库驱动返回，通常等于 records 长度）。
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO gas_mixture 
            (temperature, x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10, pressure)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            (
                r.get('temperature', 0),
                r.get('x_ch4', 0),
                r.get('x_c2h6', 0),
                r.get('x_c3h8', 0),
                r.get('x_co2', 0),
                r.get('x_n2', 0),
                r.get('x_h2s', 0),
                r.get('x_ic4h10', 0),
                r.get('pressure', 0)
            ) for r in records
        ])
        conn.commit()
        return cursor.rowcount


def get_chart_data(chart_type: str) -> Dict:
    """
    生成前端图表所需的聚合数据。

    Args:
        chart_type: 图表类型，支持：
            - temperature: 温度分布（分桶直方图）
            - pressure: 压力分布（区间统计）
            - scatter: 温度-压力散点（抽样）

    Returns:
        图表数据字典（结构会随 chart_type 不同而不同）。
    """
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        if chart_type == 'temperature':
            # 温度分布直方图数据
            temp_bucket = "FLOOR(temperature / 20)" if is_mysql() else "CAST((temperature / 20) AS INTEGER)"
            cursor.execute(f'''
                SELECT 
                    {temp_bucket} * 20 as temp_range,
                    COUNT(*) as count
                FROM gas_mixture
                GROUP BY temp_range
                ORDER BY temp_range
            ''')
            rows = cursor.fetchall()
            return {
                'labels': [f"{int(r['temp_range'])}-{int(r['temp_range'])+20}K" for r in rows],
                'data': [r['count'] for r in rows],
                'title': '温度分布'
            }
            
        elif chart_type == 'pressure':
            # 压力分布直方图数据
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN pressure < 1 THEN '0-1'
                        WHEN pressure < 5 THEN '1-5'
                        WHEN pressure < 10 THEN '5-10'
                        WHEN pressure < 50 THEN '10-50'
                        WHEN pressure < 100 THEN '50-100'
                        ELSE '100+'
                    END as pressure_range,
                    COUNT(*) as count
                FROM gas_mixture
                GROUP BY pressure_range
                ORDER BY 
                    CASE pressure_range
                        WHEN '0-1' THEN 1
                        WHEN '1-5' THEN 2
                        WHEN '5-10' THEN 3
                        WHEN '10-50' THEN 4
                        WHEN '50-100' THEN 5
                        ELSE 6
                    END
            ''')
            rows = cursor.fetchall()
            return {
                'labels': [f"{r['pressure_range']} MPa" for r in rows],
                'data': [r['count'] for r in rows],
                'title': '压力分布'
            }
            
        elif chart_type == 'scatter':
            # 温度-压力散点图数据（采样）
            random_func = "RAND()" if is_mysql() else "RANDOM()"
            cursor.execute(f'''
                SELECT temperature, pressure
                FROM gas_mixture
                ORDER BY {random_func}
                LIMIT 200
            ''')
            rows = cursor.fetchall()
            return {
                'data': [{'x': r['temperature'], 'y': r['pressure']} for r in rows],
                'title': '温度-压力分布'
            }
        
        return {}


# ==================== 组分查询 ====================

def query_by_composition(composition: Dict[str, float], tolerance: float = 0.05, strict_mode: bool = True) -> List[Dict]:
    """
    根据气体组分查询匹配的温度和压力

    Args:
        composition: 组分字典，如 `{'x_ch4': 0.9, 'x_c2h6': 0.05}`
        tolerance: 允许的误差范围（默认 0.05）
        strict_mode: 严格模式：未输入的组分要求接近 0（<= tolerance）

    Returns:
        匹配到的记录列表（最多 100 条），按温度/压力排序。
    """
    all_components = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
    
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        for field in all_components:
            if field in composition and composition[field] is not None:
                # 用户输入的组分：在误差范围内匹配
                value = composition[field]
                min_val = value - tolerance
                max_val = value + tolerance
                conditions.append(f"({field} >= ? AND {field} <= ?)")
                params.extend([min_val, max_val])
            elif strict_mode:
                # 严格模式：未输入的组分要求接近0（小于容差）
                conditions.append(f"({field} <= ?)")
                params.append(tolerance)
        
        if not conditions:
            return []
        
        where_clause = " AND ".join(conditions)
        
        sql = f'''
            SELECT id, temperature, pressure, x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10
            FROM gas_mixture
            WHERE {where_clause}
            ORDER BY temperature ASC, pressure ASC
            LIMIT 100
        '''
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]


# ==================== 批量操作 ====================

def batch_delete_records(ids: List[int]) -> int:
    """
    批量删除记录（管理员操作常用）。

    Args:
        ids: 记录 ID 列表

    Returns:
        实际删除的记录数。
    """
    if not ids:
        return 0
    
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f'DELETE FROM gas_mixture WHERE id IN ({placeholders})', ids)
        conn.commit()
        return cursor.rowcount


def batch_update_records(ids: List[int], updates: Dict[str, Any]) -> int:
    """
    批量更新记录（管理员操作常用）。

    Args:
        ids: 记录 ID 列表
        updates: 更新字段字典（仅允许更新白名单字段；None 值会被忽略）

    Returns:
        实际更新的记录数。
    """
    if not ids or not updates:
        return 0
    
    # 过滤有效字段
    valid_fields = ['temperature', 'x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10', 'pressure']
    filtered_updates = {k: v for k, v in updates.items() if k in valid_fields and v is not None}
    
    if not filtered_updates:
        return 0
    
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        # 构建 UPDATE 语句
        set_clause = ', '.join([f'{k} = ?' for k in filtered_updates.keys()])
        placeholders = ','.join('?' * len(ids))
        
        sql = f'''
            UPDATE gas_mixture 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        '''
        
        params = list(filtered_updates.values()) + ids
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount


# 初始化数据库
init_database()


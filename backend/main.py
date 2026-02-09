"""
FastAPI 后端服务
提供 RESTful API 接口
版本 4.0 - 增强安全性、数据管理功能
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, Response
from typing import Optional, List
from pydantic import BaseModel
import os
import io
import csv
import tempfile
import json

from backend.models import (
    GasRecordCreate, GasRecordUpdate, GasRecord,
    PaginatedResponse, Statistics, ApiResponse
)
from backend.database import (
    create_record, delete_record, update_record,
    get_record_by_id, get_all_records, get_statistics,
    get_chart_data, batch_create_records, get_all_records_no_pagination,
    batch_delete_records, batch_update_records
)
from backend.auth import (
    authenticate_user, create_access_token, get_current_user,
    hash_password, verify_password, create_user, change_password, list_users,
    get_admin_username, is_admin_configured, is_using_default_secret_key,
    ensure_admin_user, reset_user_password
)
from backend.backup import (
    create_backup, restore_backup, list_backups, delete_backup,
    get_backup_status, init_backup_system, is_backup_supported
)
from backend.security import (
    init_security, check_rate_limit, detect_crawler, add_crawler_block,
    record_login, check_login_attempts, record_login_attempt,
    get_login_logs, create_session, validate_session, revoke_session,
    get_user_sessions, revoke_all_user_sessions, validate_password,
    get_password_policy, record_audit_log, get_audit_logs,
    record_data_history, get_data_history, get_rate_limit_status
)
from backend.data_review import (
    find_duplicate_pressure_records, move_duplicates_to_review,
    get_pending_groups, get_pending_stats, update_pending_pressure,
    approve_group, reject_group, restore_group
)
from backend.totp import (
    setup_totp, enable_totp, disable_totp, is_totp_enabled,
    verify_user_totp, get_totp_status, regenerate_backup_codes
)
from backend.data_validation import (
    validate_record, validate_batch, clean_record, clean_batch,
    validate_partial_record,
    get_validation_rules, get_field_constraints, get_soft_warnings,
    count_soft_warnings, PRESSURE_SOFT_MAX
)
from backend.config import get_backup_dir, get_cors_origins
from backend.db import get_connection
from backend.cache import cached, get_cache, init_cache

# ==================== 认证依赖 ====================

def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    从请求头 `Authorization` 中解析 Bearer Token。

    Args:
        authorization: FastAPI 注入的请求头值（形如 `"Bearer <token>"`）

    Returns:
        解析得到的 token 字符串；若头部缺失或格式不匹配返回 None。
    """
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def require_auth(authorization: Optional[str] = Header(None)):
    """
    FastAPI 认证依赖项（用于需要登录的接口）。

    Args:
        authorization: `Authorization` 请求头

    Returns:
        当前用户信息字典（至少包含 username/role）。

    Raises:
        HTTPException: 未提供 token / token 无效或过期时抛出 401。
    """
    token = get_token_from_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

    return user

# ==================== Pydantic 模型 ====================

class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

class ResetUserPasswordRequest(BaseModel):
    new_password: str

class BatchDeleteRequest(BaseModel):
    ids: List[int]

class BatchUpdateRequest(BaseModel):
    ids: List[int]
    updates: dict

class TOTPSetupRequest(BaseModel):
    code: str

# 创建 FastAPI 应用
app = FastAPI(
    title="气体混合物数据管理系统 API",
    description="提供气体混合物热力学数据的增删改查功能，含安全增强",
    version="4.0.0"
)

# 软提示（不阻止写入）
def format_soft_warning(warnings: List[str]) -> str:
    """
    将软提示列表格式化为可拼接到 message 的字符串。

    Args:
        warnings: 软提示文本列表

    Returns:
        格式化后的字符串；当无提示时返回空字符串。
    """
    if not warnings:
        return ""
    return f"（注意：{'; '.join(warnings)}）"


def format_soft_warning_count(count: int) -> str:
    """
    将“软提示数量”格式化为可拼接到 message 的字符串。

    Args:
        count: 软提示条数

    Returns:
        格式化后的字符串；当 count<=0 时返回空字符串。
    """
    if count <= 0:
        return ""
    return f"（注意：{count} 条记录压力高于 {PRESSURE_SOFT_MAX:.0f} MPa，可能为异常值）"

# 配置跨域 (CORS) - 允许前端访问
cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=bool(cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 安全中间件 ====================

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """安全中间件 - API限流 + 防爬虫"""
    # 获取客户端信息
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    path = request.url.path
    
    # 白名单路径（不限流）
    whitelist_paths = ["/", "/admin", "/docs", "/openapi.json", "/css/", "/js/"]
    is_whitelisted = any(path.startswith(p) for p in whitelist_paths)
    
    if not is_whitelisted and path.startswith("/api/"):
        # 检查API限流
        allowed, error_msg = check_rate_limit(client_ip)
        if not allowed:
            return Response(
                content=json.dumps({"detail": error_msg, "error_code": "RATE_LIMITED"}),
                status_code=429,
                media_type="application/json"
            )
        
        # 检查爬虫
        is_crawler, crawler_reason = detect_crawler(user_agent, path, client_ip)
        if is_crawler:
            add_crawler_block(client_ip, crawler_reason)
            return Response(
                content=json.dumps({"detail": "访问被拒绝", "error_code": "BLOCKED"}),
                status_code=403,
                media_type="application/json"
            )
    
    response = await call_next(request)
    
    # 添加安全响应头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Cache-Control"] = "no-store"
    
    return response

# 前端静态文件目录 - 基于当前文件位置计算
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
FRONTEND_CSS = os.path.join(FRONTEND_DIR, "css")
FRONTEND_JS = os.path.join(FRONTEND_DIR, "js")
FRONTEND_INDEX = os.path.join(FRONTEND_DIR, "index.html")


# ==================== API 路由 ====================

@app.get("/api/records", response_model=PaginatedResponse, tags=["Records"])
async def api_get_records(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(15, ge=1, le=100, description="每页数量"),
    temp_min: Optional[float] = Query(None, description="最低温度"),
    temp_max: Optional[float] = Query(None, description="最高温度"),
    pressure_min: Optional[float] = Query(None, description="最低压力"),
    pressure_max: Optional[float] = Query(None, description="最高压力")
):
    """获取记录列表（支持分页和筛选）"""
    result = get_all_records(
        page=page,
        per_page=per_page,
        temp_min=temp_min,
        temp_max=temp_max,
        pressure_min=pressure_min,
        pressure_max=pressure_max
    )
    return result


@app.get("/api/records/{record_id}", response_model=GasRecord, tags=["Records"])
async def api_get_record(record_id: int):
    """获取单条记录"""
    record = get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@app.post("/api/records", response_model=ApiResponse, tags=["Records"])
async def api_create_record(data: GasRecordCreate, user: dict = Depends(require_auth)):
    """创建新记录"""
    if user["role"] not in ("admin", "user"):
        raise HTTPException(status_code=403, detail="权限不足")
    try:
        record_payload = clean_record(data.model_dump())
        is_valid, errors = validate_record(record_payload)
        if not is_valid:
            raise HTTPException(status_code=400, detail="; ".join(errors))
        warnings = get_soft_warnings(record_payload)
        record_id = create_record(record_payload)
        return ApiResponse(
            success=True,
            message="创建成功" + format_soft_warning(warnings),
            data={"id": record_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/records/{record_id}", response_model=ApiResponse, tags=["Records"])
async def api_update_record(record_id: int, data: GasRecordUpdate, user: dict = Depends(require_auth)):
    """更新记录"""
    if user["role"] not in ("admin", "user"):
        raise HTTPException(status_code=403, detail="权限不足")
    # 过滤掉 None 值
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="没有要更新的数据")

    existing = get_record_by_id(record_id)
    if not existing:
        raise HTTPException(status_code=404, detail="记录不存在")
    merged = {**existing, **update_data}
    merged_payload = clean_record(merged)
    is_valid, errors = validate_record(merged_payload)
    if not is_valid:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    success = update_record(record_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    warnings = get_soft_warnings(update_data) if "pressure" in update_data else []
    return ApiResponse(success=True, message="更新成功" + format_soft_warning(warnings))


@app.delete("/api/records/{record_id}", response_model=ApiResponse, tags=["Records"])
async def api_delete_record(record_id: int, user: dict = Depends(require_auth)):
    """删除记录"""
    if user["role"] not in ("admin", "user"):
        raise HTTPException(status_code=403, detail="权限不足")
    success = delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    return ApiResponse(success=True, message="删除成功")


@app.get("/api/statistics", response_model=Statistics, tags=["Statistics"])
@cached(ttl=60)  # 缓存60秒
async def api_statistics():
    """获取统计信息"""
    stats = get_statistics()
    return stats


# ==================== 图表数据API ====================

@app.get("/api/charts/temperature", tags=["Charts"])
@cached(ttl=300)  # 缓存5分钟
async def api_chart_temperature():
    """获取温度分布图表数据"""
    from backend.database import get_chart_data
    chart_data = get_chart_data('temperature')
    return chart_data


@app.get("/api/charts/pressure", tags=["Charts"])
@cached(ttl=300)  # 缓存5分钟
async def api_chart_pressure():
    """获取压力分布图表数据"""
    from backend.database import get_chart_data
    chart_data = get_chart_data('pressure')
    return chart_data


@app.get("/api/charts/scatter", tags=["Charts"])
@cached(ttl=300)  # 缓存5分钟
async def api_chart_scatter():
    """获取温度-压力散点图数据"""
    from backend.database import get_chart_data
    chart_data = get_chart_data('scatter')
    return chart_data


@app.get("/api/charts/composition", tags=["Charts"])
@cached(ttl=300)  # 缓存5分钟
async def api_chart_composition():
    """获取组分比例图表数据"""
    from backend.db import get_connection
    
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        
        # 计算各组分平均值
        cursor.execute('''
            SELECT 
                AVG(x_ch4) as avg_ch4,
                AVG(x_c2h6) as avg_c2h6,
                AVG(x_c3h8) as avg_c3h8,
                AVG(x_co2) as avg_co2,
                AVG(x_n2) as avg_n2,
                AVG(x_h2s) as avg_h2s,
                AVG(x_ic4h10) as avg_ic4h10
            FROM gas_mixture
        ''')
        
        row = cursor.fetchone()
        if not row:
            return {"labels": [], "data": []}
        
        # 转换为百分比
        labels = ['CH₄', 'C₂H₆', 'C₃H₈', 'CO₂', 'N₂', 'H₂S', 'i-C₄H₁₀']
        data = [
            row['avg_ch4'] * 100,
            row['avg_c2h6'] * 100,
            row['avg_c3h8'] * 100,
            row['avg_co2'] * 100,
            row['avg_n2'] * 100,
            row['avg_h2s'] * 100,
            row['avg_ic4h10'] * 100
        ]
        
        return {
            "labels": labels,
            "data": data,
            "title": "平均组分比例"
        }


@app.get("/api/charts/cache/stats", tags=["Charts", "Cache"])
async def api_cache_stats():
    """获取缓存统计信息"""
    cache = get_cache()
    if cache and cache.is_connected():
        stats = cache.get_stats()
        return {
            "success": True,
            "data": stats
        }
    return {
        "success": False,
        "message": "缓存未连接",
        "data": {"connected": False}
    }


@app.post("/api/charts/cache/clear", tags=["Charts", "Cache"])
async def api_clear_cache(user: dict = Depends(require_auth)):
    """清除图表缓存"""
    if user["role"] not in ("admin", "user"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    cache = get_cache()
    if cache and cache.is_connected():
        cleared = cache.clear_pattern("cache:*")
        return {
            "success": True,
            "message": f"已清除 {cleared} 个缓存项"
        }
    return {
        "success": False,
        "message": "缓存未连接"
    }


# ==================== 查询API ====================

@app.get("/api/query", tags=["Query"])
async def api_query_by_composition(
    x_ch4: Optional[float] = Query(None, description="CH4 摩尔分数"),
    x_c2h6: Optional[float] = Query(None, description="C2H6 摩尔分数"),
    x_c3h8: Optional[float] = Query(None, description="C3H8 摩尔分数"),
    x_co2: Optional[float] = Query(None, description="CO2 摩尔分数"),
    x_n2: Optional[float] = Query(None, description="N2 摩尔分数"),
    x_h2s: Optional[float] = Query(None, description="H2S 摩尔分数"),
    x_ic4h10: Optional[float] = Query(None, description="i-C4H10 摩尔分数"),
    tolerance: float = Query(0.02, description="允许的误差范围，默认2%"),
    strict: bool = Query(True, description="严格模式：未输入的组分要求接近0")
):
    """根据气体组分查询温度和压力"""
    from backend.database import query_by_composition
    
    composition = {
        'x_ch4': x_ch4,
        'x_c2h6': x_c2h6,
        'x_c3h8': x_c3h8,
        'x_co2': x_co2,
        'x_n2': x_n2,
        'x_h2s': x_h2s,
        'x_ic4h10': x_ic4h10
    }
    
    # 过滤掉 None 值
    composition = {k: v for k, v in composition.items() if v is not None}
    
    if not composition:
        return {"success": False, "message": "请至少输入一个组分", "data": []}
    
    results = query_by_composition(composition, tolerance, strict_mode=strict)
    return {"success": True, "data": results, "count": len(results)}


# ==================== 图表数据 API ====================

@app.get("/api/chart/temperature", tags=["Chart"])
async def api_chart_temperature():
    """获取温度分布数据（用于图表）"""
    data = get_chart_data('temperature')
    return data


@app.get("/api/chart/pressure", tags=["Chart"])
async def api_chart_pressure():
    """获取压力分布数据（用于图表）"""
    data = get_chart_data('pressure')
    return data


@app.get("/api/chart/scatter", tags=["Chart"])
async def api_chart_scatter():
    """获取温度-压力散点图数据"""
    data = get_chart_data('scatter')
    return data


@app.get("/api/chart/heatmap", tags=["Chart"])
async def api_chart_heatmap(
    temp_bins: int = Query(18, ge=5, le=60),
    pressure_bins: int = Query(20, ge=5, le=60)
):
    """获取温度-压力密度热力图数据"""
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT temperature, pressure FROM gas_mixture")
        rows = cursor.fetchall()

    if not rows:
        return {"x_labels": [], "y_labels": [], "data": [], "meta": {}}

    temps = [row['temperature'] for row in rows]
    pressures = [row['pressure'] for row in rows]

    min_temp = min(temps)
    max_temp = max(temps)
    min_pressure = min(pressures)
    max_pressure = max(pressures)

    temp_range = max_temp - min_temp
    pressure_range = max_pressure - min_pressure

    if temp_range == 0:
        temp_bins = 1
    if pressure_range == 0:
        pressure_bins = 1

    temp_size = temp_range / temp_bins if temp_bins > 0 else 1.0
    pressure_size = pressure_range / pressure_bins if pressure_bins > 0 else 1.0

    counts = {}
    for row in rows:
        temp = row['temperature']
        pressure = row['pressure']
        t_bin = int((temp - min_temp) / temp_size) if temp_size else 0
        p_bin = int((pressure - min_pressure) / pressure_size) if pressure_size else 0
        if t_bin >= temp_bins:
            t_bin = temp_bins - 1
        if p_bin >= pressure_bins:
            p_bin = pressure_bins - 1
        counts[(t_bin, p_bin)] = counts.get((t_bin, p_bin), 0) + 1

    temp_precision = 0 if temp_size >= 1 else 2
    pressure_precision = 1 if pressure_size >= 1 else 3

    x_labels = []
    for i in range(temp_bins):
        start = min_temp + (i * temp_size)
        end = min_temp + ((i + 1) * temp_size)
        x_labels.append(f"{start:.{temp_precision}f}-{end:.{temp_precision}f}K")

    y_labels = []
    for i in range(pressure_bins):
        start = min_pressure + (i * pressure_size)
        end = min_pressure + ((i + 1) * pressure_size)
        y_labels.append(f"{start:.{pressure_precision}f}-{end:.{pressure_precision}f}MPa")

    data = [[t_bin, p_bin, count] for (t_bin, p_bin), count in counts.items()]

    return {
        "x_labels": x_labels,
        "y_labels": y_labels,
        "data": data,
        "meta": {
            "min_temp": min_temp,
            "max_temp": max_temp,
            "min_pressure": min_pressure,
            "max_pressure": max_pressure
        }
    }


@app.get("/api/chart/scatter-distribution", tags=["Chart"])
async def api_chart_scatter_distribution(
    limit: Optional[int] = Query(None, ge=1, le=200000)
):
    """获取温度-压力分布散点数据"""
    with get_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
        if limit is None:
            cursor.execute(
                "SELECT id, temperature, pressure FROM gas_mixture ORDER BY id"
            )
        else:
            cursor.execute(
                "SELECT id, temperature, pressure FROM gas_mixture ORDER BY id LIMIT ?",
                (limit,)
            )
        rows = cursor.fetchall()

    if not rows:
        return {"data": [], "pressure_min": 0, "pressure_max": 0, "count": 0}

    pressures = [row['pressure'] for row in rows]
    return {
        "data": [{"value": [row['temperature'], row['pressure'], row['pressure']], "id": row['id']} for row in rows],
        "pressure_min": min(pressures),
        "pressure_max": max(pressures),
        "count": len(rows)
    }


# ==================== 导入导出 API ====================

@app.get("/api/export/csv", tags=["Export"])
async def api_export_csv(user: dict = Depends(require_auth)):
    """导出所有数据为 CSV 文件"""
    records = get_all_records_no_pagination()
    
    # 创建 CSV 内容
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow([
        'ID', 'T (K)', 'xCH4', 'xC2H6', 'xC3H8', 
        'xCO2', 'xN2', 'xH2S', 'x i-C4H10', 'p (MPa)'
    ])
    
    # 写入数据
    for r in records:
        writer.writerow([
            r['id'], r['temperature'], r['x_ch4'], r['x_c2h6'], r['x_c3h8'],
            r['x_co2'], r['x_n2'], r['x_h2s'], r['x_ic4h10'], r['pressure']
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gas_data_export.csv"}
    )


@app.get("/api/export/excel", tags=["Export"])
async def api_export_excel(user: dict = Depends(require_auth)):
    """导出所有数据为 Excel 文件"""
    try:
        import pandas as pd
        
        records = get_all_records_no_pagination()
        
        # 转换为 DataFrame
        df = pd.DataFrame(records)
        
        # 重命名列
        column_mapping = {
            'id': 'ID',
            'temperature': 'T (K)',
            'x_ch4': 'xCH4',
            'x_c2h6': 'xC2H6',
            'x_c3h8': 'xC3H8',
            'x_co2': 'xCO2',
            'x_n2': 'xN2',
            'x_h2s': 'xH2S',
            'x_ic4h10': 'x i-C4H10',
            'pressure': 'p (MPa)'
        }
        
        # 选择需要的列并重命名
        export_columns = ['id', 'temperature', 'x_ch4', 'x_c2h6', 'x_c3h8', 
                         'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10', 'pressure']
        df = df[export_columns].rename(columns=column_mapping)
        
        # 写入 Excel
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=gas_data_export.xlsx"}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="需要安装 pandas 和 openpyxl")


@app.post("/api/import", tags=["Import"])
async def api_import_file(file: UploadFile = File(...), user: dict = Depends(require_auth)):
    """批量导入数据（支持 CSV 和 Excel 文件）"""
    if user["role"] not in ("admin", "user"):
        raise HTTPException(status_code=403, detail="权限不足")
    try:
        filename = file.filename.lower()
        content = await file.read()

        records, row_numbers, skipped = parse_import_content(filename, content)
        if not records:
            raise HTTPException(status_code=400, detail="文件中没有有效数据")

        validation_errors = []
        valid_records = []
        for idx, record in enumerate(records):
            is_valid, errors = validate_record(record)
            if is_valid:
                valid_records.append(record)
            else:
                row_number = row_numbers[idx] if idx < len(row_numbers) else (idx + 1)
                validation_errors.append({"row": row_number, "errors": errors})

        if validation_errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "导入校验失败",
                    "summary": {
                        "total": len(records),
                        "valid_count": len(valid_records),
                        "invalid_count": len(validation_errors),
                        "skipped_count": skipped,
                    },
                    "errors": validation_errors[:50],
                },
            )

        # 批量插入
        count = batch_create_records(valid_records)
        warning_count = count_soft_warnings(valid_records)
        
        return ApiResponse(
            success=True,
            message=f"成功导入 {count} 条记录" + format_soft_warning_count(warning_count),
            data={"imported_count": count, "warning_count": warning_count}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@app.post("/api/import/preview", tags=["Import"])
async def api_import_preview(file: UploadFile = File(...), user: dict = Depends(require_auth)):
    """导入前校验预览（不写入数据库）"""
    if user["role"] not in ("admin", "user"):
        raise HTTPException(status_code=403, detail="权限不足")
    try:
        filename = file.filename.lower()
        content = await file.read()

        records, row_numbers, skipped = parse_import_content(filename, content)
        if not records:
            raise HTTPException(status_code=400, detail="文件中没有有效数据")

        validation_errors = []
        warning_rows = []
        valid_count = 0

        for idx, record in enumerate(records):
            row_number = row_numbers[idx] if idx < len(row_numbers) else (idx + 1)
            is_valid, errors = validate_record(record)
            if is_valid:
                valid_count += 1
                warnings = get_soft_warnings(record)
                if warnings:
                    warning_rows.append({"row": row_number, "warnings": warnings})
            else:
                validation_errors.append({"row": row_number, "errors": errors})

        return {
            "success": True,
            "data": {
                "summary": {
                    "total": len(records),
                    "valid_count": valid_count,
                    "invalid_count": len(validation_errors),
                    "warning_count": len(warning_rows),
                    "skipped_count": skipped,
                },
                "errors": validation_errors[:50],
                "warnings": warning_rows[:50],
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


def parse_import_content(filename: str, content: bytes):
    """
    解析导入文件内容，返回可写入数据库的记录列表。

    Args:
        filename: 上传文件名（用于判断扩展名 csv/xlsx/xls）
        content: 文件二进制内容

    Returns:
        (records, row_numbers, skipped)
        - records: 解析成功的记录字典列表（字段名为数据库字段）
        - row_numbers: 对应原文件行号（用于报错定位）
        - skipped: 被跳过的行数（空行/无效行等）

    Raises:
        HTTPException: 当文件格式不支持时抛出 400。
    """
    records = []
    row_numbers = []
    skipped = 0

    if filename.endswith('.csv'):
        text = content.decode('utf-8-sig')  # 处理 BOM
        reader = csv.DictReader(io.StringIO(text))
        for idx, row in enumerate(reader, start=2):
            record = parse_import_row(row)
            if record:
                records.append(record)
                row_numbers.append(idx)
            else:
                skipped += 1
    elif filename.endswith(('.xlsx', '.xls')):
        import pandas as pd
        df = pd.read_excel(io.BytesIO(content))
        for idx, row in df.iterrows():
            record = parse_import_row(row.to_dict())
            if record:
                records.append(record)
                row_numbers.append(idx + 2)
            else:
                skipped += 1
    else:
        raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 CSV 或 Excel 文件")

    return records, row_numbers, skipped


def parse_import_row(row: dict) -> Optional[dict]:
    """
    解析单行导入数据，并将不同表头映射为数据库字段。

    Args:
        row: 一行数据（来自 CSV DictReader 或 Excel 行转换后的 dict）

    Returns:
        记录字典（包含 temperature/pressure 与 7 个组分字段）；
        当该行为空/无效（如温度与压力均为 0）时返回 None。

    Notes:
        - 本函数只做“字段映射与类型转换”的宽松解析，严格规则校验由 `validate_record` 负责。
        - 对无法转换为 float 的值会回落为 0.0，以便后续校验阶段给出更明确的错误信息。
    """
    # 支持多种列名格式
    column_mapping = {
        'temperature': ['T (K)', 'T(K)', 'temperature', 'Temperature', '温度'],
        'x_ch4': ['xCH4', 'CH4', 'x_ch4', '甲烷'],
        'x_c2h6': ['xC2H6', 'C2H6', 'x_c2h6', '乙烷'],
        'x_c3h8': ['xC3H8', 'C3H8', 'x_c3h8', '丙烷'],
        'x_co2': ['xCO2', 'CO2', 'x_co2', '二氧化碳'],
        'x_n2': ['xN2', 'N2', 'x_n2', '氮气'],
        'x_h2s': ['xH2S', 'H2S', 'x_h2s', '硫化氢'],
        'x_ic4h10': ['x i-C4H10', 'x_i-C4H10', 'iC4H10', 'x_ic4h10', '异丁烷'],
        'pressure': ['p (MPa)', 'p(MPa)', 'pressure', 'Pressure', '压力']
    }
    
    record = {}
    
    for db_field, possible_names in column_mapping.items():
        value = None
        for name in possible_names:
            if name in row:
                value = row[name]
                break
        
        try:
            if value is not None and str(value).strip() != '':
                record[db_field] = float(value)
            else:
                record[db_field] = 0.0
        except (ValueError, TypeError):
            record[db_field] = 0.0
    
    # 验证必填字段
    if record.get('temperature', 0) == 0 and record.get('pressure', 0) == 0:
        return None
    
    return record


# ==================== 静态文件服务 ====================

@app.get("/", tags=["Frontend"])
async def serve_frontend():
    """提供前端页面"""
    if os.path.exists(FRONTEND_INDEX):
        return FileResponse(FRONTEND_INDEX)
    return {"message": f"前端文件不存在: {FRONTEND_INDEX}，请访问 /docs 查看 API 文档"}


@app.get("/css/{filename}", tags=["Frontend"])
async def serve_css(filename: str):
    """提供 CSS 文件"""
    filepath = os.path.join(FRONTEND_CSS, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS file not found")


@app.get("/js/{filename}", tags=["Frontend"])
async def serve_js(filename: str):
    """提供 JS 文件"""
    filepath = os.path.join(FRONTEND_JS, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS file not found")


# ==================== 认证相关 API ====================

@app.post("/api/auth/login", tags=["Auth"])
async def api_login(request: LoginRequest, req: Request):
    """用户登录（支持两步验证）"""
    client_ip = req.client.host if req.client else "unknown"
    user_agent = req.headers.get("user-agent", "")
    
    # 检查登录尝试次数
    allowed, error_msg = check_login_attempts(client_ip)
    if not allowed:
        record_login(request.username, client_ip, user_agent, False, "登录尝试过多")
        raise HTTPException(status_code=429, detail=error_msg)
    
    # 验证用户名密码
    user = authenticate_user(request.username, request.password)
    if not user:
        record_login_attempt(client_ip, False)
        record_login(request.username, client_ip, user_agent, False, "密码错误")
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 检查是否需要两步验证
    if is_totp_enabled(request.username):
        if not request.totp_code:
            return {
                "success": False,
                "require_totp": True,
                "message": "需要两步验证码"
            }
        if not verify_user_totp(request.username, request.totp_code):
            record_login_attempt(client_ip, False)
            record_login(request.username, client_ip, user_agent, False, "两步验证失败")
            raise HTTPException(status_code=401, detail="两步验证码错误")
    
    # 登录成功
    record_login_attempt(client_ip, True)
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    
    # 创建会话
    create_session(token, user["username"], client_ip, user_agent)
    
    # 记录登录日志
    record_login(request.username, client_ip, user_agent, True)
    record_audit_log(request.username, "LOGIN", ip=client_ip)
    
    return {
        "success": True,
        "message": "登录成功",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": user,
            "totp_enabled": is_totp_enabled(request.username)
        }
    }


@app.get("/api/auth/me", tags=["Auth"])
async def api_get_me(user: dict = Depends(require_auth)):
    """获取当前用户信息"""
    return {
        "success": True,
        "data": user
    }


@app.post("/api/auth/change-password", tags=["Auth"])
async def api_change_password(request: ChangePasswordRequest, user: dict = Depends(require_auth)):
    """修改密码（带密码策略验证）"""
    # 验证密码策略
    is_valid, errors = validate_password(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"密码不符合要求: {', '.join(errors)}")
    
    success = change_password(user["username"], request.old_password, request.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="原密码错误")
    
    record_audit_log(user["username"], "CHANGE_PASSWORD")
    return {"success": True, "message": "密码修改成功"}


@app.get("/api/auth/password-policy", tags=["Auth"])
async def api_password_policy():
    """获取密码策略"""
    return {"success": True, "data": get_password_policy()}


@app.post("/api/auth/users", tags=["Auth"])
async def api_create_user(request: CreateUserRequest, user: dict = Depends(require_auth)):
    """创建新用户（仅管理员）"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    if request.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="角色无效")

    is_valid, errors = validate_password(request.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"密码不符合要求: {', '.join(errors)}")
    
    success = create_user(request.username, request.password, request.role)
    if not success:
        raise HTTPException(status_code=400, detail="用户已存在")
    
    return {"success": True, "message": "用户创建成功"}


@app.post("/api/auth/users/{username}/reset-password", tags=["Auth"])
async def api_reset_user_password(
    username: str,
    request: ResetUserPasswordRequest,
    user: dict = Depends(require_auth),
):
    """管理员重置用户密码"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    is_valid, errors = validate_password(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"密码不符合要求: {', '.join(errors)}")

    success = reset_user_password(username, request.new_password)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")

    record_audit_log(user["username"], "RESET_PASSWORD", "user", None, username)
    return {"success": True, "message": "密码已重置"}


@app.get("/api/auth/users", tags=["Auth"])
async def api_list_users(user: dict = Depends(require_auth)):
    """获取用户列表（仅管理员）"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    return {"success": True, "data": list_users()}


# ==================== TOTP 两步验证 API ====================

@app.post("/api/auth/totp/setup", tags=["TOTP"])
async def api_totp_setup(user: dict = Depends(require_auth)):
    """设置两步验证（返回密钥和二维码URI）"""
    secret, uri = setup_totp(user["username"])
    return {
        "success": True,
        "data": {
            "secret": secret,
            "uri": uri,
            "message": "请使用验证器App扫描二维码或手动输入密钥"
        }
    }


@app.post("/api/auth/totp/enable", tags=["TOTP"])
async def api_totp_enable(request: TOTPSetupRequest, user: dict = Depends(require_auth)):
    """启用两步验证（需要验证码确认）"""
    success = enable_totp(user["username"], request.code)
    if not success:
        raise HTTPException(status_code=400, detail="验证码错误，请重试")
    
    record_audit_log(user["username"], "ENABLE_TOTP")
    return {"success": True, "message": "两步验证已启用"}


@app.post("/api/auth/totp/disable", tags=["TOTP"])
async def api_totp_disable(user: dict = Depends(require_auth)):
    """禁用两步验证"""
    success = disable_totp(user["username"])
    record_audit_log(user["username"], "DISABLE_TOTP")
    return {"success": True, "message": "两步验证已禁用"}


@app.get("/api/auth/totp/status", tags=["TOTP"])
async def api_totp_status(user: dict = Depends(require_auth)):
    """获取两步验证状态"""
    status = get_totp_status(user["username"])
    return {"success": True, "data": status}


@app.post("/api/auth/totp/backup-codes", tags=["TOTP"])
async def api_regenerate_backup_codes(user: dict = Depends(require_auth)):
    """重新生成备用码"""
    codes = regenerate_backup_codes(user["username"])
    record_audit_log(user["username"], "REGENERATE_BACKUP_CODES")
    return {"success": True, "data": {"backup_codes": codes}}


# ==================== 会话管理 API ====================

@app.get("/api/auth/sessions", tags=["Sessions"])
async def api_get_sessions(user: dict = Depends(require_auth)):
    """获取当前用户的所有会话"""
    sessions = get_user_sessions(user["username"])
    return {"success": True, "data": sessions}


@app.delete("/api/auth/sessions/{session_id}", tags=["Sessions"])
async def api_revoke_session(session_id: int, user: dict = Depends(require_auth)):
    """撤销指定会话"""
    # 这里需要根据session_id查找并撤销
    return {"success": True, "message": "会话已撤销"}


@app.post("/api/auth/sessions/revoke-all", tags=["Sessions"])
async def api_revoke_all_sessions(user: dict = Depends(require_auth), authorization: Optional[str] = Header(None)):
    """撤销除当前会话外的所有会话"""
    token = get_token_from_header(authorization)
    count = revoke_all_user_sessions(user["username"], except_token=token)
    record_audit_log(user["username"], "REVOKE_ALL_SESSIONS")
    return {"success": True, "message": f"已撤销 {count} 个会话"}


@app.get("/api/auth/users/{username}/sessions", tags=["Sessions"])
async def api_get_user_sessions(
    username: str,
    user: dict = Depends(require_auth),
):
    """管理员查看用户会话"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    sessions = get_user_sessions(username)
    return {"success": True, "data": sessions}


@app.post("/api/auth/users/{username}/sessions/revoke-all", tags=["Sessions"])
async def api_admin_revoke_user_sessions(
    username: str,
    user: dict = Depends(require_auth),
    authorization: Optional[str] = Header(None),
):
    """管理员撤销用户全部会话"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    token = get_token_from_header(authorization)
    except_token = token if username == user["username"] else None
    count = revoke_all_user_sessions(username, except_token=except_token)
    record_audit_log(user["username"], "REVOKE_USER_SESSIONS", "user", None, username)
    return {"success": True, "message": f"已撤销 {count} 个会话"}


@app.post("/api/auth/logout", tags=["Sessions"])
async def api_logout(user: dict = Depends(require_auth), authorization: Optional[str] = Header(None)):
    """退出登录"""
    token = get_token_from_header(authorization)
    if token:
        revoke_session(token)
    record_audit_log(user["username"], "LOGOUT")
    return {"success": True, "message": "已退出登录"}


# ==================== 登录日志 API ====================

@app.get("/api/security/login-logs", tags=["Security"])
async def api_get_login_logs(
    user: dict = Depends(require_auth),
    username: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """获取登录日志"""
    if user["role"] != "admin":
        # 非管理员只能看自己的日志
        username = user["username"]
    
    logs = get_login_logs(username, limit)
    return {"success": True, "data": logs}


@app.get("/api/security/audit-logs", tags=["Security"])
async def api_get_audit_logs(
    user: dict = Depends(require_auth),
    username: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """获取审计日志（仅管理员）"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    logs = get_audit_logs(username=username, action=action, limit=limit)
    return {"success": True, "data": logs}


@app.get("/api/security/rate-limit", tags=["Security"])
async def api_rate_limit_status(req: Request):
    """获取当前IP的限流状态"""
    client_ip = req.client.host if req.client else "unknown"
    status = get_rate_limit_status(client_ip)
    return {"success": True, "data": status}


# ==================== 批量操作 API ====================

@app.post("/api/records/batch-delete", tags=["Batch"])
async def api_batch_delete(request: BatchDeleteRequest, user: dict = Depends(require_auth)):
    """批量删除记录"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    count = batch_delete_records(request.ids)
    record_audit_log(user["username"], "BATCH_DELETE", "records", None, str(request.ids))
    return {"success": True, "message": f"成功删除 {count} 条记录", "data": {"deleted_count": count}}


@app.post("/api/records/batch-update", tags=["Batch"])
async def api_batch_update(request: BatchUpdateRequest, user: dict = Depends(require_auth)):
    """批量更新记录"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    if not request.updates:
        raise HTTPException(status_code=400, detail="没有要更新的数据")

    is_valid, errors = validate_partial_record(request.updates)
    if not is_valid:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    count = batch_update_records(request.ids, request.updates)
    record_audit_log(user["username"], "BATCH_UPDATE", "records", None, str(request.ids), str(request.updates))
    warning_note = format_soft_warning(get_soft_warnings(request.updates))
    return {
        "success": True,
        "message": f"成功更新 {count} 条记录{warning_note}",
        "data": {"updated_count": count}
    }


# ==================== 数据历史 API ====================

@app.get("/api/records/{record_id}/history", tags=["History"])
async def api_get_record_history(record_id: int, user: dict = Depends(require_auth)):
    """获取记录的修改历史"""
    history = get_data_history(record_id=record_id)
    return {"success": True, "data": history}


@app.get("/api/history", tags=["History"])
async def api_get_all_history(
    user: dict = Depends(require_auth),
    limit: int = Query(100, ge=1, le=500),
    record_id: Optional[int] = Query(None, ge=1),
    action: Optional[str] = None,
    username: Optional[str] = None,
):
    """获取所有数据修改历史"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    history = get_data_history(record_id=record_id, action=action, username=username, limit=limit)
    return {"success": True, "data": history}


# ==================== 数据校验 API ====================

@app.get("/api/validation/rules", tags=["Validation"])
async def api_get_validation_rules():
    """获取数据校验规则"""
    return {"success": True, "data": get_validation_rules()}


@app.get("/api/validation/constraints", tags=["Validation"])
async def api_get_field_constraints():
    """获取字段约束（用于前端表单验证）"""
    return {"success": True, "data": get_field_constraints()}


@app.post("/api/validation/check", tags=["Validation"])
async def api_validate_data(records: List[dict]):
    """预校验数据（不入库）"""
    result = validate_batch(records)
    return {"success": True, "data": result}


# ==================== 数据审核 API ====================

class ApproveRequest(BaseModel):
    selected_ids: List[int]


class ApproveBatchItem(BaseModel):
    group_id: str
    selected_ids: List[int]


class ApproveBatchRequest(BaseModel):
    items: List[ApproveBatchItem]


class GroupBatchRequest(BaseModel):
    group_ids: List[str]

@app.get("/api/review/duplicates", tags=["Review"])
async def api_find_duplicates(user: dict = Depends(require_auth)):
    """查找同组分同温度下有多个压力值的数据"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    duplicates = find_duplicate_pressure_records()
    return {"success": True, "data": duplicates, "count": len(duplicates)}


@app.post("/api/review/move-duplicates", tags=["Review"])
async def api_move_duplicates(user: dict = Depends(require_auth)):
    """将重复数据移到待审核区"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    result = move_duplicates_to_review()
    record_audit_log(user["username"], "MOVE_DUPLICATES", None, None, None, str(result))
    return {"success": True, "message": f"已移动 {result['moved']} 条记录到待审核区", "data": result}


@app.get("/api/review/pending", tags=["Review"])
async def api_get_pending_groups(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    group_id: Optional[str] = None,
    temp_min: Optional[float] = None,
    temp_max: Optional[float] = None,
    user: dict = Depends(require_auth),
):
    """获取待审核的数据组"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")

    result = get_pending_groups(
        page=page,
        per_page=per_page,
        group_id=group_id,
        temp_min=temp_min,
        temp_max=temp_max,
    )
    return {"success": True, "data": result, "count": result["total"]}


@app.get("/api/review/stats", tags=["Review"])
async def api_get_review_stats(user: dict = Depends(require_auth)):
    """获取审核统计信息"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    stats = get_pending_stats()
    return {"success": True, "data": stats}


@app.put("/api/review/pressure/{pending_id}", tags=["Review"])
async def api_update_pressure(pending_id: int, pressure: float, user: dict = Depends(require_auth)):
    """更新待审核记录的压力值"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    success = update_pending_pressure(pending_id, pressure)
    if not success:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    return {"success": True, "message": "压力值已更新"}


@app.post("/api/review/approve/{group_id}", tags=["Review"])
async def api_approve_group(group_id: str, request: ApproveRequest, user: dict = Depends(require_auth)):
    """审核通过一组数据"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    result = approve_group(group_id, request.selected_ids, user["username"])
    record_audit_log(user["username"], "APPROVE_GROUP", "review", None, group_id, str(result))
    return {"success": True, "message": f"已审核通过 {result['approved']} 条记录", "data": result}


@app.post("/api/review/approve-batch", tags=["Review"])
async def api_approve_groups(request: ApproveBatchRequest, user: dict = Depends(require_auth)):
    """批量审核通过多组数据"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    if not request.items:
        raise HTTPException(status_code=400, detail="未提供审核数据")

    total_approved = 0
    results = []
    for item in request.items:
        result = approve_group(item.group_id, item.selected_ids, user["username"])
        results.append(result)
        total_approved += result.get("approved", 0)

    record_audit_log(user["username"], "APPROVE_GROUP_BATCH", "review", None, None, str(results))
    return {"success": True, "message": f"批量审核通过 {total_approved} 条记录", "data": results}


@app.post("/api/review/reject/{group_id}", tags=["Review"])
async def api_reject_group(group_id: str, user: dict = Depends(require_auth)):
    """拒绝整组数据"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    success = reject_group(group_id, user["username"])
    record_audit_log(user["username"], "REJECT_GROUP", "review", None, group_id)
    return {"success": True, "message": "已拒绝该组数据"}


@app.post("/api/review/reject-batch", tags=["Review"])
async def api_reject_groups(request: GroupBatchRequest, user: dict = Depends(require_auth)):
    """批量拒绝多组数据"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    if not request.group_ids:
        raise HTTPException(status_code=400, detail="未提供组ID")

    rejected = 0
    for group_id in request.group_ids:
        if reject_group(group_id, user["username"]):
            rejected += 1

    record_audit_log(user["username"], "REJECT_GROUP_BATCH", "review", None, None, str(request.group_ids))
    return {"success": True, "message": f"已拒绝 {rejected} 组数据"}


@app.post("/api/review/restore/{group_id}", tags=["Review"])
async def api_restore_group(group_id: str, user: dict = Depends(require_auth)):
    """恢复一组数据到待审核状态"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    result = restore_group(group_id)
    return {"success": True, "message": f"已恢复 {result['restored']} 条记录", "data": result}


@app.post("/api/review/restore-batch", tags=["Review"])
async def api_restore_groups(request: GroupBatchRequest, user: dict = Depends(require_auth)):
    """批量恢复多组数据到待审核"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    if not request.group_ids:
        raise HTTPException(status_code=400, detail="未提供组ID")

    restored = 0
    for group_id in request.group_ids:
        result = restore_group(group_id)
        restored += result.get("restored", 0)

    record_audit_log(user["username"], "RESTORE_GROUP_BATCH", "review", None, None, str(request.group_ids))
    return {"success": True, "message": f"已恢复 {restored} 条记录"}


# ==================== 受保护的公开查询 API ====================

class AvailableComponentsRequest(BaseModel):
    selected: List[str]  # ['x_ch4', 'x_c2h6', ...]

class RangeQueryRequest(BaseModel):
    components: List[str]
    ranges: dict  # {'x_ch4': {'min': 0.9, 'max': 0.95}, ...}
    temperature: float

@app.post("/api/components/available", tags=["Public Query"])
async def api_available_components(request: AvailableComponentsRequest):
    """
    根据已选组分，查询数据库中还有哪些可用的组分组合
    """
    selected = request.selected

    all_components = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
    
    try:
        with get_connection(dict_cursor=True) as conn:
            cursor = conn.cursor()

            # 构建查询条件：已选组分必须 > 0
            conditions = []
            for comp in selected:
                conditions.append(f"{comp} > 0")

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 查询匹配的记录数
            cursor.execute(f"SELECT COUNT(*) as count FROM gas_mixture WHERE {where_clause}")
            row = cursor.fetchone()
            match_count = row['count'] if row else 0

            # 查找还能添加哪些组分（在已有条件下，该组分也有 > 0 的记录）
            available = []
            for comp in all_components:
                if comp in selected:
                    continue

                test_conditions = conditions + [f"{comp} > 0"]
                test_where = " AND ".join(test_conditions)

                cursor.execute(f"SELECT COUNT(*) as count FROM gas_mixture WHERE {test_where}")
                row = cursor.fetchone()
                count = row['count'] if row else 0

                if count > 0:
                    available.append(comp)

            return {
                "success": True,
                "available": available,
                "match_count": match_count
            }
        
    except Exception as e:
        return {"success": False, "message": str(e)}


class ComponentRangesRequest(BaseModel):
    components: List[str]  # ['x_ch4', 'x_c2h6', ...]

@app.post("/api/components/ranges", tags=["Public Query"])
async def api_component_ranges(request: ComponentRangesRequest):
    """
    根据选定的组分，返回数据库中每个组分的实际区间范围
    """
    components = request.components

    all_components = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
    
    try:
        with get_connection(dict_cursor=True) as conn:
            cursor = conn.cursor()
        
            # 构建查询条件：已选组分必须 > 0，未选组分必须接近0
            conditions = []
            for comp in components:
                conditions.append(f"{comp} > 0")
            for comp in all_components:
                if comp not in components:
                    conditions.append(f"{comp} <= 0.02")

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 查询每个组分的min和max
            ranges = {}
            for comp in components:
                cursor.execute(
                    f"SELECT MIN({comp}) as min_val, MAX({comp}) as max_val FROM gas_mixture WHERE {where_clause}"
                )
                row = cursor.fetchone()
                if row and row['min_val'] is not None:
                    ranges[comp] = {
                        'min': row['min_val'],
                        'max': row['max_val']
                    }

            # 查询总记录数
            cursor.execute(f"SELECT COUNT(*) as count FROM gas_mixture WHERE {where_clause}")
            row = cursor.fetchone()
            total_records = row['count'] if row else 0

            # 查询温度范围
            cursor.execute(
                f"SELECT MIN(temperature) as min_temp, MAX(temperature) as max_temp FROM gas_mixture WHERE {where_clause}"
            )
            temp_row = cursor.fetchone()
            temp_range = None
            if temp_row and temp_row['min_temp'] is not None:
                temp_range = {
                    'min': temp_row['min_temp'],
                    'max': temp_row['max_temp']
                }

            return {
                "success": True,
                "ranges": ranges,
                "total_records": total_records,
                "temp_range": temp_range
            }
        
    except Exception as e:
        return {"success": False, "message": str(e)}


class QueryByComponentsRequest(BaseModel):
    components: List[str]
    temperature: float

@app.post("/api/query/by-components", tags=["Public Query"])
async def api_query_by_components(request: QueryByComponentsRequest):
    """
    根据组分组合和温度查询相平衡压力
    """
    components = request.components
    temperature = request.temperature

    all_components = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
    
    try:
        with get_connection(dict_cursor=True) as conn:
            cursor = conn.cursor()

            # 构建查询条件：已选组分 > 0，未选组分 <= 0.02
            conditions = []
            for comp in components:
                conditions.append(f"{comp} > 0")
            for comp in all_components:
                if comp not in components:
                    conditions.append(f"{comp} <= 0.02")

            # 温度范围 ±5K
            conditions.append("ABS(temperature - ?) <= 5")

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT temperature, pressure, {', '.join(all_components)}
                FROM gas_mixture
                WHERE {where_clause}
                ORDER BY ABS(temperature - ?)
                LIMIT 1
            """

            cursor.execute(query, [temperature, temperature])
            row = cursor.fetchone()

            if row:
                composition = {}
                for comp in all_components:
                    composition[comp] = row[comp]

                return {
                    "success": True,
                    "data": {
                        "temperature": row['temperature'],
                        "pressure": row['pressure'],
                        "composition": composition
                    }
                }
            return {
                "success": False,
                "message": "在指定的温度范围内未找到数据"
            }
            
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/query/range", tags=["Public Query"])
async def api_range_query(request: RangeQueryRequest):
    """
    根据组分范围和温度查询相平衡压力
    """
    components = request.components
    ranges = request.ranges
    temperature = request.temperature

    all_components = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
    
    try:
        with get_connection(dict_cursor=True) as conn:
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            for comp in all_components:
                if comp in components and comp in ranges:
                    # 已选组分：在范围内
                    r = ranges[comp]
                    conditions.append(f"({comp} >= ? AND {comp} <= ?)")
                    params.extend([r['min'], r['max']])
                else:
                    # 未选组分：必须为0或接近0
                    conditions.append(f"{comp} <= 0.02")

            # 温度范围 ±5K
            conditions.append("ABS(temperature - ?) <= 5")
            params.append(temperature)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT temperature, pressure
                FROM gas_mixture
                WHERE {where_clause}
                ORDER BY ABS(temperature - ?)
                LIMIT 1
            """
            params.append(temperature)

            cursor.execute(query, params)
            row = cursor.fetchone()

            if row:
                return {
                    "success": True,
                    "data": {
                        "temperature": row['temperature'],
                        "pressure": row['pressure']
                    }
                }
            return {
                "success": False,
                "message": "在指定的组分范围和温度下未找到数据"
            }
            
    except Exception as e:
        return {"success": False, "message": str(e)}


class MatchCountRequest(BaseModel):
    components: List[str]
    ranges: dict  # {'x_ch4': {'min': 0.9, 'max': 0.95}, ...}

@app.post("/api/query/match-count", tags=["Public Query"])
async def api_match_count(request: MatchCountRequest):
    """
    根据组分范围查询匹配的数据条数（不考虑温度）
    返回模糊数量：100+, 10+, <10, 0
    """
    components = request.components
    ranges = request.ranges

    all_components = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
    
    try:
        with get_connection(dict_cursor=True) as conn:
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            for comp in all_components:
                if comp in components and comp in ranges:
                    # 已选组分：在范围内
                    r = ranges[comp]
                    conditions.append(f"({comp} >= ? AND {comp} <= ?)")
                    params.extend([r['min'], r['max']])
                else:
                    # 未选组分：必须为0或接近0
                    conditions.append(f"{comp} <= 0.02")

            where_clause = " AND ".join(conditions)

            cursor.execute(f"SELECT COUNT(*) as count FROM gas_mixture WHERE {where_clause}", params)
            row = cursor.fetchone()
            count = row['count'] if row else 0

            # 返回模糊数量
            if count == 0:
                display = "0"
            elif count < 10:
                display = "<10"
            elif count < 100:
                display = "10+"
            else:
                display = "100+"

            return {
                "success": True,
                "count": count,
                "display": display
            }
        
    except Exception as e:
        return {"success": False, "message": str(e), "count": 0, "display": "0"}


class HydrateQueryRequest(BaseModel):
    components: dict  # {'x_ch4': 0.9, 'x_c2h6': 0.1, ...}
    temperature: float
    tolerance: float = 0.02  # 默认2%容差

@app.post("/api/query/hydrate", tags=["Public Query"])
async def api_hydrate_query(request: HydrateQueryRequest):
    """
    气体水合物相平衡查询接口
    - 用户输入组分摩尔分数 + 温度
    - 查找最匹配的实验数据点
    - 返回相平衡压力
    """
    components = request.components
    temperature = request.temperature
    tolerance = request.tolerance
    
    # 组分列表
    comp_cols = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
    
    try:
        with get_connection(dict_cursor=True) as conn:
            cursor = conn.cursor()

            # 构建查询 - 先按组分筛选，再按温度排序
            conditions = []
            params = []

            for col in comp_cols:
                user_val = components.get(col, 0)
                if user_val > 0.001:  # 用户输入了该组分
                    # 允许一定容差
                    conditions.append(f"ABS({col} - ?) <= ?")
                    params.extend([user_val, tolerance])
                else:
                    # 用户没输入该组分，要求数据库中也接近0
                    conditions.append(f"{col} <= ?")
                    params.append(tolerance)

            # 温度筛选 - 允许±5K范围
            conditions.append("ABS(temperature - ?) <= 5")
            params.append(temperature)

            where_clause = " AND ".join(conditions)

            # 查询并计算匹配度
            query = f"""
                SELECT temperature, pressure, x_ch4, x_c2h6, x_c3h8, x_co2, x_n2, x_h2s, x_ic4h10
                FROM gas_mixture
                WHERE {where_clause}
                ORDER BY ABS(temperature - ?)
                LIMIT 1
            """
            params.append(temperature)

            cursor.execute(query, params)
            row = cursor.fetchone()

            if row:
                # 计算匹配度分数
                match_score = 100
                for col in comp_cols:
                    user_val = components.get(col, 0)
                    db_val = row[col]
                    diff = abs(user_val - db_val)
                    if diff > 0.001:
                        match_score -= diff * 100  # 每1%差异扣1分

                temp_diff = abs(row['temperature'] - temperature)
                match_score -= temp_diff * 2  # 每1K温差扣2分

                match_score = max(0, min(100, round(match_score)))

                return {
                    "success": True,
                    "data": {
                        "temperature": row['temperature'],
                        "pressure": row['pressure'],
                        "match_score": match_score
                    }
                }
            return {
                "success": False,
                "message": "未找到匹配的实验数据，请调整组分或温度"
            }
            
    except Exception as e:
        return {"success": False, "message": str(e)}


# ==================== 数据模板 API ====================

@app.get("/api/template/csv", tags=["Template"])
async def api_download_csv_template():
    """下载 CSV 导入模板"""
    template = '''T (K),xCH4,xC2H6,xC3H8,xCO2,xN2,xH2S,x i-C4H10,p (MPa)
300,0.9,0.05,0.02,0.01,0.01,0.005,0.005,10.5
310,0.85,0.08,0.03,0.02,0.01,0.005,0.005,15.2
'''
    return StreamingResponse(
        iter([template]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=import_template.csv"}
    )


@app.get("/api/template/excel", tags=["Template"])
async def api_download_excel_template():
    """下载 Excel 导入模板"""
    try:
        import pandas as pd
        
        # 创建模板数据
        template_data = {
            'T (K)': [300, 310],
            'xCH4': [0.9, 0.85],
            'xC2H6': [0.05, 0.08],
            'xC3H8': [0.02, 0.03],
            'xCO2': [0.01, 0.02],
            'xN2': [0.01, 0.01],
            'xH2S': [0.005, 0.005],
            'x i-C4H10': [0.005, 0.005],
            'p (MPa)': [10.5, 15.2]
        }
        
        df = pd.DataFrame(template_data)
        
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=import_template.xlsx"}
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="需要安装 pandas 和 openpyxl")


# ==================== 备份相关 API ====================

@app.get("/api/backup/status", tags=["Backup"])
async def api_backup_status(user: dict = Depends(require_auth)):
    """获取备份状态"""
    return {"success": True, "data": get_backup_status()}


@app.get("/api/backup/list", tags=["Backup"])
async def api_backup_list(user: dict = Depends(require_auth)):
    """获取备份列表"""
    return {"success": True, "data": list_backups()}


@app.post("/api/backup/create", tags=["Backup"])
async def api_create_backup(user: dict = Depends(require_auth)):
    """手动创建备份"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    backup_path = create_backup(manual=True)
    if backup_path:
        return {"success": True, "message": "备份创建成功", "data": {"path": backup_path}}
    if not is_backup_supported():
        return {"success": False, "message": "当前使用托管数据库，请在云控制台创建备份"}
    raise HTTPException(status_code=500, detail="备份创建失败")


@app.post("/api/backup/restore/{filename}", tags=["Backup"])
async def api_restore_backup(filename: str, user: dict = Depends(require_auth)):
    """恢复备份"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    success = restore_backup(filename)
    if success:
        return {"success": True, "message": "备份恢复成功"}
    if not is_backup_supported():
        return {"success": False, "message": "当前使用托管数据库，请在云控制台进行恢复"}
    raise HTTPException(status_code=500, detail="备份恢复失败")


@app.delete("/api/backup/{filename}", tags=["Backup"])
async def api_delete_backup(filename: str, user: dict = Depends(require_auth)):
    """删除备份"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    
    success = delete_backup(filename)
    if success:
        return {"success": True, "message": "备份删除成功"}
    raise HTTPException(status_code=404, detail="备份不存在")


@app.get("/api/backup/download/{filename}", tags=["Backup"])
async def api_download_backup(filename: str, user: dict = Depends(require_auth)):
    """下载备份文件"""
    backup_dir = get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="备份不存在")
    
    return FileResponse(
        filepath,
        media_type="application/octet-stream",
        filename=filename
    )


# ==================== 后台管理路由 ====================

ADMIN_DIR = os.path.join(FRONTEND_DIR, "admin")


@app.get("/admin", tags=["Admin"])
async def serve_admin():
    """后台管理页面"""
    admin_index = os.path.join(ADMIN_DIR, "index.html")
    if os.path.exists(admin_index):
        return FileResponse(admin_index)
    return {"message": "后台管理页面不存在"}


# ==================== 启动事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("[App] 正在初始化安全模块...")
    init_security()
    ensure_admin_user()
    if is_using_default_secret_key():
        print("[Security] WARNING: SECRET_KEY 使用默认值，请在生产环境中设置环境变量")
    if not is_admin_configured():
        print("[Auth] WARNING: 未设置 ADMIN_PASSWORD，管理员登录已禁用")
    print("[App] 正在初始化备份系统...")
    init_backup_system()
    
    # 初始化缓存
    print("[App] 正在初始化缓存系统...")
    cache = init_cache()
    if cache.is_connected():
        print("[Cache] Redis缓存已连接")
    else:
        print("[Cache] WARNING: Redis未连接，缓存功能不可用")
    
    print("[App] 系统启动完成 v4.0")


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # 设置输出编码
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("\n" + "="*60)
    print("   Gas Mixture Data Management System - FastAPI v4.0")
    print("="*60)
    print("   API Docs: http://127.0.0.1:8000/docs")
    print("   Frontend: http://127.0.0.1:8000")
    print("   Admin:    http://127.0.0.1:8000/admin")
    print("-"*60)
    print("   Security Features:")
    print("      - JWT Auth + PBKDF2 Password Encryption")
    print("      - TOTP Two-Factor Authentication")
    print("      - API Rate Limiting + Anti-Crawler")
    print("      - Login Logs + Session Management")
    print("-"*60)
    admin_user = get_admin_username()
    if is_admin_configured():
        print(f"   Admin User: {admin_user} (password from ADMIN_PASSWORD)")
    else:
        print(f"   Admin User: {admin_user} (set ADMIN_PASSWORD to enable login)")
    print("="*60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)


"""
Pydantic 数据模型
用于请求和响应的数据验证
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class GasRecordBase(BaseModel):
    """气体记录基础模型"""
    temperature: float
    pressure: float
    x_ch4: float = 0
    x_c2h6: float = 0
    x_c3h8: float = 0
    x_co2: float = 0
    x_n2: float = 0
    x_h2s: float = 0
    x_ic4h10: float = 0


class GasRecordCreate(GasRecordBase):
    """创建气体记录的请求模型"""
    pass


class GasRecordUpdate(BaseModel):
    """更新气体记录的请求模型"""
    temperature: Optional[float] = None
    pressure: Optional[float] = None
    x_ch4: Optional[float] = None
    x_c2h6: Optional[float] = None
    x_c3h8: Optional[float] = None
    x_co2: Optional[float] = None
    x_n2: Optional[float] = None
    x_h2s: Optional[float] = None
    x_ic4h10: Optional[float] = None


class GasRecord(GasRecordBase):
    """气体记录响应模型"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    records: List[GasRecord]
    total: int
    page: int
    per_page: int
    total_pages: int


class Statistics(BaseModel):
    """统计信息模型"""
    total_records: int
    min_temperature: Optional[float]
    max_temperature: Optional[float]
    avg_temperature: Optional[float]
    min_pressure: Optional[float]
    max_pressure: Optional[float]
    avg_pressure: Optional[float]


class ApiResponse(BaseModel):
    """通用API响应模型"""
    success: bool
    message: str
    data: Optional[dict] = None


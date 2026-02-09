"""
数据校验模块 - 导入时自动校验数据有效性

本模块的职责：
- 对单条/批量记录进行字段范围、必填项、类型等校验
- 提供“软提示”机制：不阻止写入，但提醒可能的异常值（如压力偏高、组分和偏差较大）
- 提供数据清洗函数：统一将输入转换为 float 并填充默认值
"""

import re
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass


PRESSURE_SOFT_MAX = 10.0
SUM_SOFT_TOLERANCE = 0.02
SUM_HARD_TOLERANCE = 0.05


@dataclass
class ValidationRule:
    """校验规则"""
    field: str
    rule_type: str
    params: dict
    error_message: str


# ==================== 预定义校验规则 ====================

GAS_MIXTURE_RULES = [
    # 温度校验
    ValidationRule(
        field='temperature',
        rule_type='range',
        params={'min': 100, 'max': 1000},
        error_message='温度必须在 100-1000 K 范围内'
    ),
    ValidationRule(
        field='temperature',
        rule_type='required',
        params={},
        error_message='温度不能为空'
    ),
    
    # 压力校验
    ValidationRule(
        field='pressure',
        rule_type='range',
        params={'min': 0, 'max': 10000},
        error_message='压力必须在 0-10000 MPa 范围内'
    ),
    ValidationRule(
        field='pressure',
        rule_type='required',
        params={},
        error_message='压力不能为空'
    ),
    
    # 摩尔分数校验（每个组分 0-1）
    ValidationRule(
        field='x_ch4',
        rule_type='range',
        params={'min': 0, 'max': 1},
        error_message='CH4 摩尔分数必须在 0-1 范围内'
    ),
    ValidationRule(
        field='x_c2h6',
        rule_type='range',
        params={'min': 0, 'max': 1},
        error_message='C2H6 摩尔分数必须在 0-1 范围内'
    ),
    ValidationRule(
        field='x_c3h8',
        rule_type='range',
        params={'min': 0, 'max': 1},
        error_message='C3H8 摩尔分数必须在 0-1 范围内'
    ),
    ValidationRule(
        field='x_co2',
        rule_type='range',
        params={'min': 0, 'max': 1},
        error_message='CO2 摩尔分数必须在 0-1 范围内'
    ),
    ValidationRule(
        field='x_n2',
        rule_type='range',
        params={'min': 0, 'max': 1},
        error_message='N2 摩尔分数必须在 0-1 范围内'
    ),
    ValidationRule(
        field='x_h2s',
        rule_type='range',
        params={'min': 0, 'max': 1},
        error_message='H2S 摩尔分数必须在 0-1 范围内'
    ),
    ValidationRule(
        field='x_ic4h10',
        rule_type='range',
        params={'min': 0, 'max': 1},
        error_message='i-C4H10 摩尔分数必须在 0-1 范围内'
    ),
]


# ==================== 校验函数 ====================

def validate_required(value: Any) -> bool:
    """必填校验"""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == '':
        return False
    return True


def validate_range(value: float, min_val: float = None, max_val: float = None) -> bool:
    """范围校验"""
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True
    except (ValueError, TypeError):
        return False


def validate_type(value: Any, expected_type: str) -> bool:
    """类型校验"""
    type_map = {
        'int': int,
        'float': float,
        'str': str,
        'number': (int, float)
    }
    expected = type_map.get(expected_type)
    if not expected:
        return True
    
    try:
        if expected_type in ('int', 'float', 'number'):
            float(value)  # 尝试转换
            return True
        return isinstance(value, expected)
    except (ValueError, TypeError):
        return False


def validate_pattern(value: str, pattern: str) -> bool:
    """正则表达式校验"""
    if not isinstance(value, str):
        value = str(value)
    return bool(re.match(pattern, value))


def validate_sum(values: List[float], expected_sum: float, tolerance: float = 0.01) -> bool:
    """
    总和校验（用于摩尔分数之和应接近 1.0）。

    Args:
        values: 数值列表
        expected_sum: 期望总和（通常为 1.0）
        tolerance: 允许误差

    Returns:
        是否在容差范围内。
    """
    try:
        total = sum(float(v) for v in values if v is not None)
        return abs(total - expected_sum) <= tolerance
    except (ValueError, TypeError):
        return False


# ==================== 主校验函数 ====================

def validate_record(record: Dict[str, Any], rules: List[ValidationRule] = None) -> Tuple[bool, List[str]]:
    """
    校验单条记录
    返回: (是否有效, 错误列表)

    Args:
        record: 单条记录字典（字段名为数据库字段）
        rules: 校验规则列表；不传则使用默认 `GAS_MIXTURE_RULES`

    Returns:
        (is_valid, errors)
        - is_valid: 是否通过校验
        - errors: 错误信息列表（可直接拼接给用户）

    Notes:
        - 本函数会额外检查：7 个组分摩尔分数之和是否接近 1.0
        - 硬阈值（SUM_HARD_TOLERANCE）超出会视为错误
    """
    if rules is None:
        rules = GAS_MIXTURE_RULES
    
    errors = []
    
    for rule in rules:
        value = record.get(rule.field)
        
        if rule.rule_type == 'required':
            if not validate_required(value):
                errors.append(f"第{rule.field}列: {rule.error_message}")
        
        elif rule.rule_type == 'range':
            if value is not None and str(value).strip() != '':
                if not validate_range(value, rule.params.get('min'), rule.params.get('max')):
                    errors.append(f"第{rule.field}列: {rule.error_message}")
        
        elif rule.rule_type == 'type':
            if value is not None:
                if not validate_type(value, rule.params.get('type', 'str')):
                    errors.append(f"第{rule.field}列: {rule.error_message}")
        
        elif rule.rule_type == 'pattern':
            if value is not None:
                if not validate_pattern(value, rule.params.get('pattern', '.*')):
                    errors.append(f"第{rule.field}列: {rule.error_message}")
    
    # 额外校验：摩尔分数之和
    mole_fractions = [
        record.get('x_ch4', 0),
        record.get('x_c2h6', 0),
        record.get('x_c3h8', 0),
        record.get('x_co2', 0),
        record.get('x_n2', 0),
        record.get('x_h2s', 0),
        record.get('x_ic4h10', 0)
    ]
    
    # 转换为浮点数
    try:
        mole_fractions = [float(x) if x else 0 for x in mole_fractions]
        total = sum(mole_fractions)
        if total == 0:
            errors.append("摩尔分数不能全部为 0")
        elif abs(total - 1.0) > SUM_HARD_TOLERANCE:  # 允许5%误差
            errors.append(f"摩尔分数之和为 {total:.4f}，应接近 1.0")
    except (ValueError, TypeError):
        pass  # 类型错误已经在上面处理
    
    return len(errors) == 0, errors


def validate_partial_record(record: Dict[str, Any], rules: List[ValidationRule] = None) -> Tuple[bool, List[str]]:
    """
    校验部分字段（用于更新场景）
    仅校验提供的字段，忽略 required 规则。

    Args:
        record: 待更新字段字典（只包含部分字段）
        rules: 校验规则列表；不传则使用默认 `GAS_MIXTURE_RULES`

    Returns:
        (is_valid, errors)

    Notes:
        - 组分总和校验仅在“全部 7 个组分字段都在更新字典中”时触发，
          以避免更新单个组分时无法判断总和是否合理的问题。
    """
    if rules is None:
        rules = GAS_MIXTURE_RULES

    errors = []

    for rule in rules:
        if rule.field not in record:
            continue
        value = record.get(rule.field)

        if rule.rule_type == 'range':
            if value is not None and str(value).strip() != '':
                if not validate_range(value, rule.params.get('min'), rule.params.get('max')):
                    errors.append(f"第{rule.field}列: {rule.error_message}")

        elif rule.rule_type == 'type':
            if value is not None:
                if not validate_type(value, rule.params.get('type', 'str')):
                    errors.append(f"第{rule.field}列: {rule.error_message}")

        elif rule.rule_type == 'pattern':
            if value is not None:
                if not validate_pattern(value, rule.params.get('pattern', '.*')):
                    errors.append(f"第{rule.field}列: {rule.error_message}")

    # 仅当全部组分都在更新字段中时才做总和校验
    comp_fields = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
    if all(field in record for field in comp_fields):
        try:
            mole_fractions = [float(record.get(f) or 0) for f in comp_fields]
            total = sum(mole_fractions)
            if total == 0:
                errors.append("摩尔分数不能全部为 0")
            elif abs(total - 1.0) > SUM_HARD_TOLERANCE:
                errors.append(f"摩尔分数之和为 {total:.4f}，应接近 1.0")
        except (ValueError, TypeError):
            pass

    return len(errors) == 0, errors


def validate_batch(records: List[Dict[str, Any]], rules: List[ValidationRule] = None) -> Dict:
    """
    批量校验记录
    返回: {
        'valid': True/False,
        'total': 总数,
        'valid_count': 有效数,
        'invalid_count': 无效数,
        'errors': [(行号, 错误列表), ...]
    }

    Args:
        records: 记录列表
        rules: 校验规则列表；不传则使用默认 `GAS_MIXTURE_RULES`

    Returns:
        汇总结果字典（错误最多返回 50 条，避免响应过大）。
    """
    if rules is None:
        rules = GAS_MIXTURE_RULES
    
    errors = []
    valid_count = 0
    
    for idx, record in enumerate(records):
        is_valid, record_errors = validate_record(record, rules)
        if is_valid:
            valid_count += 1
        else:
            errors.append({
                'row': idx + 1,  # 从1开始计数
                'errors': record_errors
            })
    
    return {
        'valid': len(errors) == 0,
        'total': len(records),
        'valid_count': valid_count,
        'invalid_count': len(errors),
        'errors': errors[:50]  # 最多返回50条错误
    }


def get_soft_warnings(record: Dict[str, Any], pressure_threshold: float = PRESSURE_SOFT_MAX) -> List[str]:
    """
    生成“软性提示”（不阻止保存/写入）。

    Args:
        record: 单条记录字典
        pressure_threshold: 压力软阈值（默认 `PRESSURE_SOFT_MAX`）

    Returns:
        软提示文本列表。

    Notes:
        当前软提示包括：
        - 压力高于阈值（可能为异常值）
        - 组分总和与 1.0 的偏差处于“软阈值-硬阈值”之间（提醒检查）
    """
    warnings = []
    try:
        pressure = record.get('pressure')
        if pressure is not None and float(pressure) > pressure_threshold:
            warnings.append(
                f"压力 {float(pressure):.3f} MPa 高于 {pressure_threshold:.0f} MPa，可能为异常值"
            )
    except (ValueError, TypeError):
        pass

    # 组分和提示
    comp_fields = ['x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10']
    try:
        mole_fractions = [float(record.get(f) or 0) for f in comp_fields]
        total = sum(mole_fractions)
        if total > 0 and SUM_SOFT_TOLERANCE < abs(total - 1.0) <= SUM_HARD_TOLERANCE:
            warnings.append(f"摩尔分数之和为 {total:.4f}，与 1.0 偏差较大")
    except (ValueError, TypeError):
        pass

    return warnings


def count_soft_warnings(records: List[Dict[str, Any]], pressure_threshold: float = PRESSURE_SOFT_MAX) -> int:
    """
    统计记录列表中触发“压力软提示”的条数。

    Args:
        records: 记录列表
        pressure_threshold: 压力软阈值

    Returns:
        触发压力软提示的记录数量。
    """
    count = 0
    for record in records:
        if not record:
            continue
        try:
            pressure = record.get('pressure')
            if pressure is not None and float(pressure) > pressure_threshold:
                count += 1
        except (ValueError, TypeError):
            continue
    return count


# ==================== 数据清洗 ====================

def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    清洗单条记录
    - 转换数据类型
    - 填充默认值
    - 去除空白

    Args:
        record: 原始输入记录（可能包含字符串、None、空白等）

    Returns:
        清洗后的记录（所有数值字段转换为 float；缺失/无效填 0.0）。
    """
    cleaned = {}
    
    float_fields = [
        'temperature', 'pressure',
        'x_ch4', 'x_c2h6', 'x_c3h8', 'x_co2', 'x_n2', 'x_h2s', 'x_ic4h10'
    ]
    
    for field in float_fields:
        value = record.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ''):
            cleaned[field] = 0.0
        else:
            try:
                cleaned[field] = float(value)
            except (ValueError, TypeError):
                cleaned[field] = 0.0
    
    return cleaned


def clean_batch(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量清洗记录（逐条调用 `clean_record`）。

    Args:
        records: 原始记录列表

    Returns:
        清洗后的记录列表。
    """
    return [clean_record(r) for r in records]


# ==================== 校验规则管理 ====================

def get_validation_rules() -> List[Dict]:
    """
    获取当前校验规则（用于前端展示/动态表单）。

    Returns:
        规则列表（dict 形式），包含 field/type/params/message 等字段。
    """
    return [
        {
            'field': rule.field,
            'type': rule.rule_type,
            'params': rule.params,
            'message': rule.error_message
        }
        for rule in GAS_MIXTURE_RULES
    ]


def get_field_constraints() -> Dict[str, Dict]:
    """
    获取字段约束（用于前端表单验证/输入组件配置）。

    Returns:
        字段约束字典：key 为字段名，value 为类型、范围、单位、展示标签等。
    """
    return {
        'temperature': {
            'type': 'number',
            'required': True,
            'min': 100,
            'max': 1000,
            'unit': 'K',
            'label': '温度'
        },
        'pressure': {
            'type': 'number',
            'required': True,
            'min': 0,
            'max': 10000,
            'unit': 'MPa',
            'label': '压力'
        },
        'x_ch4': {
            'type': 'number',
            'required': False,
            'min': 0,
            'max': 1,
            'label': 'CH₄ 摩尔分数'
        },
        'x_c2h6': {
            'type': 'number',
            'required': False,
            'min': 0,
            'max': 1,
            'label': 'C₂H₆ 摩尔分数'
        },
        'x_c3h8': {
            'type': 'number',
            'required': False,
            'min': 0,
            'max': 1,
            'label': 'C₃H₈ 摩尔分数'
        },
        'x_co2': {
            'type': 'number',
            'required': False,
            'min': 0,
            'max': 1,
            'label': 'CO₂ 摩尔分数'
        },
        'x_n2': {
            'type': 'number',
            'required': False,
            'min': 0,
            'max': 1,
            'label': 'N₂ 摩尔分数'
        },
        'x_h2s': {
            'type': 'number',
            'required': False,
            'min': 0,
            'max': 1,
            'label': 'H₂S 摩尔分数'
        },
        'x_ic4h10': {
            'type': 'number',
            'required': False,
            'min': 0,
            'max': 1,
            'label': 'i-C₄H₁₀ 摩尔分数'
        }
    }


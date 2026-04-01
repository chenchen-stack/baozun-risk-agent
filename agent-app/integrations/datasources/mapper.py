"""将外部 JSON / SQL 行映射为 agent.PROCUREMENT_DB 单条记录结构。"""

from __future__ import annotations

import re
from typing import Any


def _first(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


_PO_RE = re.compile(r"^PO-\d{4}-\d{3}$", re.I)


def _normalize_po(raw: Any) -> str | None:
    if raw is None:
        return None
    t = str(raw).strip().upper().replace(" ", "")
    if t.startswith("P0-"):
        t = "PO-" + t[3:]
    if _PO_RE.match(t):
        return t
    return None


def rest_item_to_po_record(item: dict[str, Any]) -> dict[str, Any] | None:
    """支持 snake_case 与常见 camelCase（与 OpenAPI 样例一致）。"""
    po = _normalize_po(_first(item, "po_number", "poNumber", "purchaseOrderNo", "purchase_order_no"))
    if not po:
        return None

    title = _first(item, "title", "projectTitle", "project_name") or ""
    category = _first(item, "category", "purchaseCategory") or "非经营性采购-其他"
    department = _first(item, "department", "deptName", "dept") or ""
    applicant = _first(item, "applicant", "applicantName", "createdBy") or ""
    supplier = _first(item, "supplier", "supplierName", "vendorName") or ""
    supplier_id = _first(item, "supplier_id", "supplierId", "vendorId") or ""
    amount = _first(item, "amount", "totalAmount", "poAmount")
    try:
        amount = int(float(amount)) if amount is not None else 0
    except (TypeError, ValueError):
        amount = 0
    apply_date = str(_first(item, "apply_date", "applyDate", "createdDate") or "")[:10]
    status = str(_first(item, "status", "orderStatus") or "未知")
    hpr = _first(item, "has_purchase_request", "hasPurchaseRequest", "prFlag")
    if isinstance(hpr, str):
        has_pr = hpr.strip() in ("1", "true", "True", "是", "Y", "yes")
    else:
        has_pr = bool(hpr) if hpr is not None else True
    pr_number = _first(item, "pr_number", "prNumber", "purchaseRequestNo")
    budget_code = _first(item, "budget_code", "budgetCode") or ""
    budget_total = _first(item, "budget_total", "budgetTotal", 0)
    budget_used = _first(item, "budget_used", "budgetUsed", 0)
    try:
        budget_total = int(float(budget_total)) if budget_total is not None else 0
    except (TypeError, ValueError):
        budget_total = 0
    try:
        budget_used = int(float(budget_used)) if budget_used is not None else 0
    except (TypeError, ValueError):
        budget_used = 0

    return {
        "po_number": po,
        "title": str(title),
        "category": str(category),
        "department": str(department),
        "applicant": str(applicant),
        "supplier": str(supplier),
        "supplier_id": str(supplier_id),
        "amount": amount,
        "apply_date": apply_date or "2026-01-01",
        "status": status,
        "has_purchase_request": has_pr,
        "pr_number": pr_number if pr_number else (f"PR-{po[3:]}" if has_pr else None),
        "budget_code": str(budget_code),
        "budget_total": budget_total,
        "budget_used": budget_used,
    }


def normalize_sql_row(row: dict[Any, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        nk = k.decode("utf-8") if isinstance(k, bytes) else str(k)
        if isinstance(v, bytes):
            out[nk] = v.decode("utf-8", errors="replace")
        else:
            out[nk] = v
    return out


def sql_row_to_po_record(row: dict[str, Any]) -> dict[str, Any] | None:
    """SQL 结果集一行 → 与 REST 相同结构。"""
    return rest_item_to_po_record(normalize_sql_row(row))

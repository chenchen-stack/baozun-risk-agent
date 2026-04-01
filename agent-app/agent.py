"""
宝尊电商风控AI Agent — LangChain Agent Core
Mock databases + LangChain tools + Agent loop + HTML report generator
"""

import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

# ════════════════════════════════════════════════════════════════
#  TAX RATE STANDARDS — Used for three-doc match & invoice check
# ════════════════════════════════════════════════════════════════

EXPECTED_TAX_RATES = {
    "门店装修": 0.09, "建筑装饰": 0.09, "IT设备": 0.13, "办公用品": 0.13,
    "办公家具": 0.13, "市场营销": 0.06, "印刷": 0.06, "广告": 0.06, "技术服务": 0.06,
}

# ════════════════════════════════════════════════════════════════
#  MOCK DATABASES — Simulating 3 disconnected systems
# ════════════════════════════════════════════════════════════════

PROCUREMENT_DB = {
    "PO-2026-001": {
        "po_number": "PO-2026-001", "title": "GAP南京西路旗舰店装修工程",
        "category": "非经营性采购-门店装修", "department": "BBM-GAP事业部",
        "applicant": "王磊", "supplier": "上海锦华装饰工程有限公司", "supplier_id": "SUP-001",
        "amount": 250000, "apply_date": "2026-01-15", "status": "已完成",
        "has_purchase_request": True, "pr_number": "PR-2026-001",
        "budget_code": "BBM-CAPEX-2026-Q1", "budget_total": 800000, "budget_used": 300000,
    },
    "PO-2026-002": {
        "po_number": "PO-2026-002", "title": "办公笔记本采购(联想ThinkPad T14s)",
        "category": "非经营性采购-IT设备", "department": "BEC-技术部",
        "applicant": "陈志远", "supplier": "上海联拓科技有限公司", "supplier_id": "SUP-002",
        "amount": 200000, "apply_date": "2026-01-20", "status": "已完成",
        "has_purchase_request": True, "pr_number": "PR-2026-002",
        "budget_code": "BEC-IT-2026-Q1", "budget_total": 500000, "budget_used": 200000,
    },
    "PO-2026-003": {
        "po_number": "PO-2026-003", "title": "GAP杭州万象城店装修工程",
        "category": "非经营性采购-门店装修", "department": "BBM-GAP事业部",
        "applicant": "王磊", "supplier": "杭州博雅建设有限公司", "supplier_id": "SUP-003",
        "amount": 580000, "apply_date": "2026-02-01", "status": "已完成",
        "has_purchase_request": True, "pr_number": "PR-2026-003",
        "budget_code": "BBM-CAPEX-2026-Q1", "budget_total": 800000, "budget_used": 580000,
    },
    "PO-2026-004": {
        "po_number": "PO-2026-004", "title": "市场部办公家具采购",
        "category": "非经营性采购-办公用品", "department": "BEC-市场部",
        "applicant": "刘佳", "supplier": "上海美宜家具有限公司", "supplier_id": "SUP-004",
        "amount": 32000, "apply_date": "2026-03-05", "status": "已付款",
        "has_purchase_request": False, "pr_number": None,
        "budget_code": "BEC-ADMIN-2026-Q1", "budget_total": 100000, "budget_used": 45000,
    },
    "PO-2026-005": {
        "po_number": "PO-2026-005", "title": "GAP成都太古里店装修工程",
        "category": "非经营性采购-门店装修", "department": "BBM-GAP事业部",
        "applicant": "王磊", "supplier": "成都锦华装饰工程有限公司", "supplier_id": "SUP-005",
        "amount": 980000, "apply_date": "2026-03-08", "status": "进行中",
        "has_purchase_request": True, "pr_number": "PR-2026-005",
        "budget_code": "BBM-CAPEX-2026-Q1", "budget_total": 2000000, "budget_used": 980000,
    },
    "PO-2026-006": {
        "po_number": "PO-2026-006", "title": "ThinkPad笔记本批量采购(第二批)",
        "category": "非经营性采购-IT设备", "department": "BEC-技术部",
        "applicant": "陈志远", "supplier": "上海联拓科技有限公司", "supplier_id": "SUP-002",
        "amount": 200000, "apply_date": "2026-03-10", "status": "已付款",
        "has_purchase_request": True, "pr_number": "PR-2026-006",
        "budget_code": "BEC-IT-2026-Q1", "budget_total": 500000, "budget_used": 400000,
    },
    "PO-2026-007": {
        "po_number": "PO-2026-007", "title": "HUNTER杭州旗舰店营销物料制作",
        "category": "非经营性采购-市场营销", "department": "BBM-HUNTER事业部",
        "applicant": "赵敏", "supplier": "杭州创意印务有限公司", "supplier_id": "SUP-006",
        "amount": 85000, "apply_date": "2026-03-22", "status": "待审批",
        "has_purchase_request": True, "pr_number": "PR-2026-007",
        "budget_code": "BBM-MKT-2026-Q1", "budget_total": 200000, "budget_used": 120000,
    },
    "PO-2026-008": {
        "po_number": "PO-2026-008", "title": "GAP北京三里屯店翻新工程",
        "category": "非经营性采购-门店装修", "department": "BBM-GAP事业部",
        "applicant": "王磊", "supplier": "北京恒达建设有限公司", "supplier_id": "SUP-007",
        "amount": 1200000, "apply_date": "2026-03-18", "status": "待审批",
        "has_purchase_request": True, "pr_number": "PR-2026-008",
        "budget_code": "BBM-CAPEX-2026-Q2", "budget_total": 3000000, "budget_used": 0,
    },
    "PO-2026-088": {
        "po_number": "PO-2026-088", "title": "演示用·四流不一致样例（合同主体≠收款方）",
        "category": "非经营性采购-演示", "department": "BEC-市场部",
        "applicant": "刘佳", "supplier": "上海甲方科技有限公司", "supplier_id": "SUP-DEMO-A",
        "amount": 50000, "apply_date": "2026-03-20", "status": "已付款",
        "has_purchase_request": True, "pr_number": "PR-2026-088",
        "budget_code": "BEC-ADMIN-2026-Q1", "budget_total": 100000, "budget_used": 50000,
    },
}

CONTRACT_DB = {
    "SC-2026-001": {
        "contract_number": "SC-2026-001", "title": "GAP南京西路旗舰店装修工程合同",
        "po_number": "PO-2026-001", "contract_type": "非经营性采购-门店装修",
        "supplier": "上海锦华装饰工程有限公司", "supplier_id": "SUP-001",
        "amount": 250000, "sign_date": "2026-01-20", "status": "已履行",
        "approval_flow": "部门经理→财务总监→法务", "correct_type": True,
    },
    "SC-2026-002": {
        "contract_number": "SC-2026-002", "title": "联想ThinkPad T14s笔记本采购合同",
        "po_number": "PO-2026-002", "contract_type": "非经营性采购-IT设备",
        "supplier": "上海联拓科技有限公司", "supplier_id": "SUP-002",
        "amount": 200000, "sign_date": "2026-01-25", "status": "已履行",
        "approval_flow": "部门经理→财务总监", "correct_type": True,
    },
    "SC-2026-003": {
        "contract_number": "SC-2026-003", "title": "GAP杭州万象城店装修工程合同",
        "po_number": "PO-2026-003", "contract_type": "非经营性采购-门店装修",
        "supplier": "杭州博雅建设有限公司", "supplier_id": "SUP-003",
        "amount": 580000, "sign_date": "2026-02-05", "status": "已履行",
        "approval_flow": "部门经理→财务总监→CFO→法务", "correct_type": True,
    },
    "SC-2026-004": {
        "contract_number": "SC-2026-004", "title": "办公家具采购合同",
        "po_number": "PO-2026-004", "contract_type": "经营性采购-日常办公",
        "supplier": "上海美宜家具有限公司", "supplier_id": "SUP-004",
        "amount": 35000, "sign_date": "2026-03-06", "status": "已签署",
        "approval_flow": "部门经理", "correct_type": False,
    },
    "SC-2026-005": {
        "contract_number": "SC-2026-005", "title": "GAP成都太古里店装修工程合同",
        "po_number": "PO-2026-005", "contract_type": "经营性采购-门店运营",
        "supplier": "成都锦华装饰工程有限公司", "supplier_id": "SUP-005",
        "amount": 980000, "sign_date": "2026-03-12", "status": "审批中",
        "approval_flow": "部门经理→财务总监", "correct_type": False,
    },
    "SC-2026-006": {
        "contract_number": "SC-2026-006", "title": "ThinkPad笔记本批量采购合同(第二批)",
        "po_number": "PO-2026-006", "contract_type": "非经营性采购-IT设备",
        "supplier": "上海联拓科技有限公司", "supplier_id": "SUP-002",
        "amount": 200000, "sign_date": "2026-03-12", "status": "已签署",
        "approval_flow": "部门经理→财务总监", "correct_type": True,
    },
    "SC-2026-007": {
        "contract_number": "SC-2026-007", "title": "HUNTER杭州营销物料制作合同",
        "po_number": "PO-2026-007", "contract_type": "非经营性采购-市场营销",
        "supplier": "杭州创意印务有限公司", "supplier_id": "SUP-006",
        "amount": 85000, "sign_date": "2026-03-25", "status": "待签署",
        "approval_flow": "部门经理→财务总监", "correct_type": True,
    },
    "SC-2026-088": {
        "contract_number": "SC-2026-088", "title": "演示合同·签约主体A",
        "po_number": "PO-2026-088", "contract_type": "非经营性采购-演示",
        "supplier": "上海甲方科技有限公司", "supplier_id": "SUP-DEMO-A",
        "amount": 50000, "sign_date": "2026-03-21", "status": "已签署",
        "approval_flow": "部门经理→财务总监", "correct_type": True,
    },
}

ACCEPTANCE_DB = {
    "ACC-2026-001": {"po_number": "PO-2026-001", "date": "2026-02-28", "acceptor": "张建国", "acceptor_dept": "BBM-GAP事业部",
                      "result": "验收通过", "qty_received": 1, "qty_ordered": 1},
    "ACC-2026-002": {"po_number": "PO-2026-002", "date": "2026-02-15", "acceptor": "李涛", "acceptor_dept": "BEC-技术部",
                      "result": "验收通过", "qty_received": 20, "qty_ordered": 20},
    "ACC-2026-003": {"po_number": "PO-2026-003", "date": "2026-03-20", "acceptor": "张建国", "acceptor_dept": "BBM-GAP事业部",
                      "result": "验收通过", "qty_received": 1, "qty_ordered": 1},
    "ACC-2026-004": {"po_number": "PO-2026-004", "date": "2026-03-10", "acceptor": "刘佳", "acceptor_dept": "BEC-市场部",
                      "result": "验收通过", "qty_received": 15, "qty_ordered": 15},
    "ACC-2026-006": {"po_number": "PO-2026-006", "date": "2026-03-18", "acceptor": "李涛", "acceptor_dept": "BEC-技术部",
                      "result": "验收通过", "qty_received": 20, "qty_ordered": 20},
    "ACC-2026-088": {"po_number": "PO-2026-088", "date": "2026-03-22", "acceptor": "刘佳", "acceptor_dept": "BEC-市场部",
                      "result": "验收通过", "qty_received": 100, "qty_ordered": 100,
                      "shipper_name": "杭州乙方商贸有限公司"},
}

INVOICE_DB = {
    "INV-2026-001": {"invoice_number": "INV-2026-001", "invoice_code": "3100232130", "invoice_no": "08956781",
                      "po_number": "PO-2026-001", "contract_number": "SC-2026-001", "supplier": "上海锦华装饰工程有限公司",
                      "supplier_tax_id": "91310000MA1FL8XQ3K", "buyer_tax_id": "91310000XXXBZ001",
                      "amount": 250000, "tax_rate": 0.09, "tax_amount": 22500, "total_with_tax": 272500,
                      "issue_date": "2026-03-01", "verified": True, "is_valid": True, "consecutive_flag": False},
    "INV-2026-002": {"invoice_number": "INV-2026-002", "invoice_code": "3100232130", "invoice_no": "08956782",
                      "po_number": "PO-2026-002", "contract_number": "SC-2026-002", "supplier": "上海联拓科技有限公司",
                      "supplier_tax_id": "91310000MA1GT9PQ5L", "buyer_tax_id": "91310000XXXBZ001",
                      "amount": 200000, "tax_rate": 0.13, "tax_amount": 26000, "total_with_tax": 226000,
                      "issue_date": "2026-02-20", "verified": True, "is_valid": True, "consecutive_flag": True},
    "INV-2026-003": {"invoice_number": "INV-2026-003", "invoice_code": "3300232145", "invoice_no": "12345678",
                      "po_number": "PO-2026-003", "contract_number": "SC-2026-003", "supplier": "杭州博雅建设有限公司",
                      "supplier_tax_id": "91330000MA1HK2RQ7N", "buyer_tax_id": "91310000XXXBZ001",
                      "amount": 580000, "tax_rate": 0.09, "tax_amount": 52200, "total_with_tax": 632200,
                      "issue_date": "2026-03-25", "verified": True, "is_valid": True, "consecutive_flag": False},
    "INV-2026-004": {"invoice_number": "INV-2026-004", "invoice_code": "3100232130", "invoice_no": "08956783",
                      "po_number": "PO-2026-004", "contract_number": "SC-2026-004", "supplier": "上海美宜家具有限公司",
                      "supplier_tax_id": "91310000MA1JN3SQ9P", "buyer_tax_id": "91310000XXXBZ001",
                      "amount": 35000, "tax_rate": 0.13, "tax_amount": 4550, "total_with_tax": 39550,
                      "issue_date": "2026-03-12", "verified": True, "is_valid": True, "consecutive_flag": True},
    "INV-2026-006": {"invoice_number": "INV-2026-006", "invoice_code": "3100232130", "invoice_no": "08956784",
                      "po_number": "PO-2026-006", "contract_number": "SC-2026-006", "supplier": "上海联拓科技有限公司",
                      "supplier_tax_id": "91310000MA1GT9PQ5L", "buyer_tax_id": "91310000XXXBZ001",
                      "amount": 200000, "tax_rate": 0.13, "tax_amount": 26000, "total_with_tax": 226000,
                      "issue_date": "2026-03-15", "verified": True, "is_valid": True, "consecutive_flag": True},
    "INV-2026-007": {"invoice_number": "INV-2026-007", "invoice_code": "3300232150", "invoice_no": "00112233",
                      "po_number": "PO-2026-007", "contract_number": "SC-2026-007", "supplier": "杭州创意印务有限公司",
                      "supplier_tax_id": "91330000MA1LQ5UQ3T", "buyer_tax_id": "91310000XXXBZ001",
                      "amount": 88500, "tax_rate": 0.06, "tax_amount": 5310, "total_with_tax": 93810,
                      "issue_date": "2026-03-28", "verified": False, "is_valid": False, "consecutive_flag": False},
    "INV-2026-088": {"invoice_number": "INV-2026-088", "invoice_code": "3100232199", "invoice_no": "09998877",
                      "po_number": "PO-2026-088", "contract_number": "SC-2026-088", "supplier": "杭州乙方商贸有限公司",
                      "supplier_tax_id": "91330000MA9DEMO02B", "buyer_tax_id": "91310000XXXBZ001",
                      "amount": 50000, "tax_rate": 0.13, "tax_amount": 6500, "total_with_tax": 56500,
                      "issue_date": "2026-03-23", "verified": True, "is_valid": True, "consecutive_flag": False},
}

PAYMENT_DB = {
    "PAY-2026-001": {"payment_number": "PAY-2026-001", "contract_number": "SC-2026-001", "po_number": "PO-2026-001", "desc": "GAP南京西路店装修尾款", "amount": 250000, "payee": "上海锦华装饰工程有限公司", "applicant": "王磊", "apply_date": "2026-03-05", "pay_date": "2026-03-08", "status": "已付"},
    "PAY-2026-002": {"payment_number": "PAY-2026-002", "contract_number": "SC-2026-002", "po_number": "PO-2026-002", "desc": "ThinkPad笔记本全款", "amount": 200000, "payee": "上海联拓科技有限公司", "applicant": "陈志远", "apply_date": "2026-02-20", "pay_date": "2026-02-25", "status": "已付"},
    "PAY-2026-003": {"payment_number": "PAY-2026-003", "contract_number": "SC-2026-003", "po_number": "PO-2026-003", "desc": "GAP杭州店装修尾款", "amount": 580000, "payee": "杭州博雅建设有限公司", "applicant": "王磊", "apply_date": "2026-03-22", "pay_date": "2026-03-25", "status": "已付"},
    "PAY-2026-004": {"payment_number": "PAY-2026-004", "contract_number": "SC-2026-004", "po_number": "PO-2026-004", "desc": "办公家具全款", "amount": 35000, "payee": "上海美宜家具有限公司", "applicant": "刘佳", "apply_date": "2026-03-12", "pay_date": "2026-03-15", "status": "已付"},
    "PAY-2026-005": {"payment_number": "PAY-2026-005", "contract_number": "SC-2026-005", "po_number": "PO-2026-005", "desc": "GAP成都太古里店装修首期款", "amount": 400000, "payee": "成都锦华装饰工程有限公司", "applicant": "王磊", "apply_date": "2026-03-20", "pay_date": None, "status": "待审批"},
    "PAY-2026-006": {"payment_number": "PAY-2026-006", "contract_number": "SC-2026-006", "po_number": "PO-2026-006", "desc": "ThinkPad笔记本(第二批)全款", "amount": 200000, "payee": "上海联拓科技有限公司", "applicant": "陈志远", "apply_date": "2026-03-16", "pay_date": "2026-03-18", "status": "已付"},
    "PAY-2026-007": {"payment_number": "PAY-2026-007", "contract_number": "SC-2026-006", "po_number": "PO-2026-006", "desc": "ThinkPad笔记本(第二批)全款", "amount": 200000, "payee": "上海联拓科技有限公司", "applicant": "张蕾", "apply_date": "2026-03-18", "pay_date": None, "status": "待审批"},
    "PAY-2026-008": {"payment_number": "PAY-2026-008", "contract_number": "SC-2026-007", "po_number": "PO-2026-007", "desc": "HUNTER杭州营销物料款", "amount": 85000, "payee": "杭州创意印务有限公司", "applicant": "赵敏", "apply_date": "2026-03-28", "pay_date": None, "status": "待审批"},
    "PAY-2026-088": {"payment_number": "PAY-2026-088", "contract_number": "SC-2026-088", "po_number": "PO-2026-088", "desc": "演示付款·收款方为乙方", "amount": 50000, "payee": "杭州乙方商贸有限公司", "applicant": "刘佳", "apply_date": "2026-03-24", "pay_date": "2026-03-25", "status": "已付"},
}

# ════════════════════════════════════════════════════════════════
#  WORK ORDER DATABASE (F12) — Exception tracking & resolution
# ════════════════════════════════════════════════════════════════

WORKORDER_DB = {
    "WO-2026-001": {
        "id": "WO-2026-001", "po_number": "PO-2026-004",
        "type": "跳过采购申请", "priority": "high",
        "title": "市场部办公家具采购未提交采购申请",
        "assignee": "李明（风控专员）", "status": "open",
        "created": "2026-03-15 09:30", "due": "2026-03-20",
        "description": "PO-2026-004 未提交采购申请直接签署合同SC-2026-004，需追补采购申请流程",
    },
    "WO-2026-002": {
        "id": "WO-2026-002", "po_number": "PO-2026-005",
        "type": "合同类型错误+审批流异常", "priority": "high",
        "title": "GAP成都太古里店装修合同类型错误",
        "assignee": "王芳（风控主管）", "status": "in_progress",
        "created": "2026-03-18 14:20", "due": "2026-03-22",
        "description": "SC-2026-005 合同类型标记为'经营性采购-门店运营'，应为'非经营性采购-门店装修'，98万合同缺少CFO和法务审批",
    },
    "WO-2026-003": {
        "id": "WO-2026-003", "po_number": "PO-2026-006",
        "type": "疑似重复付款+超合同金额", "priority": "high",
        "title": "ThinkPad笔记本第二批疑似重复付款",
        "assignee": "张强（风控专员）", "status": "open",
        "created": "2026-03-19 10:15", "due": "2026-03-21",
        "description": "PAY-2026-006和PAY-2026-007金额相同(¥200,000)，收款方相同但发起人不同(陈志远vs张蕾)，且审批后将超合同金额",
    },
    "WO-2026-088": {
        "id": "WO-2026-088", "po_number": "PO-2026-088",
        "type": "四流不一致·合同主体与收款方不符", "priority": "high",
        "title": "演示样例：合同签约上海甲方，付款至杭州乙方",
        "assignee": "风控专员", "status": "open",
        "created": "2026-03-25 09:00", "due": "2026-03-28",
        "description": "合同供方为上海甲方科技有限公司，已付记录收款方为杭州乙方商贸有限公司，需核实是否供应商变更或账户风险，建议冻结待复核",
    },
}
_wo_counter = [3]

# ════════════════════════════════════════════════════════════════
#  NOTIFICATION LOG (F13) — Feishu/OA push history
# ════════════════════════════════════════════════════════════════

NOTIFICATION_LOG = [
    {"id": "N-001", "time": "2026-03-15 09:31", "channel": "飞书", "recipient": "李明", "type": "工单创建", "content": "WO-2026-001: 市场部办公家具采购未提交采购申请", "status": "已送达"},
    {"id": "N-002", "time": "2026-03-15 09:31", "channel": "飞书", "recipient": "风控负责人", "type": "高风险预警", "content": "PO-2026-004 跳过采购申请直接签署合同，已创建工单WO-2026-001", "status": "已送达"},
    {"id": "N-003", "time": "2026-03-18 14:21", "channel": "飞书", "recipient": "王芳", "type": "工单创建", "content": "WO-2026-002: GAP成都太古里店装修合同类型错误", "status": "已送达"},
    {"id": "N-004", "time": "2026-03-19 10:16", "channel": "飞书", "recipient": "张强", "type": "工单创建", "content": "WO-2026-003: ThinkPad笔记本第二批疑似重复付款", "status": "已送达"},
    {"id": "N-005", "time": "2026-03-19 10:16", "channel": "飞书", "recipient": "风控负责人", "type": "高风险预警", "content": "PO-2026-006 疑似重复付款，金额¥200,000×2，已创建工单WO-2026-003", "status": "已送达"},
]
_notif_counter = [5]

# ════════════════════════════════════════════════════════════════
#  SUPPLIER DATABASE — Supplier profiles & risk (场景5)
# ════════════════════════════════════════════════════════════════

SUPPLIER_DB = {
    "SUP-001": {"id": "SUP-001", "name": "上海锦华装饰工程有限公司", "reg_date": "2015-03-20", "reg_capital": 5000000,
                "business_scope": "建筑装饰装修工程设计与施工", "credit_score": 85, "total_contracts": 3, "total_amount": 850000,
                "win_rate": 0.67, "bid_count": 6, "related_suppliers": [], "risk_level": "low",
                "last_audit": "2025-12-01", "status": "正常", "contacts": "张经理 138-0000-0001",
                "tax_id": "91310000MA1FL8XQ3K", "bank_account": "工商银行 6222-0000-0000-0001"},
    "SUP-002": {"id": "SUP-002", "name": "上海联拓科技有限公司", "reg_date": "2018-06-15", "reg_capital": 2000000,
                "business_scope": "计算机软硬件销售与技术服务", "credit_score": 78, "total_contracts": 4, "total_amount": 600000,
                "win_rate": 0.80, "bid_count": 5, "related_suppliers": [], "risk_level": "medium",
                "last_audit": "2025-09-15", "status": "正常", "contacts": "李经理 139-0000-0002",
                "tax_id": "91310000MA1GT9PQ5L", "bank_account": "建设银行 6227-0000-0000-0002"},
    "SUP-003": {"id": "SUP-003", "name": "杭州博雅建设有限公司", "reg_date": "2012-09-10", "reg_capital": 10000000,
                "business_scope": "建筑装饰装修工程、市政工程", "credit_score": 92, "total_contracts": 2, "total_amount": 580000,
                "win_rate": 0.50, "bid_count": 4, "related_suppliers": [], "risk_level": "low",
                "last_audit": "2025-11-20", "status": "正常", "contacts": "赵经理 137-0000-0003",
                "tax_id": "91330000MA1HK2RQ7N", "bank_account": "农业银行 6228-0000-0000-0003"},
    "SUP-004": {"id": "SUP-004", "name": "上海美宜家具有限公司", "reg_date": "2020-01-08", "reg_capital": 1000000,
                "business_scope": "家具销售、办公用品", "credit_score": 65, "total_contracts": 1, "total_amount": 35000,
                "win_rate": 1.00, "bid_count": 1, "related_suppliers": ["SUP-008"], "risk_level": "medium",
                "last_audit": "2025-06-01", "status": "正常", "contacts": "周经理 136-0000-0004",
                "tax_id": "91310000MA1JN3SQ9P", "bank_account": "招商银行 6225-0000-0000-0004"},
    "SUP-005": {"id": "SUP-005", "name": "成都锦华装饰工程有限公司", "reg_date": "2016-11-25", "reg_capital": 8000000,
                "business_scope": "建筑装饰装修工程", "credit_score": 82, "total_contracts": 1, "total_amount": 980000,
                "win_rate": 0.33, "bid_count": 3, "related_suppliers": ["SUP-001"], "risk_level": "medium",
                "last_audit": "2025-10-10", "status": "正常", "contacts": "吴经理 135-0000-0005",
                "tax_id": "91510000MA1KP4TQ1R", "bank_account": "中国银行 6217-0000-0000-0005"},
    "SUP-006": {"id": "SUP-006", "name": "杭州创意印务有限公司", "reg_date": "2019-04-12", "reg_capital": 500000,
                "business_scope": "印刷、广告设计制作", "credit_score": 72, "total_contracts": 1, "total_amount": 85000,
                "win_rate": 1.00, "bid_count": 1, "related_suppliers": [], "risk_level": "low",
                "last_audit": "2025-08-20", "status": "正常", "contacts": "郑经理 134-0000-0006",
                "tax_id": "91330000MA1LQ5UQ3T", "bank_account": "工商银行 6222-0000-0000-0006"},
    "SUP-007": {"id": "SUP-007", "name": "北京恒达建设有限公司", "reg_date": "2010-07-01", "reg_capital": 20000000,
                "business_scope": "建筑工程施工、装饰装修", "credit_score": 90, "total_contracts": 0, "total_amount": 0,
                "win_rate": 0, "bid_count": 1, "related_suppliers": [], "risk_level": "low",
                "last_audit": "2025-12-15", "status": "正常", "contacts": "陈经理 133-0000-0007",
                "tax_id": "91110000MA1MR6VQ5V", "bank_account": "交通银行 6222-0000-0000-0007"},
    "SUP-008": {"id": "SUP-008", "name": "上海美宜办公用品有限公司", "reg_date": "2020-03-15", "reg_capital": 500000,
                "business_scope": "办公用品销售", "credit_score": 55, "total_contracts": 0, "total_amount": 0,
                "win_rate": 0, "bid_count": 2, "related_suppliers": ["SUP-004"], "risk_level": "high",
                "last_audit": None, "status": "待审核", "contacts": "周小明 136-0000-0008",
                "tax_id": "91310000MA1NS7WQ7X", "bank_account": "招商银行 6225-0000-0000-0008"},
}

# ════════════════════════════════════════════════════════════════
#  BUDGET DATABASE — Budget management (阶段❶)
# ════════════════════════════════════════════════════════════════

BUDGET_DB = {
    "BBM-CAPEX-2026-Q1": {"code": "BBM-CAPEX-2026-Q1", "dept": "BBM-GAP事业部", "category": "资本性支出-门店装修",
                           "annual_budget": 5000000, "q_budget": 2000000, "used": 1810000, "frozen": 400000,
                           "available": -210000, "po_list": ["PO-2026-001", "PO-2026-003", "PO-2026-005", "PO-2026-008"]},
    "BBM-CAPEX-2026-Q2": {"code": "BBM-CAPEX-2026-Q2", "dept": "BBM-GAP事业部", "category": "资本性支出-门店装修",
                           "annual_budget": 5000000, "q_budget": 3000000, "used": 0, "frozen": 1200000,
                           "available": 1800000, "po_list": ["PO-2026-008"]},
    "BEC-IT-2026-Q1": {"code": "BEC-IT-2026-Q1", "dept": "BEC-技术部", "category": "IT设备采购",
                        "annual_budget": 1000000, "q_budget": 500000, "used": 400000, "frozen": 0,
                        "available": 100000, "po_list": ["PO-2026-002", "PO-2026-006"]},
    "BEC-ADMIN-2026-Q1": {"code": "BEC-ADMIN-2026-Q1", "dept": "BEC-市场部", "category": "行政办公",
                           "annual_budget": 200000, "q_budget": 100000, "used": 45000, "frozen": 0,
                           "available": 55000, "po_list": ["PO-2026-004"]},
    "BBM-MKT-2026-Q1": {"code": "BBM-MKT-2026-Q1", "dept": "BBM-HUNTER事业部", "category": "市场营销",
                          "annual_budget": 500000, "q_budget": 200000, "used": 120000, "frozen": 85000,
                          "available": -5000, "po_list": ["PO-2026-007"]},
}

# ════════════════════════════════════════════════════════════════
#  DELIVERY DATABASE — Order tracking (阶段❺)
# ════════════════════════════════════════════════════════════════

DELIVERY_DB = {
    "PO-2026-001": {"po_number": "PO-2026-001", "expected_date": "2026-02-25", "actual_date": "2026-02-28",
                     "status": "已交付", "delay_days": 3, "penalty_applicable": False, "delivery_note": "DN-2026-001"},
    "PO-2026-002": {"po_number": "PO-2026-002", "expected_date": "2026-02-10", "actual_date": "2026-02-10",
                     "status": "已交付", "delay_days": 0, "penalty_applicable": False, "delivery_note": "DN-2026-002"},
    "PO-2026-003": {"po_number": "PO-2026-003", "expected_date": "2026-03-15", "actual_date": "2026-03-20",
                     "status": "已交付", "delay_days": 5, "penalty_applicable": True, "delivery_note": "DN-2026-003"},
    "PO-2026-004": {"po_number": "PO-2026-004", "expected_date": "2026-03-08", "actual_date": "2026-03-10",
                     "status": "已交付", "delay_days": 2, "penalty_applicable": False, "delivery_note": "DN-2026-004"},
    "PO-2026-005": {"po_number": "PO-2026-005", "expected_date": "2026-04-30", "actual_date": None,
                     "status": "进行中", "delay_days": 0, "penalty_applicable": False, "delivery_note": None},
    "PO-2026-006": {"po_number": "PO-2026-006", "expected_date": "2026-03-15", "actual_date": "2026-03-15",
                     "status": "已交付", "delay_days": 0, "penalty_applicable": False, "delivery_note": "DN-2026-006"},
    "PO-2026-007": {"po_number": "PO-2026-007", "expected_date": "2026-04-15", "actual_date": None,
                     "status": "待交付", "delay_days": 0, "penalty_applicable": False, "delivery_note": None},
    "PO-2026-008": {"po_number": "PO-2026-008", "expected_date": "2026-06-30", "actual_date": None,
                     "status": "待下单", "delay_days": 0, "penalty_applicable": False, "delivery_note": None},
    "PO-2026-088": {"po_number": "PO-2026-088", "expected_date": "2026-03-20", "actual_date": "2026-03-21",
                     "status": "已交付", "delay_days": 0, "penalty_applicable": False, "delivery_note": "DN-DEMO-088"},
}

# ════════════════════════════════════════════════════════════════
#  ASSET DATABASE — Fixed asset management (阶段❿)
# ════════════════════════════════════════════════════════════════

ASSET_DB = {
    "FA-2026-001": {"id": "FA-2026-001", "name": "GAP南京西路店装修", "po_number": "PO-2026-001",
                     "category": "长期待摊费用-门店装修", "original_value": 250000, "entry_date": "2026-03-01",
                     "depreciation_method": "直线法", "useful_life_months": 36, "monthly_depreciation": 6944,
                     "accumulated_depreciation": 6944, "net_value": 243056, "location": "上海南京西路旗舰店",
                     "custodian": "张建国（BBM-GAP事业部）", "status": "在用", "last_inventory": "2026-03-15",
                     "inventory_result": "账实一致"},
    "FA-2026-002": {"id": "FA-2026-002", "name": "联想ThinkPad T14s×20台", "po_number": "PO-2026-002",
                     "category": "固定资产-电子设备", "original_value": 200000, "entry_date": "2026-02-20",
                     "depreciation_method": "直线法", "useful_life_months": 36, "monthly_depreciation": 5556,
                     "accumulated_depreciation": 11112, "net_value": 188888, "location": "宝尊上海总部-技术部",
                     "custodian": "李涛（BEC-技术部）", "status": "在用", "last_inventory": "2026-03-15",
                     "inventory_result": "账实一致"},
    "FA-2026-003": {"id": "FA-2026-003", "name": "GAP杭州万象城店装修", "po_number": "PO-2026-003",
                     "category": "长期待摊费用-门店装修", "original_value": 580000, "entry_date": "2026-03-25",
                     "depreciation_method": "直线法", "useful_life_months": 36, "monthly_depreciation": 16111,
                     "accumulated_depreciation": 0, "net_value": 580000, "location": "杭州万象城GAP店",
                     "custodian": "张建国（BBM-GAP事业部）", "status": "在用", "last_inventory": None,
                     "inventory_result": "待盘点"},
}

# ════════════════════════════════════════════════════════════════
#  CONTRACT CLAUSE TEMPLATES — For contract review (场景4)
# ════════════════════════════════════════════════════════════════

CONTRACT_CLAUSE_STANDARDS = {
    "预付比例": {"threshold": 0.30, "rule": "预付款不超过合同总额的30%"},
    "验收条款": {"required": True, "rule": "必须明确验收标准和验收流程"},
    "违约条款": {"required": True, "rule": "必须包含对等违约责任条款"},
    "付款条件": {"rule": "付款条件应明确约定，收款账户必须为供应商对公账户"},
    "保密条款": {"required": True, "rule": "涉及宝尊品牌方信息的合同必须包含保密条款"},
}

CONTRACT_DETAILS_DB = {
    "SC-2026-001": {"prepay_ratio": 0.30, "has_acceptance_clause": True, "has_penalty_clause": True,
                     "has_confidential_clause": True, "payment_to_public_account": True, "penalty_symmetric": True},
    "SC-2026-002": {"prepay_ratio": 0, "has_acceptance_clause": True, "has_penalty_clause": True,
                     "has_confidential_clause": False, "payment_to_public_account": True, "penalty_symmetric": True},
    "SC-2026-003": {"prepay_ratio": 0.20, "has_acceptance_clause": True, "has_penalty_clause": True,
                     "has_confidential_clause": True, "payment_to_public_account": True, "penalty_symmetric": True},
    "SC-2026-004": {"prepay_ratio": 0, "has_acceptance_clause": False, "has_penalty_clause": False,
                     "has_confidential_clause": False, "payment_to_public_account": True, "penalty_symmetric": False},
    "SC-2026-005": {"prepay_ratio": 0.40, "has_acceptance_clause": True, "has_penalty_clause": True,
                     "has_confidential_clause": True, "payment_to_public_account": True, "penalty_symmetric": False},
    "SC-2026-006": {"prepay_ratio": 0, "has_acceptance_clause": True, "has_penalty_clause": True,
                     "has_confidential_clause": False, "payment_to_public_account": True, "penalty_symmetric": True},
    "SC-2026-007": {"prepay_ratio": 0.50, "has_acceptance_clause": True, "has_penalty_clause": False,
                     "has_confidential_clause": False, "payment_to_public_account": True, "penalty_symmetric": False},
}

# ════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════

def _find_contract_by_po(po_number):
    for c in CONTRACT_DB.values():
        if c["po_number"] == po_number:
            return c
    return None

def _find_payments_by_contract(contract_number):
    return [p for p in PAYMENT_DB.values() if p["contract_number"] == contract_number]

def _find_payments_by_po(po_number):
    return [p for p in PAYMENT_DB.values() if p["po_number"] == po_number]

def _find_acceptance_by_po(po_number):
    for a in ACCEPTANCE_DB.values():
        if a["po_number"] == po_number:
            return a
    return None

def _find_invoice_by_po(po_number):
    for i in INVOICE_DB.values():
        if i["po_number"] == po_number:
            return i
    return None

def _fmt(amount):
    return f"¥{amount:,.0f}"


def normalize_po_number(raw: str) -> str | None:
    """前端 / API 传入的 PO 号归一化为 PO-YYYY-NNN。"""
    t = (raw or "").strip().upper().replace(" ", "")
    if re.fullmatch(r"PO-\d{4}-\d{3}", t):
        return t
    return None


def _coerce_po_for_tool(raw: str) -> str | None:
    """模型常把字母 O 写成数字 0（如 P0-2026-002），在此纠正为 PO-。"""
    t = (raw or "").strip().upper().replace(" ", "")
    if t.startswith("P0-"):
        t = "PO-" + t[3:]
    if re.fullmatch(r"PO-\d{4}-\d{3}", t):
        return t
    return None


def _analyze_bid_rigging_for_po_row(po: dict) -> dict:
    """单条采购单的围标串标分析（供 detect_bid_rigging 与全量扫描复用）。"""
    pn = po["po_number"]
    supplier_id = po.get("supplier_id", "")
    supplier = SUPPLIER_DB.get(supplier_id)
    if not supplier:
        return {"po_number": pn, "supplier": None, "supplier_id": supplier_id, "alerts": ["未找到供应商信息"], "risk": "unknown"}
    alerts: list[str] = []
    if supplier["related_suppliers"]:
        for rs_id in supplier["related_suppliers"]:
            rs = SUPPLIER_DB.get(rs_id)
            if rs:
                alerts.append(
                    f"中标方 {supplier['name']} 与 {rs['name']}({rs_id}) 为关联企业（相似名称/相同法人/相同注册地址）"
                )
    if supplier["win_rate"] >= 0.8 and supplier["bid_count"] >= 3:
        alerts.append(f"中标率异常偏高: {supplier['win_rate'] * 100:.0f}%（{supplier['bid_count']}次投标）")
    same_bid = [
        s
        for s in SUPPLIER_DB.values()
        if s["id"] != supplier_id and any(r == supplier_id for r in s["related_suppliers"])
    ]
    for s in same_bid:
        alerts.append(f"供应商 {s['name']} 与中标方存在关联，可能参与陪标")
    risk = "high" if alerts else "low"
    return {
        "po_number": pn,
        "supplier": supplier["name"],
        "supplier_id": supplier_id,
        "bid_count": supplier["bid_count"],
        "win_rate": f"{supplier['win_rate'] * 100:.0f}%",
        "alerts": alerts if alerts else ["未发现围标串标风险"],
        "risk": risk,
    }


def build_po_trace(po_raw: str) -> dict | None:
    """采购溯源 POC：基于模拟库拼装全链路步骤、金额一致性、关联工单（供 /api/po-trace 与前端专用页）。"""
    po_key = normalize_po_number(po_raw)
    if not po_key:
        return None
    pr = PROCUREMENT_DB.get(po_key)
    if not pr:
        return None

    contract = None
    for c in CONTRACT_DB.values():
        if c.get("po_number") == po_key:
            contract = c
            break

    acc = next((a for a in ACCEPTANCE_DB.values() if a.get("po_number") == po_key), None)
    inv = _find_invoice_by_po(po_key)
    pays = [p for p in PAYMENT_DB.values() if p.get("po_number") == po_key]

    pr_ok = bool(pr.get("has_purchase_request"))

    if not inv:
        inv_state, inv_hint = "warn", "无发票记录"
    elif inv.get("verified"):
        inv_state, inv_hint = "ok", inv.get("invoice_number", "—")
    else:
        inv_state, inv_hint = "fail", f"{inv.get('invoice_number', '—')}（未验真）"

    paid_list = [p for p in pays if p.get("status") == "已付"]
    dup_pay = len(pays) >= 2 and len({p["amount"] for p in pays}) == 1
    four_flow_aligned = True
    four_flow_note = ""
    if contract and paid_list:
        c_sup = (contract.get("supplier") or "").strip()
        py0 = paid_list[0]
        payee = (py0.get("payee") or "").strip()
        if c_sup and payee and c_sup != payee:
            four_flow_aligned = False
            four_flow_note = (
                f"合同签约主体「{c_sup}」与已付款收款方「{payee}」不一致，请核实供应商变更或账户风险（演示：建议冻结待复核）"
            )
    if inv and contract and four_flow_aligned:
        isup = (inv.get("supplier") or "").strip()
        csup = (contract.get("supplier") or "").strip()
        if isup and csup and isup != csup:
            four_flow_aligned = False
            four_flow_note = (
                f"发票销售方「{isup}」与合同供方「{csup}」不一致，四流校验未通过（演示）"
            )

    if dup_pay:
        pay_state, pay_hint = "fail", "疑似重复付款链路"
    elif paid_list and not four_flow_aligned:
        pay_state, pay_hint = "fail", "四流不符·待冻结核实"
    elif paid_list:
        pay_state, pay_hint = "ok", paid_list[0].get("payment_number", "已付款")
    else:
        pay_state, pay_hint = "warn", "待付款/审批中"

    steps = [
        {"id": "pr", "label": "采购申请", "state": "ok" if pr_ok else "fail", "hint": pr.get("pr_number") or "未关联 PR"},
        {"id": "contract", "label": "合同", "state": "ok" if contract else "warn", "hint": contract["contract_number"] if contract else "未匹配合同"},
        {"id": "po", "label": "采购订单", "state": "ok", "hint": po_key},
        {"id": "accept", "label": "验收", "state": "ok" if acc else "warn", "hint": acc.get("result", "—") if acc else "无验收记录"},
        {"id": "invoice", "label": "发票", "state": inv_state, "hint": inv_hint},
        {"id": "payment", "label": "付款", "state": pay_state, "hint": pay_hint},
    ]

    ca = contract["amount"] if contract else None
    pa = pr.get("amount")
    ia = inv["amount"] if inv else None
    aligned = True
    if ca is not None and pa is not None and ca != pa:
        aligned = False
    if ia is not None and pa is not None and ia != pa:
        aligned = False
    if ca is not None and ia is not None and ca != ia:
        aligned = False

    qty_txt = "—"
    if acc:
        qty_txt = f"{acc.get('qty_received', '—')} / {acc.get('qty_ordered', '—')}"

    if aligned and (ca is not None or pa is not None):
        consistency_note = "合同、PO、发票金额一致" if (ca is not None and pa is not None and ia is not None) else "主要金额字段一致"
    elif not aligned:
        parts = []
        if ca is not None:
            parts.append(f"合同 {_fmt(ca)}")
        if pa is not None:
            parts.append(f"PO {_fmt(pa)}")
        if ia is not None:
            parts.append(f"发票 {_fmt(ia)}")
        consistency_note = "金额不一致：" + " vs ".join(parts) + "，需人工复核"
    else:
        consistency_note = "部分单据缺失，无法完成三单匹配"

    issues: list[str] = []
    if not pr_ok:
        issues.append("缺少前置采购申请")
    if not aligned:
        issues.append("三单金额不匹配")
    if dup_pay:
        issues.append("付款链路存在重复支付嫌疑")
    if inv and not inv.get("verified"):
        issues.append("发票未验真通过")
    if not four_flow_aligned and four_flow_note:
        issues.append("四流一致校验未通过")

    wo = next((w for w in WORKORDER_DB.values() if w.get("po_number") == po_key), None)
    blocked = bool(issues) or bool(wo)

    if not blocked:
        status, status_text = "released", "无异常，已自动放行"
    elif wo:
        status, status_text = "blocked", "存在异常，已关联工单待闭环"
    else:
        status, status_text = "blocked", "存在风险点，请人工复核"

    work_order = None
    if wo:
        work_order = {
            "id": wo["id"],
            "title": wo["title"],
            "anomaly_type": wo["type"],
            "detail": wo["description"],
            "priority": wo["priority"],
            "status": wo["status"],
        }
    elif blocked:
        work_order = {
            "id": "(演示)",
            "title": "系统建议关注",
            "anomaly_type": issues[0] if issues else "异常",
            "detail": "；".join(issues) if issues else "请通过 AI Agent 或工单模块进一步处置",
            "priority": "medium",
            "status": "待研判",
        }

    return {
        "po_number": po_key,
        "title": pr.get("title", ""),
        "department": pr.get("department", ""),
        "steps": steps,
        "consistency": {
            "contract_amount": ca,
            "po_amount": pa,
            "invoice_amount": ia,
            "accept_qty": qty_txt,
            "aligned": aligned,
            "note": consistency_note,
        },
        "four_flow": {"aligned": four_flow_aligned, "note": four_flow_note or "合同主体、收款方、发票销售方与物流信息一致（抽样演示）"},
        "status": status,
        "status_text": status_text,
        "work_order": work_order,
    }


# ════════════════════════════════════════════════════════════════
#  LANGCHAIN TOOLS
# ════════════════════════════════════════════════════════════════

@tool
def query_procurement_system(query: str) -> str:
    """查询采购系统。可以通过采购单号(PO-)、供应商名称、部门名称、或关键词搜索采购申请记录。"""
    results = []
    q = query.upper().strip()
    for po in PROCUREMENT_DB.values():
        if (q in po["po_number"].upper() or q in po["title"] or q in po["department"]
            or q in po["supplier"] or q in po.get("pr_number", "") or query in po["title"]
            or query in po["supplier"] or query in po["department"] or query in po["category"]):
            results.append(po)
    if not results:
        for po in PROCUREMENT_DB.values():
            for v in po.values():
                if isinstance(v, str) and query.lower() in v.lower():
                    results.append(po)
                    break
    if not results:
        return f"未找到与 '{query}' 相关的采购记录。可用的采购单号: {', '.join(PROCUREMENT_DB.keys())}"
    return json.dumps(results, ensure_ascii=False, indent=2)


@tool
def query_contract_system(query: str) -> str:
    """查询OA合同系统。可以通过合同号(SC-)、采购单号(PO-)、供应商名称搜索合同记录。"""
    results = []
    q = query.upper().strip()
    for c in CONTRACT_DB.values():
        if (q in c["contract_number"].upper() or q in c.get("po_number", "").upper()
            or query in c["supplier"] or query in c["title"]):
            results.append(c)
    if not results:
        for c in CONTRACT_DB.values():
            for v in c.values():
                if isinstance(v, str) and query.lower() in v.lower():
                    results.append(c)
                    break
    if not results:
        return f"未找到与 '{query}' 相关的合同记录。可用的合同号: {', '.join(CONTRACT_DB.keys())}"
    return json.dumps(results, ensure_ascii=False, indent=2)


@tool
def query_payment_system(query: str) -> str:
    """查询OA付款系统。可以通过付款单号(PAY-)、合同号(SC-)、采购单号(PO-)搜索付款记录。"""
    results = []
    q = query.upper().strip()
    for p in PAYMENT_DB.values():
        if (q in p["payment_number"].upper() or q in p.get("contract_number", "").upper()
            or q in p.get("po_number", "").upper() or query in p["payee"] or query in p["desc"]):
            results.append(p)
    if not results:
        return f"未找到与 '{query}' 相关的付款记录。可用的付款单号: {', '.join(PAYMENT_DB.keys())}"
    return json.dumps(results, ensure_ascii=False, indent=2)


@tool
def run_full_risk_check(po_number: str) -> str:
    """对指定采购单执行完整风控校验（10阶段全覆盖），包括：前序流程检查、合同类型校验、审批流校验、三单匹配、四流一致性、重复付款检测、超合同金额检测、验收人独立性、发票深度校验、交付进度、预算执行检查。
    参数 po_number 必须是采购单号，如 PO-2026-001。"""
    po = PROCUREMENT_DB.get(po_number)
    if not po:
        return f"采购单 {po_number} 不存在。可用: {', '.join(PROCUREMENT_DB.keys())}"

    contract = _find_contract_by_po(po_number)
    acceptance = _find_acceptance_by_po(po_number)
    invoice = _find_invoice_by_po(po_number)
    payments = _find_payments_by_po(po_number)

    checks = []

    # 1. Purchase Request
    if po["has_purchase_request"]:
        checks.append({"check": "前序流程(采购申请)", "result": "✅ 通过", "detail": f"采购申请编号 {po['pr_number']}"})
    else:
        checks.append({"check": "前序流程(采购申请)", "result": "❌ 未通过", "detail": "该采购未提交采购申请，直接进入合同签署环节，违反采购管理制度"})

    # 2. Contract type
    if contract:
        if contract["correct_type"]:
            checks.append({"check": "合同类型校验", "result": "✅ 通过", "detail": f"合同类型 '{contract['contract_type']}' 正确"})
        else:
            checks.append({"check": "合同类型校验", "result": "❌ 未通过",
                           "detail": f"合同类型 '{contract['contract_type']}' 错误，该采购属于 '{po['category']}'。"
                                     f"错误的合同类型导致审批流不正确：当前审批流为 '{contract['approval_flow']}'，"
                                     f"而金额 {_fmt(contract['amount'])} 的非经营性采购应走 '部门经理→财务总监→CFO→法务' 审批流"})
    else:
        checks.append({"check": "合同类型校验", "result": "⚠️ 待定", "detail": "暂无关联合同"})

    # 2.5 Approval flow validation (F08) — amount-based rules
    if contract:
        c_amt = contract["amount"]
        if c_amt >= 500000:
            expected_flow = "部门经理→财务总监→CFO→法务"
        elif c_amt >= 50000:
            expected_flow = "部门经理→财务总监"
        else:
            expected_flow = "部门经理"
        actual_flow = contract["approval_flow"]
        expected_steps = expected_flow.split("→")
        actual_steps = actual_flow.split("→")
        if all(s in actual_steps for s in expected_steps):
            checks.append({"check": "审批流校验(金额分级)", "result": "✅ 通过",
                           "detail": f"金额 {_fmt(c_amt)}，审批流 '{actual_flow}' 符合要求（最低要求 '{expected_flow}'）"})
        else:
            missing = [s for s in expected_steps if s not in actual_steps]
            checks.append({"check": "审批流校验(金额分级)", "result": "❌ 未通过",
                           "detail": f"金额 {_fmt(c_amt)} 应至少经过 '{expected_flow}' 审批，"
                                     f"实际为 '{actual_flow}'，缺少 {'、'.join(missing)} 审批环节"})

    # 3. Three-doc match (数量±2%, 单价±1%, 税率100%一致)
    if contract and invoice and acceptance:
        po_amt, inv_amt = po["amount"], invoice["amount"]
        price_diff = abs(po_amt - inv_amt) / po_amt * 100 if po_amt else 0
        qty_ordered = acceptance["qty_ordered"] or 1
        qty_diff = abs(acceptance["qty_received"] - qty_ordered) / qty_ordered * 100
        qty_ok = qty_diff <= 2
        contract_tax_rate = invoice.get("tax_rate", 0)
        expected_tax = None
        for k, v in EXPECTED_TAX_RATES.items():
            if k in po.get("category", "") or k in po.get("title", ""):
                expected_tax = v
                break
        tax_ok = expected_tax is None or abs(contract_tax_rate - expected_tax) < 0.001
        all_ok = price_diff <= 1 and qty_ok and tax_ok
        if all_ok:
            checks.append({"check": "三单匹配", "result": "✅ 通过",
                           "detail": f"采购金额 {_fmt(po_amt)}，发票金额 {_fmt(inv_amt)}，差异 {price_diff:.2f}% ≤ 1%；"
                                     f"验收数量 {acceptance['qty_received']}/{acceptance['qty_ordered']}（差异{qty_diff:.1f}% ≤ 2%）；"
                                     f"税率 {contract_tax_rate*100:.0f}% 一致"})
        else:
            detail_parts = []
            if price_diff > 1:
                detail_parts.append(f"金额差异 {price_diff:.2f}% > 1%（采购{_fmt(po_amt)} vs 发票{_fmt(inv_amt)}）")
            if not qty_ok:
                detail_parts.append(f"数量差异 {qty_diff:.1f}% > 2%（验收{acceptance['qty_received']}/{acceptance['qty_ordered']}）")
            if not tax_ok:
                detail_parts.append(f"税率不一致：发票 {contract_tax_rate*100:.0f}% vs 期望 {expected_tax*100:.0f}%")
            checks.append({"check": "三单匹配", "result": "❌ 未通过", "detail": "；".join(detail_parts)})
    else:
        missing = []
        if not contract: missing.append("合同")
        if not invoice: missing.append("发票")
        if not acceptance: missing.append("验收单")
        checks.append({"check": "三单匹配", "result": "⚠️ 数据不完整", "detail": f"缺少：{', '.join(missing)}"})

    # 4. Four-flow consistency
    if contract and invoice:
        supplier_match = (po["supplier"] == contract["supplier"] == invoice["supplier"])
        if payments:
            payee_match = all(p["payee"] == po["supplier"] for p in payments)
        else:
            payee_match = True
        if supplier_match and payee_match:
            checks.append({"check": "四流一致性", "result": "✅ 通过",
                           "detail": "合同主体、采购供应商、发票开具方、付款收款方完全一致"})
        else:
            checks.append({"check": "四流一致性", "result": "❌ 未通过",
                           "detail": f"主体不一致：采购供应商={po['supplier']}，合同方={contract['supplier']}，发票方={invoice['supplier']}"})
    else:
        checks.append({"check": "四流一致性", "result": "⚠️ 数据不完整", "detail": "缺少合同或发票信息"})

    # 4b 物流/发货方 vs 采购供应商（四流之货物流 — 与 V4.0 6.4 对齐的可执行版）
    if acceptance:
        shipper = (
            acceptance.get("shipper_name")
            or acceptance.get("logistics_shipper")
            or acceptance.get("delivery_party")
            or po["supplier"]
        )
        if shipper != po["supplier"]:
            checks.append({
                "check": "物流/发货方一致性",
                "result": "❌ 未通过",
                "detail": f"采购订单供应商={po['supplier']}，验收/物流记载发货方={shipper}",
            })
        else:
            checks.append({
                "check": "物流/发货方一致性",
                "result": "✅ 通过",
                "detail": f"发货方与采购供应商一致（{shipper}）",
            })

    # 5. Duplicate payment
    if payments and len(payments) > 1:
        seen = {}
        dup_found = False
        for p in payments:
            key = (p["payee"], p["amount"])
            if key in seen:
                checks.append({"check": "重复付款检测", "result": "❌ 发现疑似重复",
                               "detail": f"付款 {seen[key]} 和 {p['payment_number']} 金额相同({_fmt(p['amount'])}), "
                                         f"收款方相同({p['payee']}), 且发起人不同({PAYMENT_DB[seen[key]]['applicant']} vs {p['applicant']})"})
                dup_found = True
            seen[key] = p["payment_number"]
        if not dup_found:
            checks.append({"check": "重复付款检测", "result": "✅ 通过", "detail": "未发现重复付款"})
    elif payments:
        checks.append({"check": "重复付款检测", "result": "✅ 通过", "detail": "仅1笔付款记录，无重复风险"})
    else:
        checks.append({"check": "重复付款检测", "result": "ℹ️ 无付款记录", "detail": "暂无付款记录"})

    # 5.5 Over-contract payment check (F11)
    if contract and payments:
        total_paid = sum(p["amount"] for p in payments if p["status"] == "已付")
        total_pending = sum(p["amount"] for p in payments if p["status"] == "待审批")
        c_amt = contract["amount"]
        if total_paid > c_amt:
            checks.append({"check": "超合同金额检测", "result": "❌ 超额付款",
                           "detail": f"合同金额 {_fmt(c_amt)}，已付 {_fmt(total_paid)}，"
                                     f"超出 {_fmt(total_paid - c_amt)}（{(total_paid/c_amt-1)*100:.1f}%）"})
        elif total_paid + total_pending > c_amt:
            checks.append({"check": "超合同金额检测", "result": "⚠️ 待审批后将超额",
                           "detail": f"合同金额 {_fmt(c_amt)}，已付 {_fmt(total_paid)}，"
                                     f"待审批 {_fmt(total_pending)}，审批后总付款 {_fmt(total_paid + total_pending)} "
                                     f"将超出合同 {_fmt(total_paid + total_pending - c_amt)}"})
        else:
            checks.append({"check": "超合同金额检测", "result": "✅ 通过",
                           "detail": f"合同金额 {_fmt(c_amt)}，已付 {_fmt(total_paid)}，余额 {_fmt(c_amt - total_paid)}"})
    elif contract:
        checks.append({"check": "超合同金额检测", "result": "ℹ️ 无付款记录", "detail": "暂无付款记录"})

    # 6. Acceptor independence (阶段❻)
    if acceptance:
        if acceptance["acceptor"] == po["applicant"]:
            checks.append({"check": "验收人独立性", "result": "❌ 未通过",
                           "detail": f"采购申请人 {po['applicant']} 同时担任验收人，违反不相容职务分离原则"})
        else:
            checks.append({"check": "验收人独立性", "result": "✅ 通过",
                           "detail": f"申请人 {po['applicant']}，验收人 {acceptance['acceptor']}，满足独立性"})

    # 7. Invoice deep check (阶段❼)
    if invoice:
        inv_issues = []
        if not invoice.get("is_valid", True):
            inv_issues.append("验真失败（疑似虚开）")
        if not invoice.get("verified", True):
            inv_issues.append("未完成验证")
        if invoice.get("consecutive_flag"):
            inv_issues.append("存在连号发票风险")
        expected_rate = None
        for k, v in EXPECTED_TAX_RATES.items():
            if k in po.get("category", "") or k in po.get("title", ""):
                expected_rate = v
                break
        if expected_rate and abs(invoice["tax_rate"] - expected_rate) > 0.001:
            inv_issues.append(f"税率 {invoice['tax_rate']*100:.0f}% 与品类期望 {expected_rate*100:.0f}% 不符")
        if inv_issues:
            checks.append({"check": "发票深度校验", "result": "❌ 未通过", "detail": "；".join(inv_issues)})
        else:
            checks.append({"check": "发票深度校验", "result": "✅ 通过", "detail": "发票验真、税率、连号检查均通过"})

    # 8. Delivery tracking (阶段❺)
    delivery = DELIVERY_DB.get(po_number)
    if delivery:
        if delivery["delay_days"] > 3:
            checks.append({"check": "交付进度", "result": "⚠️ 延迟",
                           "detail": f"交付延迟 {delivery['delay_days']} 天（预期 {delivery['expected_date']}，实际 {delivery.get('actual_date','—')}）"})
        elif delivery["status"] == "已交付":
            checks.append({"check": "交付进度", "result": "✅ 已交付",
                           "detail": f"按期交付，延迟 {delivery['delay_days']} 天"})
        else:
            checks.append({"check": "交付进度", "result": "ℹ️ " + delivery["status"],
                           "detail": f"预期交付日 {delivery['expected_date']}"})

    # 9. Budget check
    budget_pct = po["budget_used"] / po["budget_total"] * 100 if po["budget_total"] else 0
    if budget_pct > 90:
        checks.append({"check": "预算执行检查", "result": "⚠️ 预算紧张",
                       "detail": f"预算 {_fmt(po['budget_total'])}，已用 {_fmt(po['budget_used'])}（{budget_pct:.0f}%），余额 {_fmt(po['budget_total'] - po['budget_used'])}"})
    else:
        checks.append({"check": "预算执行检查", "result": "✅ 通过",
                       "detail": f"预算 {_fmt(po['budget_total'])}，已用 {_fmt(po['budget_used'])}（{budget_pct:.0f}%），充足"})

    # 10. Split-order evasion (拆单规避: 同部门30天内多笔小额采购)
    dept = po["department"]
    same_dept = [p for p in PROCUREMENT_DB.values() if p["department"] == dept and p["po_number"] != po_number]
    if same_dept and po["amount"] < 50000:
        recent_small = [p for p in same_dept if p["amount"] < 50000
                        and abs((datetime.strptime(p["apply_date"], "%Y-%m-%d") - datetime.strptime(po["apply_date"], "%Y-%m-%d")).days) <= 30]
        if len(recent_small) >= 2:
            total = po["amount"] + sum(p["amount"] for p in recent_small)
            checks.append({"check": "拆单规避检测", "result": "⚠️ 疑似拆单",
                           "detail": f"{dept} 30天内有 {len(recent_small)+1} 笔<5万采购（合计 {_fmt(total)}），"
                                     f"可能拆单规避更高审批层级"})
        else:
            checks.append({"check": "拆单规避检测", "result": "✅ 通过", "detail": "未发现拆单嫌疑"})

    # 11. Duplicate invoice check (发票代码+号码唯一性)
    if invoice:
        inv_key = (invoice.get("invoice_code", ""), invoice.get("invoice_no", ""))
        dup_inv = [v for v in INVOICE_DB.values()
                   if (v.get("invoice_code", ""), v.get("invoice_no", "")) == inv_key
                   and v.get("invoice_number", "") != invoice.get("invoice_number", "")]
        if dup_inv:
            checks.append({"check": "发票重复检测", "result": "❌ 发现重复发票",
                           "detail": f"发票代码{inv_key[0]}+号码{inv_key[1]}在系统中出现多次，疑似重复报销"})
        else:
            checks.append({"check": "发票重复检测", "result": "✅ 通过", "detail": "发票代码+号码唯一"})

    # 12. Abnormal payment time (非工作时间付款检测)
    if payments:
        abnormal_time = []
        for p in payments:
            if p.get("pay_date"):
                d = datetime.strptime(p["pay_date"], "%Y-%m-%d")
                if d.weekday() >= 5:
                    abnormal_time.append(f"{p['payment_number']}于周末({p['pay_date']})付款")
        if abnormal_time:
            checks.append({"check": "异常时间付款", "result": "⚠️ 非工作时间",
                           "detail": "；".join(abnormal_time)})

    # 13. Pay-before-approve check (先付后审检测)
    if payments and contract:
        sign_date = contract.get("sign_date", "")
        for p in payments:
            if p.get("pay_date") and sign_date and p["pay_date"] < sign_date:
                checks.append({"check": "先付后审检测", "result": "❌ 先付后审",
                               "detail": f"{p['payment_number']} 付款日 {p['pay_date']} 早于合同签署日 {sign_date}"})

    risk_level = "低风险"
    failed = sum(1 for c in checks if "❌" in c["result"])
    warned = sum(1 for c in checks if "⚠️" in c["result"])
    if failed >= 2: risk_level = "高风险"
    elif failed >= 1: risk_level = "中高风险"
    elif warned >= 2: risk_level = "中风险"

    return json.dumps({
        "po_number": po_number,
        "title": po["title"],
        "department": po["department"],
        "amount": po["amount"],
        "risk_level": risk_level,
        "checks": checks,
        "contract": contract["contract_number"] if contract else None,
        "payments": [p["payment_number"] for p in payments],
    }, ensure_ascii=False, indent=2)


@tool
def search_all_anomalies(risk_level: str = "all") -> str:
    """搜索所有异常采购记录。risk_level 可选值：all（全部）、high（高风险）、medium（中风险）、low（低风险）。"""
    anomalies = []

    for po_number, po in PROCUREMENT_DB.items():
        issues = []
        level = "low"

        if not po["has_purchase_request"]:
            issues.append("跳过采购申请")
            level = "high"

        contract = _find_contract_by_po(po_number)
        if contract and not contract["correct_type"]:
            issues.append(f"合同类型错误(当前:{contract['contract_type']}, 应为:{po['category']})")
            if contract["amount"] >= 500000:
                level = "high"
            else:
                level = max(level, "medium")

        invoice = _find_invoice_by_po(po_number)
        if invoice and po["amount"] > 0:
            diff = abs(po["amount"] - invoice["amount"]) / po["amount"] * 100
            if diff > 1:
                issues.append(f"三单匹配异常(采购{_fmt(po['amount'])} vs 发票{_fmt(invoice['amount'])}, 差异{diff:.1f}%)")
                level = "medium"

        payments = _find_payments_by_po(po_number)
        if len(payments) > 1:
            amounts = [(p["payee"], p["amount"]) for p in payments]
            if len(amounts) != len(set(amounts)):
                issues.append("疑似重复付款")
                level = "high"

        if contract and payments:
            total_paid = sum(p["amount"] for p in payments if p["status"] == "已付")
            total_pending = sum(p["amount"] for p in payments if p["status"] == "待审批")
            if total_paid > contract["amount"]:
                issues.append(f"超合同金额付款(已付{_fmt(total_paid)}>合同{_fmt(contract['amount'])})")
                level = "high"
            elif total_paid + total_pending > contract["amount"]:
                issues.append(f"待审批后将超合同金额(已付+待批{_fmt(total_paid+total_pending)}>合同{_fmt(contract['amount'])})")
                if level != "high":
                    level = "medium"

        if contract:
            c_amt = contract["amount"]
            if c_amt >= 500000:
                exp = "部门经理→财务总监→CFO→法务"
            elif c_amt >= 50000:
                exp = "部门经理→财务总监"
            else:
                exp = "部门经理"
            exp_steps = exp.split("→")
            act_steps = contract["approval_flow"].split("→")
            if not all(s in act_steps for s in exp_steps):
                missing = [s for s in exp_steps if s not in act_steps]
                issues.append(f"审批流不足(缺少{'、'.join(missing)})")
                level = "high"

        acceptance = _find_acceptance_by_po(po_number)
        if acceptance and acceptance["acceptor"] == po["applicant"]:
            issues.append(f"验收人独立性不足(申请人{po['applicant']}=验收人)")
            if level != "high":
                level = "medium"

        if invoice:
            if not invoice.get("is_valid", True):
                issues.append("发票验真失败（疑似虚开）")
                level = "high"
            if invoice.get("consecutive_flag"):
                issues.append("存在连号发票")
                if level != "high":
                    level = "medium"

        delivery = DELIVERY_DB.get(po_number)
        if delivery and delivery.get("delay_days", 0) > 3:
            issues.append(f"交付延迟{delivery['delay_days']}天")
            if level != "high":
                level = "medium"

        if invoice:
            inv_key = (invoice.get("invoice_code", ""), invoice.get("invoice_no", ""))
            dup_inv = [v for v in INVOICE_DB.values()
                       if (v.get("invoice_code", ""), v.get("invoice_no", "")) == inv_key
                       and v.get("invoice_number", "") != invoice.get("invoice_number", "")]
            if dup_inv:
                issues.append("发票重复（代码+号码不唯一）")
                level = "high"

        dept = po["department"]
        same_dept = [p for p in PROCUREMENT_DB.values() if p["department"] == dept and p["po_number"] != po_number]
        if same_dept and po["amount"] < 50000:
            try:
                recent_small = [p for p in same_dept if p["amount"] < 50000
                                and abs((datetime.strptime(p["apply_date"], "%Y-%m-%d") - datetime.strptime(po["apply_date"], "%Y-%m-%d")).days) <= 30]
                if len(recent_small) >= 2:
                    issues.append(f"疑似拆单规避({dept}30天内{len(recent_small)+1}笔<5万)")
                    if level != "high":
                        level = "medium"
            except Exception:
                pass

        if payments and contract:
            sign_date = contract.get("sign_date", "")
            for p in payments:
                if p.get("pay_date") and sign_date and p["pay_date"] < sign_date:
                    issues.append(f"先付后审({p['payment_number']}付款{p['pay_date']}早于合同签署{sign_date})")
                    level = "high"
                    break

        if issues:
            anomalies.append({
                "po_number": po_number, "title": po["title"],
                "department": po["department"], "amount": po["amount"],
                "risk_level": level, "issues": issues,
                "date": po["apply_date"],
            })

    if risk_level != "all":
        anomalies = [a for a in anomalies if a["risk_level"] == risk_level]

    return json.dumps(anomalies, ensure_ascii=False, indent=2)


@tool
def get_monthly_summary() -> str:
    """获取本月非经营性采购月度统计摘要，包括采购总笔数、总金额、异常数量、按部门和品类的统计。"""
    total = len(PROCUREMENT_DB)
    total_amount = sum(p["amount"] for p in PROCUREMENT_DB.values())
    by_dept = {}
    by_cat = {}
    for po in PROCUREMENT_DB.values():
        by_dept[po["department"]] = by_dept.get(po["department"], 0) + po["amount"]
        by_cat[po["category"]] = by_cat.get(po["category"], 0) + po["amount"]

    anomaly_count = 0
    for po_number, po in PROCUREMENT_DB.items():
        if not po["has_purchase_request"]:
            anomaly_count += 1
            continue
        c = _find_contract_by_po(po_number)
        if c and not c["correct_type"]:
            anomaly_count += 1
            continue
        inv = _find_invoice_by_po(po_number)
        if inv and po["amount"] > 0 and abs(po["amount"] - inv["amount"]) / po["amount"] > 0.01:
            anomaly_count += 1
            continue
        pays = _find_payments_by_po(po_number)
        if len(pays) > 1 and len(set((p["payee"], p["amount"]) for p in pays)) < len(pays):
            anomaly_count += 1

    return json.dumps({
        "period": "2026年3月",
        "total_purchases": total,
        "total_amount": total_amount,
        "anomaly_count": anomaly_count,
        "by_department": by_dept,
        "by_category": by_cat,
        "pending_approvals": sum(1 for p in PROCUREMENT_DB.values() if p["status"] == "待审批"),
        "pending_payments": sum(1 for p in PAYMENT_DB.values() if p["status"] == "待审批"),
    }, ensure_ascii=False, indent=2)


@tool
def generate_risk_report(report_title: str = "非经营性采购内控报告") -> str:
    """生成HTML格式的风控报告并保存为文件。返回报告的访问URL。报告包含本月所有采购的完整风控分析。"""
    anomalies = []
    all_checks = []
    three_doc_pass, three_doc_total = 0, 0
    four_flow_pass, four_flow_total = 0, 0

    for po_number, po in PROCUREMENT_DB.items():
        contract = _find_contract_by_po(po_number)
        acceptance = _find_acceptance_by_po(po_number)
        invoice = _find_invoice_by_po(po_number)
        payments = _find_payments_by_po(po_number)
        issues = []

        if not po["has_purchase_request"]:
            issues.append({"type": "跳过采购申请", "level": "high", "desc": "未提交采购申请直接签署合同"})
        if contract and not contract["correct_type"]:
            issues.append({"type": "合同类型错误", "level": "high" if contract["amount"] >= 500000 else "medium",
                           "desc": f"当前类型 '{contract['contract_type']}', 应为 '{po['category']}'"})
        if contract and invoice and acceptance:
            three_doc_total += 1
            diff = abs(po["amount"] - invoice["amount"]) / po["amount"] * 100 if po["amount"] else 0
            if diff <= 1 and acceptance["qty_received"] == acceptance["qty_ordered"]:
                three_doc_pass += 1
            else:
                issues.append({"type": "三单匹配异常", "level": "medium",
                               "desc": f"金额差异 {diff:.1f}%"})
        if contract and invoice:
            four_flow_total += 1
            if po["supplier"] == contract["supplier"] == invoice["supplier"]:
                four_flow_pass += 1

        if len(payments) > 1 and len(set((p["payee"], p["amount"]) for p in payments)) < len(payments):
            issues.append({"type": "疑似重复付款", "level": "high",
                           "desc": f"发现 {len(payments)} 笔相同金额付款"})

        if issues:
            anomalies.append({"po": po, "contract": contract, "issues": issues})

    high_risk = [a for a in anomalies if any(i["level"] == "high" for i in a["issues"])]
    med_risk = [a for a in anomalies if all(i["level"] != "high" for i in a["issues"])]

    total_amount = sum(p["amount"] for p in PROCUREMENT_DB.values())

    # Build rows
    def _risk_rows(items):
        rows = ""
        for a in items:
            for iss in a["issues"]:
                bg = "#fef2f2" if iss["level"] == "high" else "#fff7ed"
                badge_bg = "#dc2626" if iss["level"] == "high" else "#ea580c"
                rows += f"""<tr style="background:{bg}">
                    <td><code>{a['po']['po_number']}</code></td>
                    <td>{a['po']['title']}</td>
                    <td>{a['po']['department']}</td>
                    <td style="text-align:right">{_fmt(a['po']['amount'])}</td>
                    <td><span style="background:{badge_bg};color:#fff;padding:2px 8px;border-radius:10px;font-size:12px">{iss['type']}</span></td>
                    <td>{iss['desc']}</td></tr>"""
        return rows

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title} - 2026年3月</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans SC','Segoe UI',sans-serif;color:#1d1d1f;background:#fff;padding:40px;max-width:1000px;margin:0 auto;line-height:1.6}}
.header{{text-align:center;padding:40px 0;border-bottom:3px solid #1E3A8A;margin-bottom:30px}}
.header h1{{font-size:24px;color:#1E3A8A;margin-bottom:4px}}
.header h2{{font-size:16px;color:#6e6e73;font-weight:400}}
.header .meta{{font-size:12px;color:#aeaeb2;margin-top:12px}}
.section{{margin-bottom:30px}}
.section h3{{font-size:16px;font-weight:600;color:#1E3A8A;padding:10px 0;border-bottom:1px solid #e5e5e5;margin-bottom:16px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}}
.kpi{{background:#f5f5f7;border-radius:12px;padding:20px;text-align:center}}
.kpi .v{{font-size:28px;font-weight:700;color:#1E3A8A}}
.kpi .l{{font-size:12px;color:#6e6e73;margin-top:4px}}
.kpi.red .v{{color:#dc2626}}
.kpi.green .v{{color:#16a34a}}
table{{width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px}}
th{{text-align:left;padding:10px 12px;background:#f5f5f7;border-bottom:2px solid #e5e5e5;font-weight:600;color:#1E3A8A}}
td{{padding:10px 12px;border-bottom:1px solid #f0f0f0}}
code{{background:#f0f0f5;padding:2px 6px;border-radius:4px;font-size:12px;font-family:'DM Mono',monospace}}
.pass{{color:#16a34a;font-weight:600}}
.fail{{color:#dc2626;font-weight:600}}
.footer{{text-align:center;padding:30px 0;border-top:1px solid #e5e5e5;margin-top:40px;font-size:12px;color:#aeaeb2}}
.rec{{background:#eef2ff;border-left:4px solid #4f46e5;padding:12px 16px;margin:8px 0;border-radius:0 8px 8px 0;font-size:13px}}
@media print{{body{{padding:20px}} .kpi-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="header">
<h1>宝尊电商集团</h1>
<h2>{report_title}</h2>
<div class="meta">报告期间：2026年3月 | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | AI Agent 自动生成</div>
</div>
<div class="section">
<h3>一、整体情况</h3>
<div class="kpi-grid">
<div class="kpi"><div class="v">{len(PROCUREMENT_DB)}</div><div class="l">采购总笔数</div></div>
<div class="kpi"><div class="v">{_fmt(total_amount)}</div><div class="l">采购总金额</div></div>
<div class="kpi red"><div class="v">{len(anomalies)}</div><div class="l">异常项目</div></div>
<div class="kpi green"><div class="v">{len(PROCUREMENT_DB) - len(anomalies)}</div><div class="l">正常项目</div></div>
</div>
</div>
<div class="section">
<h3>二、高风险项目（需立即处理）—— {len(high_risk)} 项</h3>
<table><thead><tr><th>采购单号</th><th>采购标题</th><th>部门</th><th>金额</th><th>异常类型</th><th>详情</th></tr></thead>
<tbody>{_risk_rows(high_risk)}</tbody></table>
</div>
<div class="section">
<h3>三、中风险项目（需关注）—— {len(med_risk)} 项</h3>
<table><thead><tr><th>采购单号</th><th>采购标题</th><th>部门</th><th>金额</th><th>异常类型</th><th>详情</th></tr></thead>
<tbody>{_risk_rows(med_risk)}</tbody></table>
</div>
<div class="section">
<h3>四、三单匹配与四流一致性校验</h3>
<table><thead><tr><th>校验项目</th><th>检查总数</th><th>通过</th><th>异常</th><th>通过率</th></tr></thead>
<tbody>
<tr><td>三单匹配（采购订单/验收单/发票）</td><td>{three_doc_total}</td><td class="pass">{three_doc_pass}</td><td class="fail">{three_doc_total - three_doc_pass}</td><td>{three_doc_pass/three_doc_total*100:.0f}% </td></tr>
<tr><td>四流一致性（合同/资金/发票/物流）</td><td>{four_flow_total}</td><td class="pass">{four_flow_pass}</td><td class="fail">{four_flow_total - four_flow_pass}</td><td>{four_flow_pass/four_flow_total*100:.0f}%</td></tr>
</tbody></table>
</div>
<div class="section">
<h3>五、建议措施</h3>
{"".join(f'<div class="rec">{r}</div>' for r in [
    "PO-2026-004（办公家具）：<b>追补采购申请流程</b>，加强前序流程管控，建议在OA系统中增加合同签署前的采购申请校验",
    "PO-2026-005（GAP成都太古里装修）：<b>更正合同类型</b>为'非经营性采购-门店装修'，重新走审批流程（98万应走CFO审批）",
    "PO-2026-006/PAY-2026-007（ThinkPad笔记本）：<b>立即冻结PAY-2026-007</b>，核实是否重复付款，两笔付款发起人不同（陈志远 vs 张蕾）需追查原因",
    "PO-2026-007（HUNTER营销物料）：<b>核实发票金额差异</b>，采购金额¥85,000 vs 发票金额¥88,500，差异4.1%超过1%阈值",
    "全局建议：推动采购系统与OA合同系统的数据打通，实现合同签署前自动校验采购申请是否存在",
])}
</div>
<div class="section">
<h3>六、采购明细清单</h3>
<table><thead><tr><th>采购单号</th><th>标题</th><th>品类</th><th>部门</th><th>金额</th><th>供应商</th><th>状态</th></tr></thead>
<tbody>{"".join(f'<tr><td><code>{po["po_number"]}</code></td><td>{po["title"]}</td><td>{po["category"]}</td><td>{po["department"]}</td><td style="text-align:right">{_fmt(po["amount"])}</td><td>{po["supplier"]}</td><td>{po["status"]}</td></tr>' for po in PROCUREMENT_DB.values())}</tbody></table>
</div>
<div class="footer">
本报告由宝尊风控AI Agent自动生成 | 基于采购系统、OA合同系统、OA付款系统数据 | 仅供内部使用<br>
宝尊电商集团 风控部 © 2026
</div>
</body></html>"""

    os.makedirs("reports", exist_ok=True)
    filename = f"risk-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    filepath = os.path.join("reports", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return f"报告已生成。访问URL: /reports/{filename} 。报告包含 {len(PROCUREMENT_DB)} 笔采购记录，其中 {len(high_risk)} 项高风险、{len(med_risk)} 项中风险。"


@tool
def create_work_order(po_number: str, issue_type: str, priority: str = "high", assignee: str = "待分配") -> str:
    """创建异常工单并自动推送飞书通知。参数：po_number 采购单号，issue_type 异常类型（如"跳过采购申请"/"合同类型错误"/"重复付款"等），priority 优先级(high/medium/low)，assignee 责任人姓名。"""
    po = PROCUREMENT_DB.get(po_number)
    if not po:
        return f"采购单 {po_number} 不存在。可用: {', '.join(PROCUREMENT_DB.keys())}"

    _wo_counter[0] += 1
    wid = f"WO-2026-{_wo_counter[0]:03d}"
    SLA_MAP = {"数量不符": 3, "单价不符": 5, "税率不符": 3, "缺票": 10, "错票": 10,
               "跳过采购申请": 5, "合同类型错误": 5, "重复付款": 3, "超合同金额": 3,
               "审批流异常": 5, "发票异常": 5, "验收独立性": 5, "拆单规避": 5}
    sla_days = 5
    for k, v in SLA_MAP.items():
        if k in issue_type:
            sla_days = v
            break
    due_date = (datetime.now() + timedelta(days=sla_days)).strftime("%Y-%m-%d")
    wo = {
        "id": wid, "po_number": po_number,
        "type": issue_type, "priority": priority,
        "title": f"{po['title']} - {issue_type}",
        "assignee": assignee, "status": "open",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "due": due_date, "sla_days": sla_days,
        "description": f"{po['title']}：{issue_type}（闭环时限T+{sla_days}天，截止{due_date}）",
    }
    WORKORDER_DB[wid] = wo

    _notif_counter[0] += 1
    notif = {
        "id": f"N-{_notif_counter[0]:03d}",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "channel": "飞书", "recipient": assignee,
        "type": "工单创建",
        "content": f"{wid}: {wo['title']}",
        "status": "已送达",
    }
    NOTIFICATION_LOG.append(notif)

    return json.dumps({
        "message": f"工单 {wid} 已创建，飞书通知已推送给 {assignee}",
        "work_order": wo,
        "notification": notif,
    }, ensure_ascii=False, indent=2)


@tool
def list_work_orders(status: str = "all") -> str:
    """列出异常工单。status 可选值：all（全部）、open（待处理）、in_progress（处理中）、resolved（已解决）、closed（已关闭）。"""
    orders = list(WORKORDER_DB.values())
    if status != "all":
        orders = [o for o in orders if o["status"] == status]
    return json.dumps({"total": len(orders), "work_orders": orders}, ensure_ascii=False, indent=2)


@tool
def update_work_order(work_order_id: str, status: str = "", assignee: str = "") -> str:
    """更新工单状态或责任人。work_order_id 工单号(WO-2026-XXX)，status 新状态(open/in_progress/resolved/closed)，assignee 新责任人。"""
    wo = WORKORDER_DB.get(work_order_id)
    if not wo:
        return f"工单 {work_order_id} 不存在。可用: {', '.join(WORKORDER_DB.keys())}"
    old_status = wo["status"]
    if status:
        wo["status"] = status
    if assignee:
        wo["assignee"] = assignee

    _notif_counter[0] += 1
    notif = {
        "id": f"N-{_notif_counter[0]:03d}",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "channel": "飞书", "recipient": wo["assignee"],
        "type": "工单更新",
        "content": f"{work_order_id} 状态更新: {old_status} → {wo['status']}",
        "status": "已送达",
    }
    NOTIFICATION_LOG.append(notif)

    return json.dumps({
        "message": f"工单 {work_order_id} 已更新",
        "work_order": wo, "notification": notif,
    }, ensure_ascii=False, indent=2)


@tool
def push_feishu_notification(recipient: str, message: str, notification_type: str = "异常预警") -> str:
    """推送飞书通知。recipient 接收人姓名，message 通知内容，notification_type 通知类型（异常预警/工单提醒/月报推送/审批催办等）。
    若配置了环境变量 FEISHU_WEBHOOK_URL / OA_WEBHOOK_URL，将同步 POST 到真实群机器人或 OA 回调。"""
    from integrations.webhooks import notify_integrations

    _notif_counter[0] += 1
    nid = f"N-{_notif_counter[0]:03d}"
    remote = notify_integrations(recipient=recipient, message=message, notification_type=notification_type)
    any_ok = any(x and x.get("ok") for x in remote.values() if isinstance(x, dict))
    notif = {
        "id": nid,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "channel": "飞书/OA",
        "recipient": recipient,
        "type": notification_type,
        "content": message,
        "status": "已送达(远程)" if any_ok else "已记录(演示)",
        "remote": remote,
    }
    NOTIFICATION_LOG.append(notif)
    return json.dumps(
        {
            "message": f"通知已处理：{recipient}",
            "notification": notif,
        },
        ensure_ascii=False,
        indent=2,
    )


# ════════════════════════════════════════════════════════════════
#  ONE-CLICK FIX TOOLS — Remediation actions
# ════════════════════════════════════════════════════════════════

@tool
def fix_contract_type(contract_number: str, correct_type: str) -> str:
    """一键修正合同类型并更新审批流。contract_number 合同号(SC-2026-XXX)，correct_type 正确的合同类型（如'非经营性采购-门店装修'）。执行后自动更新审批流、创建工单、推送飞书通知。"""
    contract = CONTRACT_DB.get(contract_number)
    if not contract:
        return f"合同 {contract_number} 不存在"
    old_type = contract["contract_type"]
    old_flow = contract["approval_flow"]
    contract["contract_type"] = correct_type
    contract["correct_type"] = True
    amt = contract["amount"]
    if amt >= 500000:
        contract["approval_flow"] = "部门经理→财务总监→CFO→法务"
    elif amt >= 50000:
        contract["approval_flow"] = "部门经理→财务总监"
    else:
        contract["approval_flow"] = "部门经理"
    contract["status"] = "审批中（重新提交）"
    _wo_counter[0] += 1
    wid = f"WO-2026-{_wo_counter[0]:03d}"
    WORKORDER_DB[wid] = {
        "id": wid, "po_number": contract["po_number"],
        "type": "合同类型修正-已完成", "priority": "medium",
        "title": f"{contract['title']} - 类型已修正",
        "assignee": "AI Agent 自动执行", "status": "resolved",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "due": "", "description": f"合同类型从'{old_type}'修正为'{correct_type}'，审批流更新为'{contract['approval_flow']}'",
    }
    _notif_counter[0] += 1
    NOTIFICATION_LOG.append({
        "id": f"N-{_notif_counter[0]:03d}", "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "channel": "飞书", "recipient": "风控负责人",
        "type": "整改完成", "content": f"{contract_number} 合同类型已修正: '{old_type}' → '{correct_type}'，审批流已更新",
        "status": "已送达",
    })
    return json.dumps({
        "status": "success", "message": "合同类型已修正",
        "contract_number": contract_number,
        "changes": {"contract_type": {"from": old_type, "to": correct_type},
                    "approval_flow": {"from": old_flow, "to": contract["approval_flow"]}},
        "work_order": wid, "notification_sent_to": "风控负责人",
    }, ensure_ascii=False, indent=2)


@tool
def freeze_payment(payment_number: str, reason: str) -> str:
    """一键冻结付款申请。payment_number 付款单号(PAY-2026-XXX)，reason 冻结原因。执行后自动创建工单、推送飞书通知。"""
    payment = PAYMENT_DB.get(payment_number)
    if not payment:
        return f"付款单 {payment_number} 不存在"
    old_status = payment["status"]
    payment["status"] = "已冻结"
    _wo_counter[0] += 1
    wid = f"WO-2026-{_wo_counter[0]:03d}"
    WORKORDER_DB[wid] = {
        "id": wid, "po_number": payment["po_number"],
        "type": "付款冻结", "priority": "high",
        "title": f"已冻结付款 {payment_number}（{_fmt(payment['amount'])}）",
        "assignee": "AI Agent 自动执行", "status": "resolved",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "due": "", "description": f"付款{payment_number}已冻结，原因：{reason}",
    }
    _notif_counter[0] += 1
    NOTIFICATION_LOG.append({
        "id": f"N-{_notif_counter[0]:03d}", "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "channel": "飞书", "recipient": "风控负责人",
        "type": "付款冻结", "content": f"{payment_number}（{_fmt(payment['amount'])}）已冻结: {reason}",
        "status": "已送达",
    })
    return json.dumps({
        "status": "success", "message": "付款已冻结",
        "payment_number": payment_number, "amount": payment["amount"],
        "reason": reason, "old_status": old_status, "new_status": "已冻结", "work_order": wid,
    }, ensure_ascii=False, indent=2)


@tool
def supplement_purchase_request(po_number: str) -> str:
    """一键补提采购申请。为缺少采购申请的采购单补提PR。执行后自动创建工单、推送飞书通知。"""
    po = PROCUREMENT_DB.get(po_number)
    if not po:
        return f"采购单 {po_number} 不存在"
    pr_number = f"PR-{po_number.replace('PO-', '')}-补提"
    po["has_purchase_request"] = True
    po["pr_number"] = pr_number
    _wo_counter[0] += 1
    wid = f"WO-2026-{_wo_counter[0]:03d}"
    WORKORDER_DB[wid] = {
        "id": wid, "po_number": po_number,
        "type": "采购申请补提-已完成", "priority": "medium",
        "title": f"{po['title']} - 采购申请已补提",
        "assignee": "AI Agent 自动执行", "status": "resolved",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "due": "", "description": f"已为{po_number}补提采购申请{pr_number}",
    }
    _notif_counter[0] += 1
    NOTIFICATION_LOG.append({
        "id": f"N-{_notif_counter[0]:03d}", "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "channel": "飞书", "recipient": po["applicant"],
        "type": "采购申请补提", "content": f"{po_number} 采购申请已补提，编号 {pr_number}",
        "status": "已送达",
    })
    return json.dumps({
        "status": "success", "message": "采购申请已补提",
        "po_number": po_number, "pr_number": pr_number, "work_order": wid,
    }, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════
#  SUPPLIER & BID RIGGING (场景5 — 供应商画像与风险预警 / 阶段❸)
# ════════════════════════════════════════════════════════════════

@tool
def query_supplier_profile(supplier_id: str) -> str:
    """查询供应商详细画像与风险评估。supplier_id 供应商编号(SUP-XXX)或名称关键字。"""
    found = SUPPLIER_DB.get(supplier_id)
    if not found:
        for s in SUPPLIER_DB.values():
            if supplier_id in s["name"]:
                found = s
                break
    if not found:
        return f"未找到供应商 {supplier_id}。可用: {', '.join(SUPPLIER_DB.keys())}"
    risk_factors = []
    if found["credit_score"] < 70:
        risk_factors.append(f"信用评分偏低({found['credit_score']}分)")
    if found["related_suppliers"]:
        names = [SUPPLIER_DB[rs]["name"] for rs in found["related_suppliers"] if rs in SUPPLIER_DB]
        risk_factors.append(f"存在关联供应商: {', '.join(names)}")
    if found["reg_capital"] < 1000000:
        risk_factors.append(f"注册资本偏低({_fmt(found['reg_capital'])})")
    if found["win_rate"] >= 1.0 and found["bid_count"] > 0:
        risk_factors.append("中标率100%（需关注是否存在围标）")
    if not found["last_audit"]:
        risk_factors.append("从未接受审计")
    if found["status"] != "正常":
        risk_factors.append(f"供应商状态异常: {found['status']}")
    result = {**found, "risk_factors": risk_factors, "risk_assessment": "高风险" if len(risk_factors) >= 2 else ("中风险" if risk_factors else "低风险")}
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def detect_bid_rigging(po_number: str) -> str:
    """检测指定采购的围标串标风险。分析投标方是否存在关联关系、中标率异常等。po_number 采购单号。"""
    key = _coerce_po_for_tool(po_number)
    if not key:
        return f"采购单号格式无效: {po_number}"
    po = PROCUREMENT_DB.get(key)
    if not po:
        return f"采购单 {key} 不存在"
    row = _analyze_bid_rigging_for_po_row(po)
    if row.get("risk") == "unknown":
        return json.dumps({"po_number": row["po_number"], "result": "未找到供应商信息", "risk": "unknown"}, ensure_ascii=False)
    return json.dumps(row, ensure_ascii=False, indent=2)


@tool
def scan_all_bid_rigging_risks() -> str:
    """一次性扫描演示库内全部采购单的围标串标风险。用户问「所有供应商」「全量」「全部」围标/串标时优先调用本工具，勿逐单反复 detect_bid_rigging。"""
    details = [_analyze_bid_rigging_for_po_row(po) for po in PROCUREMENT_DB.values()]
    high = [d for d in details if d.get("risk") == "high"]
    return json.dumps(
        {
            "summary": {
                "total_po": len(details),
                "high_risk_count": len(high),
                "message": "全量扫描完成。请据此输出结构化结论，勿再逐单重复调用 detect_bid_rigging。",
            },
            "high_risk_items": high,
            "all_items": details,
        },
        ensure_ascii=False,
        indent=2,
    )


# ════════════════════════════════════════════════════════════════
#  SPLIT-ORDER EVASION (阶段❷ — 拆单规避检测)
# ════════════════════════════════════════════════════════════════

@tool
def detect_split_orders(department: str = "all") -> str:
    """检测拆单规避行为：同部门30天内多笔<5万采购，可能故意拆分以规避更高审批层级。department 部门名称或'all'全部检测。"""
    results = []
    dept_groups: dict[str, list] = {}
    for po in PROCUREMENT_DB.values():
        d = po["department"]
        if department != "all" and department not in d:
            continue
        if po["amount"] < 50000:
            dept_groups.setdefault(d, []).append(po)

    for dept, pos in dept_groups.items():
        pos_sorted = sorted(pos, key=lambda x: x["apply_date"])
        for i, base in enumerate(pos_sorted):
            nearby = [p for p in pos_sorted if p["po_number"] != base["po_number"]
                      and abs((datetime.strptime(p["apply_date"], "%Y-%m-%d") - datetime.strptime(base["apply_date"], "%Y-%m-%d")).days) <= 30]
            if len(nearby) >= 2:
                total = base["amount"] + sum(p["amount"] for p in nearby)
                results.append({
                    "department": dept,
                    "count": len(nearby) + 1,
                    "total_amount": total,
                    "orders": [base["po_number"]] + [p["po_number"] for p in nearby],
                    "risk": "high" if total >= 50000 else "medium",
                    "detail": f"合计{_fmt(total)}，{'超过' if total >= 50000 else '接近'}5万审批阈值",
                })
                break
    if not results:
        return json.dumps({"result": "未发现拆单规避嫌疑", "departments_checked": department}, ensure_ascii=False)
    return json.dumps(results, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════
#  PAYMENT ANOMALY CHECK (阶段❾ — 异常时间/先付后审/账户变更)
# ════════════════════════════════════════════════════════════════

@tool
def check_payment_anomaly(payment_number: str = "all") -> str:
    """付款异常检测：非工作时间付款、先付后审、周末付款等。payment_number 付款单号或'all'全部检测。"""
    targets = list(PAYMENT_DB.values()) if payment_number == "all" else [PAYMENT_DB.get(payment_number)]
    targets = [t for t in targets if t]
    if not targets:
        return f"付款单 {payment_number} 不存在。可用: {', '.join(PAYMENT_DB.keys())}"

    anomalies = []
    for p in targets:
        issues = []
        if p.get("pay_date"):
            d = datetime.strptime(p["pay_date"], "%Y-%m-%d")
            if d.weekday() >= 5:
                issues.append(f"周末付款（{['周一','周二','周三','周四','周五','周六','周日'][d.weekday()]}）")
        contract = next((c for c in CONTRACT_DB.values() if c["contract_number"] == p.get("contract_number")), None)
        if contract and p.get("pay_date") and p["pay_date"] < contract.get("sign_date", ""):
            issues.append(f"先付后审：付款日{p['pay_date']}早于合同签署日{contract['sign_date']}")
        if issues:
            anomalies.append({"payment_number": p["payment_number"], "amount": p["amount"],
                              "payee": p["payee"], "issues": issues})

    if not anomalies:
        return json.dumps({"result": "未发现付款异常", "checked": len(targets)}, ensure_ascii=False)
    return json.dumps(anomalies, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════
#  INVOICE DEEP CHECK (阶段❼ — 发票验真、连号检测、税率校验)
# ════════════════════════════════════════════════════════════════

@tool
def check_invoice_deep(po_number: str) -> str:
    """发票深度校验：验真、连号检测、税率校验、金额计算校验。po_number 采购单号。"""
    po = PROCUREMENT_DB.get(po_number)
    if not po:
        return f"采购单 {po_number} 不存在"
    inv = _find_invoice_by_po(po_number)
    if not inv:
        return json.dumps({"po_number": po_number, "result": "未找到发票", "risk": "high"}, ensure_ascii=False)
    issues = []
    if not inv.get("is_valid", True):
        issues.append({"type": "验真失败", "desc": f"发票 {inv.get('invoice_number','')} 验真未通过，疑似虚开", "risk": "high"})
    if not inv.get("verified", True):
        issues.append({"type": "未验证", "desc": f"发票 {inv.get('invoice_number','')} 尚未完成验证", "risk": "medium"})
    if inv.get("consecutive_flag"):
        all_nos = sorted([(v.get("invoice_code",""), v.get("invoice_no","")) for v in INVOICE_DB.values()
                          if v.get("invoice_code") == inv.get("invoice_code")])
        if len(all_nos) >= 2:
            issues.append({"type": "连号发票", "desc": f"同一发票代码 {inv.get('invoice_code','')} 下存在连号发票（共{len(all_nos)}张），需核查是否来自同一供应商批量开票", "risk": "medium"})
    expected_rate = None
    for k, v in EXPECTED_TAX_RATES.items():
        if k in po.get("category", "") or k in po.get("title", ""):
            expected_rate = v
            break
    if expected_rate and abs(inv["tax_rate"] - expected_rate) > 0.001:
        issues.append({"type": "税率异常", "desc": f"发票税率 {inv['tax_rate']*100:.0f}% 与品类期望税率 {expected_rate*100:.0f}% 不符", "risk": "medium"})
    calc_tax = round(inv["amount"] * inv["tax_rate"], 2)
    actual_tax = inv.get("tax_amount", calc_tax)
    if abs(calc_tax - actual_tax) > 1:
        issues.append({"type": "税额计算异常", "desc": f"计算税额 {_fmt(calc_tax)} vs 发票税额 {_fmt(actual_tax)} 差异过大", "risk": "high"})
    calc_total = round(inv["amount"] + actual_tax, 2)
    actual_total = inv.get("total_with_tax", calc_total)
    if abs(calc_total - actual_total) > 1:
        issues.append({"type": "价税合计异常", "desc": f"计算价税合计 {_fmt(calc_total)} vs 发票价税合计 {_fmt(actual_total)}", "risk": "high"})
    risk = "high" if any(i["risk"] == "high" for i in issues) else ("medium" if issues else "low")
    return json.dumps({
        "po_number": po_number, "invoice_number": inv.get("invoice_number", ""),
        "supplier": inv["supplier"], "amount": inv["amount"], "tax_rate": f"{inv['tax_rate']*100:.0f}%",
        "tax_amount": inv.get("tax_amount", 0), "total_with_tax": inv.get("total_with_tax", 0),
        "issues": issues if issues else [{"type": "通过", "desc": "发票深度校验全部通过", "risk": "low"}],
        "overall_risk": risk,
    }, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════
#  ACCEPTOR INDEPENDENCE CHECK (阶段❻ — 验收人独立性)
# ════════════════════════════════════════════════════════════════

@tool
def check_acceptor_independence(po_number: str) -> str:
    """检查验收人独立性——验收人不应与采购申请人相同（不相容职务分离）。po_number 采购单号。"""
    po = PROCUREMENT_DB.get(po_number)
    if not po:
        return f"采购单 {po_number} 不存在"
    acc = _find_acceptance_by_po(po_number)
    if not acc:
        return json.dumps({"po_number": po_number, "result": "未找到验收记录", "risk": "medium"}, ensure_ascii=False)
    issues = []
    if acc["acceptor"] == po["applicant"]:
        issues.append({
            "type": "验收人与申请人相同",
            "desc": f"采购申请人 {po['applicant']} 同时担任验收人，违反不相容职务分离原则",
            "risk": "high",
        })
    if acc.get("acceptor_dept") == po.get("department"):
        if acc["acceptor"] == po["applicant"]:
            pass
        else:
            issues.append({
                "type": "验收人与申请人同部门",
                "desc": f"验收人 {acc['acceptor']} 与采购申请人 {po['applicant']} 均属于 {po['department']}，建议跨部门验收",
                "risk": "low",
            })
    return json.dumps({
        "po_number": po_number, "applicant": po["applicant"],
        "acceptor": acc["acceptor"], "acceptor_dept": acc.get("acceptor_dept", ""),
        "issues": issues if issues else [{"type": "通过", "desc": "验收人与申请人不同，符合独立性要求", "risk": "low"}],
        "overall_risk": "high" if any(i["risk"] == "high" for i in issues) else "low",
    }, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════
#  BUDGET MANAGEMENT (阶段❶ — 预算编制与额度管控)
# ════════════════════════════════════════════════════════════════

@tool
def query_budget(budget_code: str = "", department: str = "") -> str:
    """查询预算执行情况。可按预算编号(budget_code)或部门(department)查询。不传参则返回全部。"""
    results = []
    for code, b in BUDGET_DB.items():
        if budget_code and budget_code not in code:
            continue
        if department and department not in b["dept"]:
            continue
        usage_rate = b["used"] / b["q_budget"] * 100 if b["q_budget"] > 0 else 0
        status = "超预算" if b["available"] < 0 else ("预算紧张" if usage_rate > 80 else "正常")
        results.append({**b, "usage_rate": f"{usage_rate:.1f}%", "status": status})
    if not results:
        return f"未找到匹配的预算记录。可用预算编号: {', '.join(BUDGET_DB.keys())}"
    return json.dumps(results, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════
#  DELIVERY TRACKING (阶段❺ — 下单与订单跟踪)
# ════════════════════════════════════════════════════════════════

@tool
def track_delivery(po_number: str = "") -> str:
    """查询订单交付进度。可指定po_number查询特定订单，不传则返回全部。"""
    if po_number:
        d = DELIVERY_DB.get(po_number)
        if not d:
            return f"未找到 {po_number} 的交付记录"
        po = PROCUREMENT_DB.get(po_number, {})
        d_out = {**d, "title": po.get("title", ""), "supplier": po.get("supplier", ""), "amount": po.get("amount", 0)}
        if d["delay_days"] > 3:
            d_out["alert"] = f"交付延迟 {d['delay_days']} 天，建议确认违约金条款"
        return json.dumps(d_out, ensure_ascii=False, indent=2)
    results = []
    for po_num, d in DELIVERY_DB.items():
        po = PROCUREMENT_DB.get(po_num, {})
        item = {**d, "title": po.get("title", ""), "supplier": po.get("supplier", "")}
        results.append(item)
    return json.dumps(results, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════
#  ASSET MANAGEMENT (阶段❿ — 资产入账与后续管理)
# ════════════════════════════════════════════════════════════════

@tool
def query_assets(asset_id: str = "", po_number: str = "") -> str:
    """查询固定资产/长期待摊费用台账。可按资产编号(asset_id)或采购单号(po_number)查询。"""
    results = []
    for aid, a in ASSET_DB.items():
        if asset_id and asset_id != aid:
            continue
        if po_number and po_number != a["po_number"]:
            continue
        results.append(a)
    if not results:
        return f"未找到匹配的资产记录。可用: {', '.join(ASSET_DB.keys())}"
    return json.dumps(results, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════
#  CONTRACT CLAUSE REVIEW (场景4 — 合同智能审查)
# ════════════════════════════════════════════════════════════════

@tool
def review_contract_clauses(contract_number: str) -> str:
    """合同条款智能审查：检查预付比例、验收条款、违约条款、保密条款、付款条件等。contract_number 合同编号(SC-2026-XXX)。"""
    contract = CONTRACT_DB.get(contract_number)
    if not contract:
        return f"合同 {contract_number} 不存在"
    detail = CONTRACT_DETAILS_DB.get(contract_number, {})
    if not detail:
        return json.dumps({"contract_number": contract_number, "result": "无合同条款详情数据"}, ensure_ascii=False)
    issues = []
    std = CONTRACT_CLAUSE_STANDARDS
    if detail.get("prepay_ratio", 0) > std["预付比例"]["threshold"]:
        issues.append({"clause": "预付比例", "desc": f"预付比例 {detail['prepay_ratio']*100:.0f}% 超过标准上限 {std['预付比例']['threshold']*100:.0f}%",
                        "rule": std["预付比例"]["rule"], "risk": "high"})
    if not detail.get("has_acceptance_clause"):
        issues.append({"clause": "验收条款", "desc": "合同缺少验收标准条款", "rule": std["验收条款"]["rule"], "risk": "high"})
    if not detail.get("has_penalty_clause"):
        issues.append({"clause": "违约条款", "desc": "合同缺少违约责任条款", "rule": std["违约条款"]["rule"], "risk": "high"})
    if not detail.get("penalty_symmetric", True):
        issues.append({"clause": "违约对等性", "desc": "违约条款不对等，仅约束一方", "rule": "违约条款应对等约束双方", "risk": "medium"})
    if not detail.get("has_confidential_clause"):
        issues.append({"clause": "保密条款", "desc": "合同缺少保密条款（涉及品牌方信息）", "rule": std["保密条款"]["rule"], "risk": "medium"})
    risk = "high" if any(i["risk"] == "high" for i in issues) else ("medium" if issues else "low")
    return json.dumps({
        "contract_number": contract_number, "supplier": contract.get("supplier", ""),
        "amount": contract.get("amount", 0), "contract_type": contract.get("contract_type", ""),
        "clause_review": issues if issues else [{"clause": "全部通过", "desc": "合同条款审查全部通过", "risk": "low"}],
        "overall_risk": risk,
    }, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════
#  AUDIT WORKPAPER EXPORT (F15 — 审计底稿一键导出)
# ════════════════════════════════════════════════════════════════

@tool
def generate_audit_workpaper(report_title: str = "非经营性采购审计底稿") -> str:
    """一键导出审计底稿HTML，包含：审计目标、采购明细、审批记录、合同信息、发票校验、验收记录、付款回单、异常汇总、审计结论与建议。"""
    os.makedirs("reports", exist_ok=True)
    all_checks = []
    for po_number, po in PROCUREMENT_DB.items():
        contract = _find_contract_by_po(po_number)
        acceptance = _find_acceptance_by_po(po_number)
        invoice = _find_invoice_by_po(po_number)
        payments = _find_payments_by_po(po_number)
        delivery = DELIVERY_DB.get(po_number, {})
        asset = None
        for a in ASSET_DB.values():
            if a["po_number"] == po_number:
                asset = a
                break
        all_checks.append({
            "po": po, "contract": contract, "acceptance": acceptance,
            "invoice": invoice, "payments": payments, "delivery": delivery, "asset": asset,
        })

    total_amount = sum(po["amount"] for po in PROCUREMENT_DB.values())
    anomaly_data = json.loads(search_all_anomalies.invoke({"risk_level": "all"}))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows_html = ""
    for idx, item in enumerate(all_checks, 1):
        po = item["po"]
        c = item["contract"]
        inv = item["invoice"]
        acc = item["acceptance"]
        pays = item["payments"]
        dlv = item["delivery"]
        ast = item["asset"]
        anomalies_for_po = [a for a in anomaly_data if a["po_number"] == po["po_number"]]
        risk_tag = "🔴 高" if any(a["risk_level"] == "high" for a in anomalies_for_po) else (
            "🟡 中" if any(a["risk_level"] == "medium" for a in anomalies_for_po) else "🟢 低")
        rows_html += f"""<tr>
<td>{idx}</td><td>{po['po_number']}</td><td>{po['title']}</td><td>{po['department']}</td>
<td>{po['applicant']}</td><td>{_fmt(po['amount'])}</td>
<td>{c['contract_number'] if c else '—'}</td><td>{c['contract_type'] if c else '—'}</td>
<td>{'PR:'+po['pr_number'] if po.get('pr_number') else '❌ 无PR'}</td>
<td>{c['approval_flow'] if c else '—'}</td>
<td>{acc['acceptor'] + ' / ' + acc['date'] if acc else '—'}</td>
<td>{(inv.get('invoice_number','') + ' / ' + _fmt(inv['amount'])) if inv else '—'}</td>
<td>{(', '.join(p['payment_number']+':'+p['status'] for p in pays)) if pays else '—'}</td>
<td>{dlv.get('status','—') if dlv else '—'}{(' (延'+str(dlv.get('delay_days',0))+'天)') if dlv and dlv.get('delay_days',0)>0 else ''}</td>
<td>{ast['id']+' / '+ast['status'] if ast else '—'}</td>
<td>{risk_tag}</td>
<td>{'；'.join(a['issues'][0] if isinstance(a['issues'][0], str) else str(a['issues'][0]) for a in anomalies_for_po) if anomalies_for_po else '无异常'}</td>
</tr>"""

    anomaly_rows = ""
    for a in anomaly_data:
        anomaly_rows += f"""<tr>
<td>{a['po_number']}</td><td>{a['title']}</td><td>{'，'.join(str(i) for i in a['issues'])}</td>
<td>{'🔴 高' if a['risk_level']=='high' else ('🟡 中' if a['risk_level']=='medium' else '🟢 低')}</td>
<td>{_fmt(a['amount'])}</td></tr>"""

    wo_rows = ""
    for wo in WORKORDER_DB.values():
        wo_rows += f"<tr><td>{wo['id']}</td><td>{wo['title']}</td><td>{wo['status']}</td><td>{wo['assignee']}</td><td>{wo['created']}</td></tr>"

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{report_title}</title>
<style>
body{{font-family:'PingFang SC','Microsoft YaHei',sans-serif;max-width:1400px;margin:0 auto;padding:40px;color:#1d1d1f;background:#fff}}
h1{{font-size:28px;border-bottom:2px solid #1d1d1f;padding-bottom:12px}}
h2{{font-size:20px;margin-top:32px;color:#1d1d1f}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin:16px 0}}
th{{background:#f5f5f7;padding:8px 6px;text-align:left;border:1px solid #d2d2d7;font-weight:600}}
td{{padding:6px;border:1px solid #d2d2d7;vertical-align:top}}
.meta{{color:#86868b;font-size:13px;margin-bottom:24px}}
.summary-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:16px 0}}
.summary-card{{background:#f5f5f7;border-radius:8px;padding:16px;text-align:center}}
.summary-card .num{{font-size:28px;font-weight:700;color:#1d1d1f}}
.summary-card .label{{font-size:12px;color:#86868b;margin-top:4px}}
.footer{{margin-top:40px;padding-top:16px;border-top:1px solid #d2d2d7;font-size:12px;color:#86868b}}
</style></head><body>
<h1>{report_title}</h1>
<div class="meta">生成时间：{now} | 审计期间：2026年Q1 | 审计范围：非经营性采购全流程 | 生成方式：AI Agent自动导出</div>

<h2>一、审计概要</h2>
<div class="summary-grid">
<div class="summary-card"><div class="num">{len(PROCUREMENT_DB)}</div><div class="label">采购单总数</div></div>
<div class="summary-card"><div class="num">{_fmt(total_amount)}</div><div class="label">采购总金额</div></div>
<div class="summary-card"><div class="num">{len(anomaly_data)}</div><div class="label">异常事项</div></div>
<div class="summary-card"><div class="num">{len(WORKORDER_DB)}</div><div class="label">整改工单</div></div>
</div>

<h2>二、采购明细与全流程追踪</h2>
<table>
<tr><th>#</th><th>PO号</th><th>项目名称</th><th>部门</th><th>申请人</th><th>金额</th>
<th>合同号</th><th>合同类型</th><th>采购申请</th><th>审批流</th>
<th>验收人/日期</th><th>发票号/金额</th><th>付款状态</th><th>交付状态</th><th>资产入账</th><th>风险</th><th>异常详情</th></tr>
{rows_html}</table>

<h2>三、异常汇总</h2>
<table>
<tr><th>PO号</th><th>项目</th><th>异常描述</th><th>风险等级</th><th>金额</th></tr>
{anomaly_rows}</table>

<h2>四、整改工单跟踪</h2>
<table>
<tr><th>工单号</th><th>描述</th><th>状态</th><th>责任人</th><th>创建时间</th></tr>
{wo_rows}</table>

<h2>五、审计结论与建议</h2>
<ol>
<li>本期 {len(PROCUREMENT_DB)} 笔非经营性采购中，发现 {len(anomaly_data)} 项异常，涉及金额 {_fmt(sum(a['amount'] for a in anomaly_data))}。</li>
<li>主要风险集中在：跳过采购申请流程、合同类型不匹配、重复付款风险。</li>
<li>建议：强化采购申请前置审批，完善合同类型自动校验规则，建立付款防重复机制。</li>
<li>已通过AI Agent自动创建 {len(WORKORDER_DB)} 个整改工单，推送 {len(NOTIFICATION_LOG)} 条飞书通知。</li>
</ol>

<div class="footer">本底稿由宝尊电商风控AI Agent自动生成，仅供内部审计使用。审计人员需结合原始凭证进行最终确认。</div>
</body></html>"""

    filename = f"audit-workpaper-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    filepath = os.path.join("reports", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return f"审计底稿已生成。访问URL: /reports/{filename} 。包含 {len(PROCUREMENT_DB)} 笔采购全流程追踪、{len(anomaly_data)} 项异常汇总、{len(WORKORDER_DB)} 个工单记录。"


# ════════════════════════════════════════════════════════════════
#  ACTION EXTRACTION — Auto-detect fixable issues from risk checks
# ════════════════════════════════════════════════════════════════

def _extract_fix_actions(result_str):
    try:
        data = json.loads(result_str)
    except:
        return []
    actions = []
    po_number = data.get("po_number", "")
    po = PROCUREMENT_DB.get(po_number)
    if not po:
        return []
    seen_ids = set()
    for check in data.get("checks", []):
        r = check.get("result", "")
        cn = check.get("check", "")
        if "❌" not in r and "⚠️" not in r:
            continue
        if "前序流程" in cn and "❌" in r:
            aid = f"supplement_{po_number}"
            if aid not in seen_ids:
                seen_ids.add(aid)
                actions.append({"id": aid, "type": "supplement_purchase_request", "title": "追补采购申请",
                                "desc": f"为 {po_number} 补提采购申请流程",
                                "command": f"请为采购单{po_number}补提采购申请", "risk": "medium"})
        if "合同类型" in cn and "❌" in r:
            contract = _find_contract_by_po(po_number)
            if contract:
                aid = f"fix_type_{contract['contract_number']}"
                if aid not in seen_ids:
                    seen_ids.add(aid)
                    actions.append({"id": aid, "type": "fix_contract_type", "title": "修正合同类型",
                                    "desc": f"将 {contract['contract_number']} 更正为 '{po['category']}'",
                                    "command": f"请修正合同{contract['contract_number']}的类型为'{po['category']}'", "risk": "medium"})
        if "审批流" in cn and "❌" in r:
            contract = _find_contract_by_po(po_number)
            if contract:
                aid = f"resubmit_{contract['contract_number']}"
                if aid not in seen_ids:
                    seen_ids.add(aid)
                    amt = contract["amount"]
                    exp = "部门经理→财务总监→CFO→法务" if amt >= 500000 else "部门经理→财务总监" if amt >= 50000 else "部门经理"
                    actions.append({"id": aid, "type": "fix_contract_type", "title": "修正审批流",
                                    "desc": f"按金额 {_fmt(amt)} 重新提交 {contract['contract_number']} 审批",
                                    "command": f"请修正合同{contract['contract_number']}的类型为'{po['category']}'并按正确审批流重新提交", "risk": "high"})
        if "重复付款" in cn and "❌" in r:
            for p in _find_payments_by_po(po_number):
                if p["status"] == "待审批":
                    aid = f"freeze_{p['payment_number']}"
                    if aid not in seen_ids:
                        seen_ids.add(aid)
                        actions.append({"id": aid, "type": "freeze_payment", "title": "冻结可疑付款",
                                        "desc": f"冻结 {p['payment_number']}（{_fmt(p['amount'])}），疑似重复",
                                        "command": f"请立即冻结付款{p['payment_number']}，原因：疑似重复付款", "risk": "high"})
        if "超合同金额" in cn and ("❌" in r or "⚠️" in r):
            for p in _find_payments_by_po(po_number):
                if p["status"] == "待审批":
                    aid = f"freeze_over_{p['payment_number']}"
                    if aid not in seen_ids:
                        seen_ids.add(aid)
                        actions.append({"id": aid, "type": "freeze_payment", "title": "冻结超额付款",
                                        "desc": f"冻结 {p['payment_number']}（{_fmt(p['amount'])}），超合同金额",
                                        "command": f"请冻结付款{p['payment_number']}，原因：超合同金额", "risk": "high"})
    return actions


# ════════════════════════════════════════════════════════════════
#  LLM & AGENT
# ════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是宝尊电商集团风控部的AI智能助手，代号"宝尊风控Agent"。你服务于集团风控部及财务大中心团队；回复中不要称呼或提及任何具体个人姓名，用「您」「风控团队」「相关负责人」等通用称谓即可。

## 核心能力
你可以同时访问以下系统和功能：
1. **采购系统** — 查询采购申请、供应商信息
2. **OA合同系统** — 查询合同签署、审批状态、条款审查
3. **OA付款系统** — 查询付款申请、付款记录
4. **异常工单系统** — 创建、更新、查询异常工单
5. **飞书推送** — 向相关责任人推送实时预警通知
6. **一键整改** — 修正合同类型、冻结付款、补提采购申请
7. **供应商画像** — 查询供应商信用评分、历史合同、关联企业；单 PO 用围标检测，**全量/所有供应商围标风险用 scan_all_bid_rigging_risks 一次扫完**
8. **发票深度校验** — 发票验真、连号检测、税率校验、税额计算校验
9. **验收人独立性** — 检查采购申请人与验收人是否违反不相容职务分离原则
10. **预算管理** — 查询预算编制、额度管控、执行率分析
11. **交付跟踪** — 查询订单交付进度、延迟预警
12. **资产管理** — 查询固定资产/长期待摊费用台账、折旧信息
13. **合同条款审查** — 审查预付比例、验收条款、违约条款、保密条款等
14. **审计底稿导出** — 一键生成包含全流程追踪的审计底稿

## 主动引导原则
- 发现异常后，**不要只描述问题，要主动告知用户你可以一键修复**
- 对于高风险问题（重复付款、超合同金额），直接建议"我可以立即冻结该付款，是否确认？"
- 对于合同类型错误，直接建议"我可以一键修正合同类型并重新提交审批，是否确认？"
- 对于缺少采购申请，直接建议"我可以为该采购单补提采购申请，是否确认？"
- 用户确认后，立即调用对应的修复工具执行
- 每次回复结尾给出2-3个后续建议动作
- 用户问供应商时，主动查询供应商画像和围标串标检测
- 用户问合同时，主动进行条款审查
- 用户问发票时，主动进行深度校验
- 用户问审计时，主动建议导出审计底稿
- 语气果断专业，像一个有经验的风控总监助理

## 工作准则
- **工具迭代有限**：全量/所有供应商/全库围标串标类问题，**必须优先一次性调用 `scan_all_bid_rigging_risks`**；仅当用户明确给出 PO 号时用 `detect_bid_rigging`。拿到足够数据后**立即停止重复工具调用**，直接输出结论。
- **并行工具（必守）**：若同一分析需要采购、合同、付款、验收、发票等多源数据，请在**同一条 assistant 回复里并行发起多个 tool_call**，不要「一轮只调一个工具」空转多轮；一般 **3～6 轮**内应进入最终文字结论。
- 收到查询时，**主动调用工具**查询相关系统数据，不要凭空回答
- 发现异常时，给出**具体的风险等级和处理建议**
- 回答格式要清晰专业，使用表格、列表等结构化呈现
- 金额使用 ¥ 符号，保留整数
- 当用户要求生成报告时，调用 generate_risk_report 工具生成HTML报告
- 当用户要求审计底稿时，调用 generate_audit_workpaper 工具
- 当用户确认整改操作时，立即调用 fix_contract_type / freeze_payment / supplement_purchase_request

## 风控规则（10阶段全流程覆盖 + 横向审视）
- **❶预算管控**：预算执行率>90%预警，超预算禁止下单
- **❷采购申请**：所有非经营性采购必须先有采购申请(PR)；拆单规避检测（同部门30天内多笔<5万采购）
- **❸供应商管控**：信用评分<70预警，关联供应商围标检测，中标率异常检测
- **❹合同审查**：合同类型校验、预付比例≤30%、必须包含验收/违约/保密条款
- **❺交付跟踪**：延迟>3天预警，触发违约金条款检查
- **❻验收独立性**：采购申请人≠验收人（不相容职务分离）
- **❼发票校验**：验真、连号检测、发票重复检测（代码+号码唯一性）、税率校验（装修9%/IT设备13%/服务6%）
- **❽三单匹配**：数量差异≤2%，单价差异≤1%，税率必须100%一致
- **❾付款检测**：重复付款、超合同金额、先付后审检测、异常时间付款（周末/节假日）、审批流金额分级
- **❿资产入账**：采购完成后核查资产入账、折旧计提
- **工单闭环时限**：数量/税率不符T+3天，单价不符T+5天，缺票/错票T+10天"""

def _make_llm(api_key: str):
    """支持 DeepSeek 默认端点，或通过 LLM_OPENAI_API_BASE + LLM_MODEL 对接火山引擎/千问等 OpenAI 兼容接口。"""
    base = (
        os.getenv("LLM_OPENAI_API_BASE", "").strip()
        or os.getenv("OPENAI_API_BASE", "").strip()
        or "https://api.deepseek.com"
    )
    model = (
        os.getenv("LLM_MODEL", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
        or "deepseek-chat"
    )
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base,
        temperature=0.3,
        request_timeout=60,
    )


TOOLS = [query_procurement_system, query_contract_system, query_payment_system,
         run_full_risk_check, search_all_anomalies, get_monthly_summary, generate_risk_report,
         create_work_order, list_work_orders, update_work_order, push_feishu_notification,
         fix_contract_type, freeze_payment, supplement_purchase_request,
         query_supplier_profile, detect_bid_rigging, scan_all_bid_rigging_risks, check_invoice_deep,
         check_acceptor_independence, query_budget, track_delivery, query_assets,
         review_contract_clauses, generate_audit_workpaper,
         detect_split_orders, check_payment_anomaly]
TOOL_MAP = {t.name: t for t in TOOLS}

# 单次用户消息内 LLM↔工具循环上限（每轮可含多个并行 tool_call）。可通过环境变量覆盖。
# 默认取 36（复杂任务建议在 32～40；上限见 get_agent_max_iterations 钳制）
_DEFAULT_AGENT_MAX_ITER = 36


def get_agent_max_iterations() -> int:
    raw = os.getenv("AGENT_MAX_ITERATIONS", "").strip()
    if raw.isdigit():
        return max(10, min(int(raw), 80))
    return _DEFAULT_AGENT_MAX_ITER


async def run_agent_stream(user_message: str, history: list, api_key: str | None = None):
    """Run the agent with tool calling. Yields SSE event dicts.
    api_key: 请求头传入优先，否则读环境变量 DEEPSEEK_API_KEY。
    """
    resolved = (
        (api_key or "").strip()
        or os.getenv("LLM_API_KEY", "").strip()
        or os.getenv("DEEPSEEK_API_KEY", "").strip()
    )
    if not resolved:
        yield {
            "type": "error",
            "content": "未配置大模型 API Key。请在「产品设置」填写，或配置环境变量 LLM_API_KEY / DEEPSEEK_API_KEY。",
        }
        yield {"type": "done"}
        return

    llm = _make_llm(resolved)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    try:
        async for event in _agent_with_tools(messages, llm):
            yield event
    except Exception as e:
        yield {"type": "tool_start", "name": "fallback_mode", "input": f"工具调用异常({type(e).__name__})，切换到上下文注入模式"}
        yield {"type": "tool_end", "name": "fallback_mode"}
        async for event in _agent_fallback(user_message, messages, llm):
            yield event


async def _agent_with_tools(messages, llm):
    """Primary path: LangChain tool calling."""
    llm_with_tools = llm.bind_tools(TOOLS)
    pending_actions = []
    max_iter = get_agent_max_iterations()

    for _ in range(max_iter):
        response = await llm_with_tools.ainvoke(messages)

        if response.tool_calls:
            messages.append(response)
            for tc in response.tool_calls:
                name = tc["name"]
                args = tc["args"]
                yield {"type": "tool_start", "name": name, "input": json.dumps(args, ensure_ascii=False)}

                try:
                    tool_fn = TOOL_MAP[name]
                    result = tool_fn.invoke(args)
                except Exception as e:
                    result = f"工具执行错误: {str(e)}"

                yield {"type": "tool_end", "name": name}
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

                if name == "run_full_risk_check":
                    pending_actions.extend(_extract_fix_actions(str(result)))

                report_match = re.search(r"/reports/[\w\-.]+\.html", str(result))
                if report_match:
                    yield {"type": "report", "url": report_match.group(0)}
        else:
            content = response.content or ""
            chunk_size = 4
            for i in range(0, len(content), chunk_size):
                yield {"type": "token", "content": content[i:i + chunk_size]}
                await asyncio.sleep(0.01)
            if pending_actions:
                yield {"type": "actions", "items": pending_actions}
            yield {"type": "done"}
            return

    yield {"type": "tool_start", "name": "fallback_mode", "input": json.dumps({"reason": "max_iterations", "cap": max_iter}, ensure_ascii=False)}
    yield {"type": "tool_end", "name": "fallback_mode"}
    yield {
        "type": "token",
        "content": (
            "\n\n> 本轮工具调用已达系统上限（"
            + str(max_iter)
            + " 轮）。正在根据**已返回的工具数据**自动汇总答复；"
            "如需更深核查，请分步提问或指定具体采购单号 / 供应商编号。\n\n"
        ),
    }
    synth = HumanMessage(
        content=(
            "【系统指令】工具轮次已达上限，禁止再调用任何工具。"
            "请仅根据本对话中已有 ToolMessage 的返回内容，用中文输出完整、结构化的风控分析最终答复；"
            "不得编造工具结果中未出现的数据。"
            "若关键字段仍缺失，在末尾用简短列表说明建议用户下一步如何提问。"
        )
    )
    try:
        final = await llm.ainvoke(messages + [synth])
        text = (final.content or "").strip()
        if text:
            chunk_size = 4
            for i in range(0, len(text), chunk_size):
                yield {"type": "token", "content": text[i : i + chunk_size]}
                await asyncio.sleep(0.01)
        else:
            yield {"type": "token", "content": "（模型未返回汇总正文）请尝试缩小问题范围或分步提问。"}
    except Exception as e:
        yield {"type": "token", "content": f"\n\n汇总阶段出错：{str(e)}。请稍后重试或简化问题。"}
    yield {"type": "done"}


async def _agent_fallback(user_message: str, messages: list, llm):
    """Fallback: inject context from keyword matching, then simple chat."""
    context_parts = []

    po_matches = re.findall(r'PO-\d{4}-\d{3}', user_message)
    sc_matches = re.findall(r'SC-\d{4}-\d{3}', user_message)
    pay_matches = re.findall(r'PAY-\d{4}-\d{3}', user_message)

    for po in po_matches:
        if po in PROCUREMENT_DB:
            context_parts.append(f"[采购系统] {json.dumps(PROCUREMENT_DB[po], ensure_ascii=False)}")
            c = _find_contract_by_po(po)
            if c:
                context_parts.append(f"[OA合同系统] {json.dumps(c, ensure_ascii=False)}")
            pays = _find_payments_by_po(po)
            if pays:
                context_parts.append(f"[OA付款系统] {json.dumps(pays, ensure_ascii=False)}")
            acc = _find_acceptance_by_po(po)
            if acc:
                context_parts.append(f"[验收记录] {json.dumps(acc, ensure_ascii=False)}")
            inv = _find_invoice_by_po(po)
            if inv:
                context_parts.append(f"[发票信息] {json.dumps(inv, ensure_ascii=False)}")

    for sc in sc_matches:
        if sc in CONTRACT_DB:
            context_parts.append(f"[OA合同系统] {json.dumps(CONTRACT_DB[sc], ensure_ascii=False)}")
    for pay in pay_matches:
        if pay in PAYMENT_DB:
            context_parts.append(f"[OA付款系统] {json.dumps(PAYMENT_DB[pay], ensure_ascii=False)}")

    keywords_anomaly = ["异常", "风险", "预警", "问题", "跳过", "重复"]
    keywords_summary = ["月报", "报告", "统计", "汇总", "总结"]

    if any(k in user_message for k in keywords_anomaly):
        data = search_all_anomalies.invoke({"risk_level": "all"})
        context_parts.append(f"[异常检索结果] {data}")
    if any(k in user_message for k in keywords_summary):
        data = get_monthly_summary.invoke({})
        context_parts.append(f"[月度统计] {data}")
    if "生成" in user_message and "报告" in user_message:
        result = generate_risk_report.invoke({"report_title": "非经营性采购内控报告"})
        context_parts.append(f"[报告生成结果] {result}")
        report_match = re.search(r"/reports/[\w\-.]+\.html", result)
        if report_match:
            yield {"type": "report", "url": report_match.group(0)}

    if context_parts:
        yield {"type": "tool_start", "name": "auto_data_query", "input": "自动检索相关系统数据"}
        yield {"type": "tool_end", "name": "auto_data_query"}

    enhanced = user_message
    if context_parts:
        enhanced += "\n\n--- 以下是从各系统自动查询到的数据 ---\n" + "\n".join(context_parts)

    final_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    final_messages.append(HumanMessage(content=enhanced))

    try:
        async for chunk in llm.astream(final_messages):
            if chunk.content:
                yield {"type": "token", "content": chunk.content}
        yield {"type": "done"}
    except Exception as e:
        yield {"type": "token", "content": f"\n\n❌ API调用失败: {str(e)}"}
        yield {"type": "done"}


# ════════════════════════════════════════════════════════════════
#  DASHBOARD DATA (for frontend API)
# ════════════════════════════════════════════════════════════════

def get_dashboard_data():
    anomalies_raw = json.loads(search_all_anomalies.invoke({"risk_level": "all"}))
    summary_raw = json.loads(get_monthly_summary.invoke({}))

    exceptions = []
    for a in anomalies_raw:
        contract = _find_contract_by_po(a["po_number"])
        exceptions.append({
            "id": a["po_number"],
            "po": a["po_number"],
            "title": a["title"],
            "type": a["issues"][0] if isinstance(a["issues"][0], str) else a["issues"][0],
            "level": a["risk_level"],
            "amount": a["amount"],
            "dept": a["department"],
            "date": a["date"],
            "contract": contract["contract_number"] if contract else "—",
            "supplier": PROCUREMENT_DB[a["po_number"]]["supplier"],
        })

    pending_payments = [p for p in PAYMENT_DB.values() if p["status"] == "待审批"]

    three_doc_pass, three_doc_total = 0, 0
    for po_number in PROCUREMENT_DB:
        c = _find_contract_by_po(po_number)
        a = _find_acceptance_by_po(po_number)
        i = _find_invoice_by_po(po_number)
        if c and a and i:
            three_doc_total += 1
            diff = abs(PROCUREMENT_DB[po_number]["amount"] - i["amount"]) / PROCUREMENT_DB[po_number]["amount"] * 100
            if diff <= 1 and a["qty_received"] == a["qty_ordered"]:
                three_doc_pass += 1

    return {
        "summary": {
            "total_po": summary_raw["total_purchases"],
            "total_amount": summary_raw["total_amount"],
            "anomaly_count": len(exceptions),
            "high_risk": sum(1 for e in exceptions if e["level"] == "high"),
            "medium_risk": sum(1 for e in exceptions if e["level"] == "medium"),
            "low_risk": sum(1 for e in exceptions if e["level"] == "low"),
            "pending_payment": len(pending_payments),
            "pending_amount": sum(p["amount"] for p in pending_payments),
            "three_doc_pass": three_doc_pass,
            "three_doc_total": three_doc_total,
        },
        "exceptions": exceptions,
        "pending_payments": [{
            "id": p["payment_number"], "contract": p["contract_number"],
            "desc": p["desc"], "amount": p["amount"],
            "payee": p["payee"], "date": p["apply_date"],
            "risk": "high" if any(
                pp["payee"] == p["payee"] and pp["amount"] == p["amount"] and pp["payment_number"] != p["payment_number"]
                for pp in PAYMENT_DB.values()
            ) else "medium",
        } for p in pending_payments],
        "work_orders": list(WORKORDER_DB.values()),
        "notifications": NOTIFICATION_LOG[-10:],
    }


def get_work_orders():
    return list(WORKORDER_DB.values())


def get_notifications():
    return NOTIFICATION_LOG


def get_suppliers():
    return list(SUPPLIER_DB.values())


def get_budgets():
    for code, b in BUDGET_DB.items():
        b["usage_rate"] = round(b["used"] / b["q_budget"] * 100, 1) if b["q_budget"] > 0 else 0
        b["status"] = "超预算" if b["available"] < 0 else ("预算紧张" if b["usage_rate"] > 80 else "正常")
    return list(BUDGET_DB.values())


def get_deliveries():
    results = []
    for po_num, d in DELIVERY_DB.items():
        po = PROCUREMENT_DB.get(po_num, {})
        results.append({**d, "title": po.get("title", ""), "supplier": po.get("supplier", "")})
    return results


def get_assets():
    return list(ASSET_DB.values())

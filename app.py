import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

app = FastAPI(title="宝尊风控AI Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        k = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not k:
            raise ValueError("请设置环境变量 DEEPSEEK_API_KEY（勿将密钥写入代码或提交仓库）")
        _openai_client = OpenAI(api_key=k, base_url="https://api.deepseek.com")
    return _openai_client

SYSTEM_PROMPT = """你是宝尊电商集团风控部的AI智能助手，代号"风控Agent"。你直接服务于集团风控部总监张文洁及其团队。

## 你的核心能力
1. **跨系统信息串联**：同时访问采购系统、OA合同系统、OA付款系统的数据，将散落在三个系统的信息串成完整链条
2. **三单匹配检查**：自动对比采购订单(PO)、入库验收单、供应商发票（数量差异≤2%，单价差异≤1%，税率差异=0%）
3. **四流一致性校验**：检查合同流、资金流、发票流、物流的主体一致性（金税四期核心要求）
4. **风险识别与预警**：发现跳过采购申请、合同类型错误、重复付款、超合同付款等风险
5. **报告生成**：生成内控报告、审计底稿

## 宝尊业务背景
- 宝尊电商(BEC)：电商代运营，2025年营收~73亿，服务450+品牌
- 品牌管理(BBM)：GAP大中华区164家+HUNTER东南亚177家门店，2025年营收~6.6亿（+24%）
- 港股(9991.HK)+美股(BZUN)双上市，需满足港交所、SEC合规要求
- 技术底座：BOCDOP宝舵，800人技术团队，已部署火山引擎和千问大模型

## 当前系统数据（模拟）

### 📦 采购系统
| PO编号 | 项目名称 | 部门 | 类别 | 金额(元) | 供应商 | 供应商编号 | 申请日期 | 审批日期 | 状态 | 有采购申请 | 预算编码 |
|--------|---------|------|------|---------|--------|----------|---------|---------|------|-----------|---------|
| PO-2026-001 | GAP上海淮海路旗舰店装修工程 | BBM-GAP事业部 | 非经营性-门店装修 | 1,500,000 | 上海锦程建筑装饰工程有限公司 | SUP-088 | 2026-02-15 | 2026-02-18 | 已审批 | ✅是 | BBM-GAP-CAPEX-2026 |
| PO-2026-002 | HUNTER南京东路店LED照明改造 | BBM-HUNTER事业部 | 非经营性-门店改造 | 280,000 | 南京光辉照明科技有限公司 | SUP-102 | 2026-02-20 | 2026-02-22 | 已审批 | ✅是 | BBM-HT-CAPEX-2026 |
| PO-2026-003 | 技术部Dell服务器采购(5台) | BEC-技术部 | 非经营性-IT设备 | 500,000 | 上海戴尔科技有限公司 | SUP-015 | 2026-03-01 | 2026-03-03 | 已审批 | ✅是 | BEC-IT-CAPEX-2026 |
| PO-2026-004 | 市场部办公家具采购 | BEC-市场部 | 非经营性-办公用品 | 32,000 | 上海美宜家具有限公司 | SUP-156 | 2026-03-05 | 2026-03-05 | 已审批 | ❌否(跳过采购申请) | BEC-MKT-OPEX-2026 |
| PO-2026-005 | GAP成都太古里店装修工程 | BBM-GAP事业部 | 非经营性-门店装修 | 980,000 | 成都锦华装饰工程有限公司 | SUP-201 | 2026-03-08 | 2026-03-10 | 已审批 | ✅是 | BBM-GAP-CAPEX-2026 |
| PO-2026-006 | IT部ThinkPad笔记本采购(20台) | BEC-技术部 | 非经营性-IT设备 | 200,000 | 上海联拓科技有限公司 | SUP-078 | 2026-03-10 | 2026-03-12 | 已审批 | ✅是 | BEC-IT-CAPEX-2026 |
| PO-2026-007 | HUNTER杭州湖滨银泰店营销物料 | BBM-HUNTER事业部 | 非经营性-营销物料 | 85,000 | 杭州创意印务有限公司 | SUP-167 | 2026-03-15 | 2026-03-16 | 已审批 | ✅是 | BBM-HT-MKT-2026 |
| PO-2026-008 | GAP北京三里屯店翻新 | BBM-GAP事业部 | 非经营性-门店装修 | 1,200,000 | 北京恒达建设有限公司 | SUP-215 | 2026-03-18 | 2026-03-20 | 待审批 | ✅是 | BBM-GAP-CAPEX-2026 |

### 📑 OA合同系统
| 合同编号 | 关联PO | 合同名称 | 合同类型 | 合同金额(元) | 供应商 | 签订日期 | 有效期至 | 审批状态 | 审批人 |
|---------|--------|---------|---------|------------|--------|---------|---------|---------|--------|
| SC-2026-001 | PO-2026-001 | GAP淮海路店装修施工合同 | 非经营性采购合同 | 1,500,000 | 上海锦程建筑装饰工程有限公司 | 2026-02-20 | 2026-08-20 | 已审批 | 李明(部门经理)→王芳(财务总监)→张文洁(风控总监) |
| SC-2026-002 | PO-2026-002 | HUNTER南京店LED改造合同 | 非经营性采购合同 | 280,000 | 南京光辉照明科技有限公司 | 2026-02-25 | 2026-06-25 | 已审批 | 陈华(部门经理)→王芳(财务总监) |
| SC-2026-003 | PO-2026-003 | Dell服务器采购合同 | 非经营性采购合同 | 500,000 | 上海戴尔科技有限公司 | 2026-03-05 | 2026-09-05 | 已审批 | 刘强(技术总监)→王芳(财务总监)→张文洁(风控总监) |
| SC-2026-004 | 无(PO-2026-004未关联) | 办公家具采购协议 | ⚠️经营性采购合同(类型错误，应为非经营性) | 35,000 | 上海美宜家具有限公司 | 2026-03-06 | 2026-06-06 | 已审批 | 赵刚(市场经理) |
| SC-2026-005 | PO-2026-005 | GAP太古里店装修施工合同 | ⚠️经营性采购合同(类型错误，应为非经营性) | 980,000 | 成都锦华装饰工程有限公司 | 2026-03-12 | 2026-09-12 | 已审批 | 李明(部门经理)→王芳(财务总监) |
| SC-2026-006 | PO-2026-006 | ThinkPad笔记本采购合同 | 非经营性采购合同 | 200,000 | 上海联拓科技有限公司 | 2026-03-14 | 2026-06-14 | 已审批 | 刘强(技术总监)→王芳(财务总监) |
| SC-2026-007 | PO-2026-007 | HUNTER杭州店营销物料制作合同 | 非经营性采购合同 | 85,000 | 杭州创意印务有限公司 | 2026-03-18 | 2026-05-18 | 已审批 | 陈华(部门经理) |

### 💳 OA付款系统
| 付款编号 | 关联合同 | 付款事由 | 付款金额(元) | 收款方 | 付款日期 | 状态 | 发起人 | 发票号 | 发票金额(元) |
|---------|--------|---------|------------|--------|---------|------|--------|--------|------------|
| PAY-2026-001 | SC-2026-001 | GAP淮海路店装修首期款(30%) | 450,000 | 上海锦程建筑装饰工程有限公司 | 2026-03-01 | 已付 | 李明 | INV-20260301-001 | 450,000 |
| PAY-2026-002 | SC-2026-002 | HUNTER南京店LED改造全款 | 280,000 | 南京光辉照明科技有限公司 | 2026-03-05 | 已付 | 陈华 | INV-20260305-001 | 280,000 |
| PAY-2026-003 | SC-2026-003 | Dell服务器采购全款 | 500,000 | 上海戴尔科技有限公司 | 2026-03-10 | 已付 | 刘强 | INV-20260310-001 | 500,000 |
| PAY-2026-004 | SC-2026-004 | 办公家具采购款 | 35,000 | 上海美宜家具有限公司 | 2026-03-11 | 已付 | 赵刚 | INV-20260311-001 | 35,000 |
| PAY-2026-005 | SC-2026-001 | GAP淮海路店装修二期款(40%) | 600,000 | 上海锦程建筑装饰工程有限公司 | 2026-03-15 | 已付 | 李明 | INV-20260315-001 | 600,000 |
| PAY-2026-006 | SC-2026-006 | ThinkPad笔记本采购全款 | 200,000 | 上海联拓科技有限公司 | 2026-03-16 | 已付 | 刘强 | INV-20260316-001 | 200,000 |
| PAY-2026-007 | SC-2026-006 | ⚠️ThinkPad笔记本采购全款(疑似重复付款) | 200,000 | 上海联拓科技有限公司 | 2026-03-18 | 待审批 | 张伟 | INV-20260318-001 | 200,000 |
| PAY-2026-008 | SC-2026-005 | GAP太古里店装修首期款 | 400,000 | 成都锦华装饰工程有限公司 | 2026-03-20 | 待审批 | 李明 | INV-20260320-001 | 400,000 |
| PAY-2026-009 | SC-2026-007 | HUNTER杭州店营销物料制作款 | 85,000 | 杭州创意印务有限公司 | 2026-03-22 | 待审批 | 陈华 | INV-20260322-001 | 88,500 |

### 📋 入库验收记录
| 验收编号 | 关联PO | 验收内容 | 验收数量 | 验收金额(元) | 验收日期 | 验收人 |
|---------|--------|---------|---------|------------|---------|--------|
| RCV-2026-001 | PO-2026-001 | GAP淮海路店装修一期 | 1批 | 450,000 | 2026-02-28 | 周明 |
| RCV-2026-002 | PO-2026-002 | LED照明设备安装 | 1套 | 280,000 | 2026-03-03 | 王磊 |
| RCV-2026-003 | PO-2026-003 | Dell R750xs服务器 | 5台 | 500,000 | 2026-03-08 | 陈涛 |
| RCV-2026-004 | PO-2026-006 | ThinkPad X1 Carbon | 20台 | 200,000 | 2026-03-15 | 陈涛 |
| RCV-2026-005 | PO-2026-007 | 营销物料 | 1批 | 85,000 | 2026-03-20 | 李娜 |

## ⚠️ 已识别的风险清单
1. 🔴 **PO-2026-004 跳过采购申请**：市场部办公家具采购没有走前序采购申请流程，直接进入合同签署。违反内控规定。
2. 🔴 **SC-2026-004 合同类型错误**：办公家具合同类型选择了"经营性采购合同"，应为"非经营性采购合同"。影响审批流和统计归类。
3. 🔴 **SC-2026-005 合同类型错误**：GAP太古里店装修合同类型选择了"经营性采购合同"，应为"非经营性采购合同"。金额高达98万，风险较大。
4. 🔴 **PAY-2026-007 疑似重复付款**：ThinkPad笔记本采购，SC-2026-006合同金额20万已由PAY-2026-006全额支付，PAY-2026-007又以不同发起人(张伟)发起相同金额付款。高度疑似重复付款。
5. 🟡 **PAY-2026-009 三单匹配异常**：HUNTER杭州店营销物料，采购金额85,000元，发票金额88,500元，差异4.12%，超过1%阈值。需人工确认。
6. 🟡 **PAY-2026-004 金额异常**：合同金额35,000元 > 采购申请金额32,000元，差异9.4%，需确认是否含额外费用。
7. 🟢 **PO-2026-008 待审批**：GAP北京三里屯店翻新，金额120万，尚未完成审批流程。

## 回复要求
1. 用专业但易懂的中文回复
2. 查询结果用表格或结构化格式展示
3. 风险用 🔴高风险 🟡中风险 🟢低风险 标注
4. 给出具体、可执行的风控建议
5. 回复要简洁有力，不要啰嗦
6. 展示数据时说明是从哪个系统查询的（采购系统/OA合同系统/OA付款系统）
7. 进行三单匹配时明确列出三个单据的对比结果
8. 如果用户问的信息不在数据中，如实说明
"""


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    def generate():
        try:
            response = _get_openai_client().chat.completions.create(
                model="deepseek-chat",
                messages=full_messages,
                stream=True,
                temperature=0.7,
                max_tokens=4096,
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    payload = json.dumps(
                        {"content": chunk.choices[0].delta.content},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


MOCK_DASHBOARD = {
    "summary": {
        "total_po": 8, "total_amount": 4777000,
        "anomaly_count": 5, "high_risk": 2, "medium_risk": 2, "low_risk": 1,
        "pending_payment": 3, "pending_amount": 685000,
    },
    "exceptions": [
        {"id":"EX-001","type":"跳过采购申请","level":"high","po":"PO-2026-004","desc":"市场部办公家具采购未走采购申请流程","amount":32000,"dept":"BEC-市场部","date":"2026-03-05","status":"待处理","contract":"SC-2026-004","supplier":"上海美宜家具有限公司"},
        {"id":"EX-002","type":"合同类型错误","level":"high","po":"PO-2026-005","desc":"GAP成都太古里店装修合同类型选择为经营性(应为非经营性)","amount":980000,"dept":"BBM-GAP事业部","date":"2026-03-08","status":"待处理","contract":"SC-2026-005","supplier":"成都锦华装饰工程有限公司"},
        {"id":"EX-003","type":"合同类型错误","level":"medium","po":"PO-2026-004","desc":"办公家具合同类型为经营性(应为非经营性)，且合同金额35,000>采购32,000","amount":35000,"dept":"BEC-市场部","date":"2026-03-06","status":"待处理","contract":"SC-2026-004","supplier":"上海美宜家具有限公司"},
        {"id":"EX-004","type":"疑似重复付款","level":"high","po":"PO-2026-006","desc":"ThinkPad笔记本采购已由PAY-2026-006全额付20万,PAY-2026-007又发起相同金额","amount":200000,"dept":"BEC-技术部","date":"2026-03-18","status":"待审批","contract":"SC-2026-006","supplier":"上海联拓科技有限公司"},
        {"id":"EX-005","type":"三单匹配异常","level":"medium","po":"PO-2026-007","desc":"营销物料采购金额85,000 vs 发票金额88,500，差异4.12%超1%阈值","amount":85000,"dept":"BBM-HUNTER事业部","date":"2026-03-22","status":"待审批","contract":"SC-2026-007","supplier":"杭州创意印务有限公司"},
        {"id":"EX-006","type":"待审批","level":"low","po":"PO-2026-008","desc":"GAP北京三里屯店翻新，金额120万，尚未完成审批流程","amount":1200000,"dept":"BBM-GAP事业部","date":"2026-03-18","status":"待审批","contract":"—","supplier":"北京恒达建设有限公司"},
    ],
    "recent_payments": [
        {"id":"PAY-2026-007","contract":"SC-2026-006","desc":"ThinkPad笔记本(疑似重复)","amount":200000,"payee":"上海联拓科技有限公司","date":"2026-03-18","status":"待审批","risk":"high"},
        {"id":"PAY-2026-008","contract":"SC-2026-005","desc":"GAP太古里装修首期款","amount":400000,"payee":"成都锦华装饰工程有限公司","date":"2026-03-20","status":"待审批","risk":"medium"},
        {"id":"PAY-2026-009","contract":"SC-2026-007","desc":"HUNTER杭州营销物料","amount":85000,"payee":"杭州创意印务有限公司","date":"2026-03-22","status":"待审批","risk":"medium"},
    ],
    "monthly_report": {
        "period": "2026年3月",
        "total_purchases": 8, "total_amount": 4777000,
        "departments": ["BBM-GAP事业部","BBM-HUNTER事业部","BEC-技术部","BEC-市场部"],
        "high_risk_items": [
            {"type":"跳过采购申请","count":1,"amount":32000},
            {"type":"疑似重复付款","count":1,"amount":200000},
        ],
        "medium_risk_items": [
            {"type":"合同类型错误","count":2,"amount":1015000},
            {"type":"三单匹配异常","count":1,"amount":85000},
        ],
        "three_doc_summary": {"checked":6,"passed":5,"failed":1},
        "four_flow_summary": {"checked":6,"passed":6,"failed":0},
    }
}


@app.get("/api/dashboard")
async def dashboard():
    return MOCK_DASHBOARD


@app.get("/")
async def index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8766)

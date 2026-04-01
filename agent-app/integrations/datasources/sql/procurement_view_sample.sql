-- SelectDB / MySQL 只读视图示例（列名 snake_case，与 mapper 一致）
-- 在数仓中落地为视图后，将 SELECTDB_PROCUREMENT_SQL 指向本 SQL 或简写为 SELECT * FROM vw_risk_procurement_po;

CREATE OR REPLACE VIEW vw_risk_procurement_po AS
SELECT
    po_number,
    title,
    category,
    department,
    applicant,
    supplier,
    supplier_id,
    amount,
    apply_date,
    status,
    has_purchase_request,
    pr_number,
    budget_code,
    budget_total,
    budget_used
FROM dwd_procurement_po_detail
WHERE biz_type = 'NON_OPERATING';

-- 运行时最小查询（环境变量 SELECTDB_PROCUREMENT_SQL 可只写下面一行）：
-- SELECT po_number, title, category, department, applicant, supplier, supplier_id, amount, apply_date, status, has_purchase_request, pr_number, budget_code, budget_total, budget_used FROM vw_risk_procurement_po;

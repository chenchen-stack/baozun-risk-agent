"""采购数据源适配层：mock / HTTP REST / SelectDB(MySQL)，合并进 agent.PROCUREMENT_DB。"""

from integrations.datasources.sync import get_procurement_sync_status, sync_procurement_into_agent

__all__ = ["sync_procurement_into_agent", "get_procurement_sync_status"]

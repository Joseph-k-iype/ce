"""
Backup Service
==============
Periodic background tasks and utility methods for backing up and restoring FalkorDB RulesGraph.
Exports graphs as JSON dumps containing node and edge properties.
"""

import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from services.database import get_db_service

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
LATEST_BACKUP_FILE = BACKUP_DIR / "rules_graph_latest.json"

class BackupService:
    def __init__(self):
        self.db = get_db_service()
        self._backup_task = None

    def create_backup(self) -> Dict[str, Any]:
        """Dump the entire RulesGraph into a JSON structure."""
        logger.info("Starting RulesGraph structural backup...")
        
        # 1. Fetch all nodes
        nodes_result = self.db.execute_rules_query("MATCH (n) RETURN id(n) AS node_id, labels(n) AS labels, properties(n) AS props")
        nodes_data = []
        for row in nodes_result:
            nodes_data.append({
                "id": row.get("node_id"),
                "labels": row.get("labels", []),
                "properties": row.get("props", {})
            })

        # 2. Fetch all edges
        edges_result = self.db.execute_rules_query("MATCH (a)-[r]->(b) RETURN id(r) AS edge_id, type(r) AS type, properties(r) AS props, id(a) AS src, id(b) AS dst")
        edges_data = []
        for row in edges_result:
            edges_data.append({
                "id": row.get("edge_id"),
                "type": row.get("type"),
                "src": row.get("src"),
                "dst": row.get("dst"),
                "properties": row.get("props", {})
            })

        backup_payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": nodes_data,
            "edges": edges_data
        }

        # Save to file
        with open(LATEST_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f, indent=2)
            
        logger.info(f"Backup completed. Saved {len(nodes_data)} nodes and {len(edges_data)} edges.")
        return backup_payload

    def restore_backup(self) -> bool:
        """Restore the RulesGraph from the latest JSON dump."""
        if not LATEST_BACKUP_FILE.exists():
            logger.error("No backup file found to restore.")
            raise FileNotFoundError("backup file does not exist")

        with open(LATEST_BACKUP_FILE, "r", encoding="utf-8") as f:
            backup_payload = json.load(f)

        logger.info("Restoring RulesGraph from backup...")
        
        # 1. Wipe current graph
        self.db.execute_rules_query("MATCH (n) DETACH DELETE n")

        # 2. Re-create nodes
        id_mapping = {} # Old ID -> new Internal ID mapping (since internal DB IDs change)
        for node in backup_payload.get("nodes", []):
            labels = ":".join(node["labels"]) if node.get("labels") else "Node"
            prop_str = ", ".join([f"{k}: ${k}" for k in node["properties"].keys()])
            query = f"CREATE (n:{labels} {{{prop_str}}}) RETURN id(n) AS new_id"
            
            res = self.db.execute_rules_query(query, params=node["properties"])
            if res:
                id_mapping[node["id"]] = res[0]["new_id"]

        # 3. Re-create edges
        for edge in backup_payload.get("edges", []):
            src_new = id_mapping.get(edge["src"])
            dst_new = id_mapping.get(edge["dst"])
            
            if src_new is None or dst_new is None:
                continue
                
            prop_str = ", ".join([f"{k}: ${k}" for k in edge["properties"].keys()])
            props_clause = f" {{{prop_str}}}" if prop_str else ""
            rel_type = edge["type"]
            
            params = edge["properties"].copy()
            params["src_id"] = src_new
            params["dst_id"] = dst_new
            
            query = f"""
            MATCH (a), (b) 
            WHERE id(a) = $src_id AND id(b) = $dst_id
            CREATE (a)-[r:{rel_type}{props_clause}]->(b)
            """
            self.db.execute_rules_query(query, params=params)

        logger.info("Graph restoration complete.")
        return True

    async def _periodic_backup_loop(self):
        """Loop running every 30 minutes."""
        while True:
            await asyncio.sleep(30 * 60)  # 30 mins
            try:
                self.create_backup()
            except Exception as e:
                logger.error(f"Automated backup failed: {e}")

    def start_background_task(self):
        """Spawns the asyncio background backup loop."""
        if self._backup_task is None:
            self._backup_task = asyncio.create_task(self._periodic_backup_loop())
            logger.info("Started periodic 30-min backup background task.")

_backup_service_instance = None
def get_backup_service() -> BackupService:
    global _backup_service_instance
    if _backup_service_instance is None:
        _backup_service_instance = BackupService()
    return _backup_service_instance

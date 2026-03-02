"""
Data Sources API Router

Endpoints for managing data source connections and importing to graphs.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import uuid
import os
import shutil

from config.settings import settings

from services.data_source_connector import (
    DataSourceConfig,
    DataSourceType,
    AuthType,
    NodeMapping,
    RelationshipMapping,
    get_data_source_manager
)
from services.graph_import_service import get_graph_import_service

router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])


# Request/Response Models

class DataSourceCreateRequest(BaseModel):
    """Request to create a new data source."""
    name: str
    source_type: DataSourceType
    description: str = ""
    config: Dict[str, Any]
    auth_config: Optional[Dict[str, Any]] = None


class DataSourceResponse(BaseModel):
    """Response with data source details."""
    source_id: str
    name: str
    source_type: DataSourceType
    description: str
    config: Dict[str, Any]
    enabled: bool
    created_at: str


class NodeMappingRequest(BaseModel):
    """Request model for node mapping."""
    node_label: str
    id_field: str
    property_mappings: Dict[str, str]


class RelationshipMappingRequest(BaseModel):
    """Request model for relationship mapping."""
    relationship_type: str
    source_node_label: str
    target_node_label: str
    source_id_field: str
    target_id_field: str
    foreign_key_field: str
    properties: Dict[str, str] = {}


class ImportRequest(BaseModel):
    """Request to import data to graph."""
    source_id: str
    graph_name: str
    node_mappings: List[NodeMappingRequest]
    relationship_mappings: Optional[List[RelationshipMappingRequest]] = None
    clear_existing: bool = False


# Endpoints

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file (CSV/JSON) to be used as a data source."""
    try:
        # Secure the filename
        safe_filename = file.filename.replace(" ", "_")
        unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
        
        # Ensure upload directory exists
        upload_dir = settings.paths.data_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / unique_filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "status": "success",
            "message": "File uploaded successfully",
            "file_path": str(file_path),
            "original_filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.post("/create")
async def create_data_source(request: DataSourceCreateRequest):
    """Create a new data source configuration.

    Supported source types:
    - rest_api: REST API endpoint
    - csv: CSV file
    - json: JSON file

    Example for REST API:
    {
        "name": "External Compliance API",
        "source_type": "rest_api",
        "description": "Third-party compliance data",
        "config": {
            "base_url": "https://api.example.com",
            "data_endpoint": "/compliance/rules",
            "test_endpoint": "/health"
        },
        "auth_config": {
            "type": "bearer_token",
            "token": "your-api-token"
        }
    }

    Example for CSV:
    {
        "name": "Compliance Rules CSV",
        "source_type": "csv",
        "config": {
            "file_path": "/path/to/data.csv"
        }
    }
    """
    try:
        manager = get_data_source_manager()

        # Generate unique source ID
        source_id = f"source_{uuid.uuid4().hex[:8]}"

        # Create configuration
        config = DataSourceConfig(
            source_id=source_id,
            name=request.name,
            source_type=request.source_type,
            description=request.description,
            config=request.config,
            auth_config=request.auth_config or {}
        )

        # Test connection before saving
        connector = None
        if request.source_type == DataSourceType.REST_API:
            from services.data_source_connector import RESTAPIConnector
            connector = RESTAPIConnector(config)
        elif request.source_type == DataSourceType.CSV:
            from services.data_source_connector import CSVConnector
            connector = CSVConnector(config)
        elif request.source_type == DataSourceType.JDBC:
            from services.data_source_connector import JDBCConnector
            connector = JDBCConnector(config)

        if connector:
            success, message = connector.test_connection()
            if not success:
                raise HTTPException(
                    status_code=400,
                    detail=f"Connection test failed: {message}"
                )

        # Register source
        manager.register_source(config)

        return {
            "status": "success",
            "source_id": source_id,
            "message": f"Data source '{request.name}' created successfully",
            "test_result": message if connector else "Not tested"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_data_sources(source_type: Optional[DataSourceType] = None):
    """List all data sources, optionally filtered by type."""
    try:
        manager = get_data_source_manager()
        sources = manager.list_sources(source_type=source_type)

        return {
            "status": "success",
            "count": len(sources),
            "sources": [
                DataSourceResponse(
                    source_id=s.source_id,
                    name=s.name,
                    source_type=s.source_type,
                    description=s.description,
                    config=s.config,
                    enabled=s.enabled,
                    created_at=s.created_at.isoformat()
                ).dict()
                for s in sources
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}")
async def get_data_source(source_id: str):
    """Get data source details."""
    try:
        manager = get_data_source_manager()
        source = manager.get_source(source_id)

        if not source:
            raise HTTPException(status_code=404, detail=f"Data source '{source_id}' not found")

        return {
            "status": "success",
            "source": DataSourceResponse(
                source_id=source.source_id,
                name=source.name,
                source_type=source.source_type,
                description=source.description,
                config=source.config,
                enabled=source.enabled,
                created_at=source.created_at.isoformat()
            ).dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{source_id}")
async def delete_data_source(source_id: str):
    """Delete a data source."""
    try:
        manager = get_data_source_manager()
        success = manager.delete_source(source_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Data source '{source_id}' not found")

        return {
            "status": "success",
            "message": f"Data source '{source_id}' deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{source_id}/test")
async def test_connection(source_id: str):
    """Test connection to a data source."""
    try:
        manager = get_data_source_manager()
        connector = manager.get_connector(source_id)

        if not connector:
            raise HTTPException(status_code=404, detail=f"Data source '{source_id}' not found")

        success, message = connector.test_connection()

        return {
            "status": "success" if success else "failed",
            "connected": success,
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}/schema")
async def get_schema(source_id: str):
    """Get schema/structure of a data source."""
    try:
        manager = get_data_source_manager()
        connector = manager.get_connector(source_id)

        if not connector:
            raise HTTPException(status_code=404, detail=f"Data source '{source_id}' not found")

        schema = connector.get_schema()

        return {
            "status": "success",
            "source_id": source_id,
            "schema": schema
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}/preview")
async def preview_data(source_id: str, limit: int = 100):
    """Preview sample data from a data source."""
    try:
        manager = get_data_source_manager()
        connector = manager.get_connector(source_id)

        if not connector:
            raise HTTPException(status_code=404, detail=f"Data source '{source_id}' not found")

        preview = connector.preview_data(limit=limit)

        return {
            "status": "success",
            "source_id": source_id,
            "preview": {
                "columns": preview.columns,
                "sample_rows": preview.sample_rows,
                "total_count": preview.total_count,
                "data_types": preview.data_types
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_to_graph(request: ImportRequest):
    """Import data from source to graph.

    Example request:
    {
        "source_id": "source_abc123",
        "graph_name": "ComplianceDataGraph",
        "node_mappings": [
            {
                "node_label": "ComplianceRule",
                "id_field": "rule_id",
                "property_mappings": {
                    "name": "name",
                    "description": "description",
                    "country": "country"
                }
            }
        ],
        "clear_existing": false
    }
    """
    try:
        import_service = get_graph_import_service()

        # Convert request models to service models
        node_mappings = [
            NodeMapping(
                node_label=m.node_label,
                id_field=m.id_field,
                property_mappings=m.property_mappings
            )
            for m in request.node_mappings
        ]

        relationship_mappings = None
        if request.relationship_mappings:
            relationship_mappings = [
                RelationshipMapping(
                    relationship_type=r.relationship_type,
                    source_node_label=r.source_node_label,
                    target_node_label=r.target_node_label,
                    source_id_field=r.source_id_field,
                    target_id_field=r.target_id_field,
                    foreign_key_field=r.foreign_key_field,
                    properties=r.properties
                )
                for r in request.relationship_mappings
            ]

        # Execute import
        stats = import_service.import_to_graph(
            source_id=request.source_id,
            graph_name=request.graph_name,
            node_mappings=node_mappings,
            relationship_mappings=relationship_mappings,
            clear_existing=request.clear_existing
        )

        if stats.get("errors"):
            return {
                "status": "partial",
                "message": "Import completed with errors",
                "stats": stats
            }

        return {
            "status": "success",
            "message": f"Imported {stats['nodes_created']} nodes and {stats['relationships_created']} relationships",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/preview")
async def preview_import(
    source_id: str,
    node_mappings: List[NodeMappingRequest]
):
    """Preview what would be imported without executing.

    Shows sample of how data would be mapped to graph nodes.
    """
    try:
        import_service = get_graph_import_service()

        # Convert request models
        mappings = [
            NodeMapping(
                node_label=m.node_label,
                id_field=m.id_field,
                property_mappings=m.property_mappings
            )
            for m in node_mappings
        ]

        preview = import_service.preview_import(
            source_id=source_id,
            node_mappings=mappings
        )

        return {
            "status": "success",
            "preview": preview
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

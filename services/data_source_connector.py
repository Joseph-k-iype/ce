"""
Data Source Connector Service

Generic framework for connecting to external data sources and importing to graphs.
Supports: JDBC databases, REST APIs, GraphQL APIs, CSV/JSON files.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json
import requests
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    """Supported data source types."""
    JDBC = "jdbc"
    REST_API = "rest_api"
    GRAPHQL = "graphql"
    CSV = "csv"
    JSON = "json"


class JDBCDriver(str, Enum):
    """Supported JDBC drivers."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"


class AuthType(str, Enum):
    """Authentication types for APIs."""
    NONE = "none"
    BASIC = "basic"
    BEARER_TOKEN = "bearer_token"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    source_id: str
    name: str
    source_type: DataSourceType
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    auth_config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    enabled: bool = True


@dataclass
class DataPreview:
    """Preview of data from a source."""
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
    total_count: int
    data_types: Dict[str, str]


@dataclass
class NodeMapping:
    """Mapping for how to convert data to graph nodes."""
    node_label: str
    id_field: str  # Which field to use as node ID
    property_mappings: Dict[str, str]  # source_field -> node_property


@dataclass
class RelationshipMapping:
    """Mapping for creating relationships between nodes."""
    relationship_type: str
    source_node_label: str
    target_node_label: str
    source_id_field: str
    target_id_field: str
    foreign_key_field: str  # Field in source that references target
    properties: Dict[str, str] = field(default_factory=dict)


class DataSourceConnector(ABC):
    """Base class for data source connectors."""

    def __init__(self, config: DataSourceConfig):
        self.config = config

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Test if connection is valid. Returns (success, message)."""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get schema/structure of the data source."""
        pass

    @abstractmethod
    def preview_data(self, limit: int = 100) -> DataPreview:
        """Preview sample data from the source."""
        pass

    @abstractmethod
    def fetch_data(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch data from the source."""
        pass


class RESTAPIConnector(DataSourceConnector):
    """Connector for REST APIs."""

    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self.base_url = config.config.get("base_url", "")
        self.auth_type = AuthType(config.auth_config.get("type", "none"))
        self.headers = self._build_headers()

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {"Content-Type": "application/json"}

        if self.auth_type == AuthType.BEARER_TOKEN:
            token = self.config.auth_config.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif self.auth_type == AuthType.API_KEY:
            key_name = self.config.auth_config.get("key_name", "X-API-Key")
            key_value = self.config.auth_config.get("key_value")
            if key_value:
                headers[key_name] = key_value

        return headers

    def test_connection(self) -> Tuple[bool, str]:
        """Test API connection."""
        try:
            endpoint = self.config.config.get("test_endpoint", "/")
            url = f"{self.base_url.rstrip('/')}{endpoint}"

            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code < 400:
                return True, f"Connected successfully (HTTP {response.status_code})"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:200]}"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def get_schema(self) -> Dict[str, Any]:
        """Get API schema (if available via OpenAPI/Swagger)."""
        schema_url = self.config.config.get("schema_url")
        if not schema_url:
            return {"endpoints": [], "note": "No schema URL configured"}

        try:
            response = requests.get(schema_url, headers=self.headers, timeout=10)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch schema: {e}")
            return {"error": str(e)}

    def preview_data(self, limit: int = 100) -> DataPreview:
        """Preview data from API endpoint."""
        endpoint = self.config.config.get("data_endpoint", "/")
        data = self.fetch_data(query=endpoint)[:limit]

        if not data:
            return DataPreview(
                columns=[],
                sample_rows=[],
                total_count=0,
                data_types={}
            )

        # Extract columns from first row
        columns = list(data[0].keys()) if data else []

        # Infer data types
        data_types = {}
        if data:
            first_row = data[0]
            for key, value in first_row.items():
                data_types[key] = type(value).__name__

        return DataPreview(
            columns=columns,
            sample_rows=data[:10],  # Show first 10 rows
            total_count=len(data),
            data_types=data_types
        )

    def fetch_data(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch data from API endpoint."""
        try:
            endpoint = query or self.config.config.get("data_endpoint", "/")
            url = f"{self.base_url.rstrip('/')}{endpoint}"

            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Handle different response structures
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Try common patterns for paginated responses
                for key in ["data", "results", "items", "records"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                # If no list found, wrap dict in list
                return [data]
            else:
                logger.warning(f"Unexpected response type: {type(data)}")
                return []

        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return []


class JDBCConnector(DataSourceConnector):
    """Connector for JDBC databases (PostgreSQL, MySQL, Oracle, SQL Server)."""

    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self.driver = JDBCDriver(config.config.get("driver", "postgresql"))
        self.host = config.config.get("host", "localhost")
        self.port = config.config.get("port", self._get_default_port())
        self.database = config.config.get("database", "")
        self.username = config.auth_config.get("username", "")
        self.password = config.auth_config.get("password", "")

    def _get_default_port(self) -> int:
        """Get default port for database driver."""
        ports = {
            JDBCDriver.POSTGRESQL: 5432,
            JDBCDriver.MYSQL: 3306,
            JDBCDriver.ORACLE: 1521,
            JDBCDriver.SQLSERVER: 1433,
        }
        return ports.get(self.driver, 5432)

    def _get_connection_string(self) -> str:
        """Build database connection string."""
        if self.driver == JDBCDriver.POSTGRESQL:
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.driver == JDBCDriver.MYSQL:
            return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.driver == JDBCDriver.ORACLE:
            return f"oracle://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.driver == JDBCDriver.SQLSERVER:
            return f"mssql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        return ""

    def test_connection(self) -> Tuple[bool, str]:
        """Test database connection."""
        try:
            # Try to connect using psycopg2, pymysql, etc. depending on driver
            # For now, we'll use a simple approach with sqlalchemy
            from sqlalchemy import create_engine, text

            engine = create_engine(self._get_connection_string())

            with engine.connect() as conn:
                # Simple test query
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            return True, f"Connected to {self.driver.value} database successfully"

        except ImportError:
            return False, f"Missing driver for {self.driver.value}. Install: pip install sqlalchemy psycopg2-binary pymysql"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def get_schema(self) -> Dict[str, Any]:
        """Get database schema (tables and columns)."""
        try:
            from sqlalchemy import create_engine, inspect

            engine = create_engine(self._get_connection_string())
            inspector = inspect(engine)

            tables = {}
            for table_name in inspector.get_table_names():
                columns = []
                for column in inspector.get_columns(table_name):
                    columns.append({
                        "name": column["name"],
                        "type": str(column["type"]),
                        "nullable": column.get("nullable", True)
                    })
                tables[table_name] = columns

            return {
                "database": self.database,
                "driver": self.driver.value,
                "tables": tables,
                "table_count": len(tables)
            }

        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return {"error": str(e)}

    def preview_data(self, limit: int = 100) -> DataPreview:
        """Preview data from first available table."""
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self._get_connection_string())

            # Get first table
            schema = self.get_schema()
            tables = schema.get("tables", {})

            if not tables:
                return DataPreview(columns=[], sample_rows=[], total_count=0, data_types={})

            first_table = list(tables.keys())[0]

            # Fetch sample data
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {first_table} LIMIT {limit}"))
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]

            # Infer data types
            data_types = {}
            if rows:
                for col in columns:
                    val = rows[0].get(col)
                    data_types[col] = type(val).__name__ if val is not None else "null"

            return DataPreview(
                columns=columns,
                sample_rows=rows[:10],
                total_count=len(rows),
                data_types=data_types
            )

        except Exception as e:
            logger.error(f"Failed to preview data: {e}")
            return DataPreview(columns=[], sample_rows=[], total_count=0, data_types={})

    def fetch_data(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch data from database using SQL query."""
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self._get_connection_string())

            # If no query provided, select from first table
            if not query:
                schema = self.get_schema()
                tables = schema.get("tables", {})
                if tables:
                    first_table = list(tables.keys())[0]
                    query = f"SELECT * FROM {first_table}"
                else:
                    return []

            with engine.connect() as conn:
                result = conn.execute(text(query))
                columns = list(result.keys())
                return [dict(zip(columns, row)) for row in result.fetchall()]

        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return []


class CSVConnector(DataSourceConnector):
    """Connector for CSV files."""

    def test_connection(self) -> Tuple[bool, str]:
        """Validate CSV file exists and is readable."""
        try:
            import csv
            file_path = self.config.config.get("file_path")

            if not file_path:
                return False, "No file path provided"

            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Try to read header

            return True, "CSV file is valid"

        except FileNotFoundError:
            return False, "File not found"
        except Exception as e:
            return False, f"Invalid CSV: {str(e)}"

    def get_schema(self) -> Dict[str, Any]:
        """Get CSV column names."""
        try:
            import csv
            file_path = self.config.config.get("file_path")

            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames or []

            return {
                "columns": columns,
                "file_path": file_path
            }

        except Exception as e:
            logger.error(f"Failed to read CSV schema: {e}")
            return {"error": str(e)}

    def preview_data(self, limit: int = 100) -> DataPreview:
        """Preview CSV data."""
        data = self.fetch_data()[:limit]

        if not data:
            return DataPreview(
                columns=[],
                sample_rows=[],
                total_count=0,
                data_types={}
            )

        columns = list(data[0].keys())

        # Infer data types
        data_types = {}
        if data:
            for key, value in data[0].items():
                # Try to infer type
                if value.isdigit():
                    data_types[key] = "int"
                else:
                    try:
                        float(value)
                        data_types[key] = "float"
                    except ValueError:
                        data_types[key] = "str"

        return DataPreview(
            columns=columns,
            sample_rows=data[:10],
            total_count=len(data),
            data_types=data_types
        )

    def fetch_data(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read all data from CSV."""
        try:
            import csv
            file_path = self.config.config.get("file_path")

            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)

        except Exception as e:
            logger.error(f"Failed to read CSV data: {e}")
            return []


class DataSourceManager:
    """Manages data source configurations and connectors."""

    def __init__(self):
        self._sources: Dict[str, DataSourceConfig] = {}

    def register_source(self, config: DataSourceConfig) -> str:
        """Register a new data source."""
        self._sources[config.source_id] = config
        logger.info(f"Registered data source: {config.name} ({config.source_type})")
        return config.source_id

    def get_source(self, source_id: str) -> Optional[DataSourceConfig]:
        """Get data source configuration."""
        return self._sources.get(source_id)

    def list_sources(self, source_type: Optional[DataSourceType] = None) -> List[DataSourceConfig]:
        """List all data sources, optionally filtered by type."""
        sources = list(self._sources.values())
        if source_type:
            sources = [s for s in sources if s.source_type == source_type]
        return sources

    def delete_source(self, source_id: str) -> bool:
        """Delete a data source."""
        if source_id in self._sources:
            del self._sources[source_id]
            logger.info(f"Deleted data source: {source_id}")
            return True
        return False

    def get_connector(self, source_id: str) -> Optional[DataSourceConnector]:
        """Get a connector instance for a data source."""
        config = self.get_source(source_id)
        if not config:
            return None

        if config.source_type == DataSourceType.REST_API:
            return RESTAPIConnector(config)
        elif config.source_type == DataSourceType.CSV:
            return CSVConnector(config)
        elif config.source_type == DataSourceType.JDBC:
            return JDBCConnector(config)
        # Add more connector types as needed
        else:
            logger.warning(f"Unsupported source type: {config.source_type}")
            return None


# Global singleton instance
_manager = DataSourceManager()


def get_data_source_manager() -> DataSourceManager:
    """Get the global data source manager instance."""
    return _manager

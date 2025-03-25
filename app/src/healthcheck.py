from datetime import datetime
from typing import TypedDict

from cache import redis_client
from database import engine
from psycopg2.extensions import QueryCanceledError
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


class ComponentHealth(TypedDict):
    status: str
    message: str
    metrics: dict[str, str]


class ComponentChecks(TypedDict):
    database: ComponentHealth
    cache: ComponentHealth


class HealthCheck(BaseModel):
    status: str
    timestamp: str
    checks: ComponentChecks


def check_database() -> ComponentHealth:
    """Check database connectivity and write operations"""
    try:
        with engine.connect() as connection:
            # Test 1: Basic connectivity
            connection.execute(text("SELECT 1"))

            # Test 2: Check write operation with temporary table
            connection.execute(
                text("""
                CREATE TEMPORARY TABLE healthcheck_test (
                    id serial PRIMARY KEY,
                    test_col VARCHAR(50)
                )
            """)
            )

            # Test 3: Test write operation
            connection.execute(text("INSERT INTO healthcheck_test (test_col) VALUES ('test_value')"))

            # Get basic metrics
            metrics = {}

            # Get database size
            db_size = connection.execute(
                text("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            ).scalar()
            metrics["database_size"] = db_size

            # Get active write transactions
            active_writes = connection.execute(
                text("""
                SELECT count(*)
                FROM pg_stat_activity
                WHERE state = 'active'
                AND query ~* '^(insert|update|delete)'
            """)
            ).scalar()
            metrics["active_write_transactions"] = str(active_writes)

            # Check if there are too many active write transactions
            if active_writes > 50:  # Adjust this threshold based on your needs
                return ComponentHealth(
                    status="unhealthy",
                    message=f"High number of active write transactions: {active_writes}",
                    metrics=metrics,
                )

            return ComponentHealth(
                status="healthy",
                message="Database write operations successfully checked",
                metrics=metrics,
            )

    except QueryCanceledError:
        return ComponentHealth(
            status="unhealthy",
            message="Database query timeout",
            metrics={},
        )
    except SQLAlchemyError as e:
        return ComponentHealth(
            status="unhealthy",
            message=f"Database error: {str(e)}",
            metrics={},
        )


def check_redis() -> ComponentHealth:
    """Check Redis cache connectivity and operations"""
    try:
        # Check basic connectivity
        if not redis_client.ping():
            return ComponentHealth(
                status="unhealthy",
                message="Redis ping failed",
                metrics={},
            )

        # Test write operation
        test_key = "healthcheck:test"
        test_value = "test_value"
        if not redis_client.set(test_key, test_value, ex=10):  # Expire in 10 seconds
            return ComponentHealth(
                status="unhealthy",
                message="Redis write operation failed",
                metrics={},
            )

        # Test read operation
        read_value = redis_client.get(test_key)
        if not read_value or read_value.decode("utf-8") != test_value:
            return ComponentHealth(
                status="unhealthy",
                message="Redis read operation failed",
                metrics={},
            )

        # Test delete operation
        if not redis_client.delete(test_key):
            return ComponentHealth(
                status="unhealthy",
                message="Redis delete operation failed",
                metrics={},
            )

        # Check memory usage
        info = redis_client.info(section="memory")
        used_memory_percent = (
            int(info["used_memory"]) / int(info["maxmemory"]) * 100
            if "maxmemory" in info and int(info["maxmemory"]) > 0
            else 0
        )

        if used_memory_percent > 90:  # Warning if memory usage is above 90%
            return ComponentHealth(
                status="unhealthy",
                message=f"Redis memory usage critical: {used_memory_percent:.1f}%",
                metrics={},
            )

        metrics = {
            "memory_usage_percent": f"{used_memory_percent:.1f}%",
            "used_memory": f"{int(info['used_memory']) / 1024 / 1024:.1f}MB",
        }

        return ComponentHealth(
            status="healthy",
            message="Redis connection and operations successfully checked",
            metrics=metrics,
        )

    except RedisError as e:
        return ComponentHealth(
            status="unhealthy",
            message=f"Redis error: {str(e)}",
            metrics={},
        )


def get_health() -> HealthCheck:
    """Perform deep health checks and return overall system status"""
    db_status = check_database()
    cache_status = check_redis()

    # Determine overall status
    all_healthy = all(check["status"] == "healthy" for check in [db_status, cache_status])

    checks = ComponentChecks(database=db_status, cache=cache_status)

    return HealthCheck(
        status="healthy" if all_healthy else "unhealthy",
        timestamp=datetime.utcnow().isoformat(),
        checks=checks,
    )

import logging
import os
from enum import Enum

import models
import uvicorn
from cache import is_rate_limited
from characters import main
from database import engine, get_db
from exceptions import (
    RateLimitException,
    ServiceUnavailableException,
    rate_limit_exception_handler,
    service_unavailable_exception_handler,
)
from fastapi import Depends, FastAPI, Query, status
from fastapi.responses import JSONResponse
from fastapi_pagination import Page, add_pagination, paginate
from fastapi_pagination.utils import disable_installed_extensions_check
from healthcheck import HealthCheck, get_health
from sqlalchemy.orm import Session
from utils import PrometheusMiddleware, metrics, setting_otlp

OTLP_GRPC_ENDPOINT = os.environ.get("OTLP_GRPC_ENDPOINT", "http://tempo:4317")


# Configure logging
class EndpointFilter(logging.Filter):
    # Uvicorn endpoint access log filter
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /metrics") == -1


# Filter out /endpoint
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(openapi_prefix=os.getenv("ROOT_PATH", ""))
add_pagination(app)
disable_installed_extensions_check()
# Register exception handler
app.add_exception_handler(RateLimitException, rate_limit_exception_handler)
app.add_exception_handler(ServiceUnavailableException, service_unavailable_exception_handler)
# Configure Prometheus middleware
app.add_middleware(PrometheusMiddleware, "app")
app.add_route("/metrics", metrics)
# Setting OpenTelemetry exporter
setting_otlp(app, "fastapi-app", OTLP_GRPC_ENDPOINT)


class SortField(str, Enum):
    NAME = "name"
    ID = "id"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@app.get("/characters")
async def get_characters(
    order_by: SortField = Query(default=SortField.ID, description="Field to sort by"),
    order: SortOrder = Query(default=SortOrder.ASC, description="Sort order"),
    db: Session = Depends(get_db),
) -> Page[models.CharacterResponse]:
    if is_rate_limited():
        raise RateLimitException()

    # Get characters (either from cache or by fetching)
    characters = main(db)

    # Sort the characters based on the parameters
    sorted_characters = sorted(
        characters,
        key=lambda x: x[order_by.value],
        reverse=(order == SortOrder.DESC),
    )

    return paginate(sorted_characters)


@app.get(
    "/healthcheck",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK) if healthy, 503 if unhealthy",
    response_model=HealthCheck,
)
async def healthcheck():
    health_result = get_health()
    status_code = status.HTTP_200_OK if health_result.status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=health_result.__dict__)


if __name__ == "__main__":
    # update uvicorn access logger format
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = (
        "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s"
    )
    uvicorn.run(app, host="0.0.0.0", port="8000", log_config=log_config)

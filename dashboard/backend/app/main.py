import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db_pool, close_db_pool
from app.core.exceptions import CampusOpsException
from app.workers.outbox_worker import run_outbox_loop
from app.modules.auth.routes import router as auth_router
from app.modules.work_orders.routes import router as work_orders_router
from app.modules.inventory.routes import router as inventory_router
from app.modules.staffing.routes import router as staffing_router
from app.modules.intake.routes import router as intake_router
from app.modules.analytics.routes import router as analytics_router
from app.modules.scheduling.routes import router as scheduling_router
from app.modules.simulation.routes import router as simulation_router
from app.modules.approvals.routes import router as approvals_router
from app.modules.campus.routes import router as campus_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("campusops")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing CampusOps database pool...")
    await init_db_pool()

    logger.info("Starting background outbox worker...")
    stop_event = asyncio.Event()
    outbox_task = asyncio.create_task(
        run_outbox_loop(poll_interval=settings.OUTBOX_WORKER_POLL_INTERVAL, stop_event=stop_event)
    )

    yield

    logger.info("Stopping background outbox worker...")
    stop_event.set()
    outbox_task.cancel()
    try:
        await outbox_task
    except asyncio.CancelledError:
        pass

    logger.info("Closing database pool...")
    await close_db_pool()


app = FastAPI(
    title="CampusOps API: SRM Easwari Engineering College",
    description="Intelligent Campus Operations & Consequence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Structured Error Handlers
@app.exception_handler(CampusOpsException)
async def campusops_exception_handler(request: Request, exc: CampusOpsException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected server error occurred.",
            "path": request.url.path,
        },
    )


# Mount Sub-routers
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth_router)
api_v1.include_router(work_orders_router)
api_v1.include_router(inventory_router)
api_v1.include_router(staffing_router)
api_v1.include_router(intake_router)
api_v1.include_router(analytics_router)
api_v1.include_router(scheduling_router)
api_v1.include_router(simulation_router)
api_v1.include_router(approvals_router)
api_v1.include_router(campus_router)

app.include_router(api_v1)


@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "campus": settings.CAMPUS_NAME,
        "campus_code": settings.CAMPUS_CODE,
        "coordinates": {"lat": settings.CAMPUS_LAT, "lon": settings.CAMPUS_LON},
    }


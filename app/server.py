import asyncio
from contextlib import asynccontextmanager

import uvicorn
from config import GetEOLConfig, GetFeaturesConfig
from fastapi import FastAPI
from jobs.get_eol_fn import CiscoEOLJob
from jobs.get_features import GetFeaturesJob
from routers.features_router import features_router
from routers.product_alerts import product_alerts_router
from starlette.responses import RedirectResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI to handle background jobs.

    This lifespan function ensures that background tasks (such as data scraping jobs)
    run concurrently with the FastAPI application. The tasks are initiated before the
    app starts serving requests, allowing the app to serve API endpoints while
    the background tasks are processing data.

    Background jobs are created and managed asynchronously using asyncio, and the
    tasks continue to run while the API is live. When the API shuts down, the function
    ensures that all background tasks are properly awaited and completed before full shutdown.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: Allows the FastAPI app to serve requests while tasks run in the background.
    """
    # Create the jobs, add new as needed
    jobs = [
        CiscoEOLJob() if GetEOLConfig.ACTIVE else None,
        GetFeaturesJob() if GetFeaturesConfig.ACTIVE else None,
    ]

    # Filter out None values from jobs
    active_jobs = [job for job in jobs if job is not None]

    # Schedule the tasks to run concurrently within the current loop / no raw threading
    tasks = [asyncio.create_task(job.fetch_data()) for job in active_jobs]
    yield

    await asyncio.gather(*tasks)


app = FastAPI(
    lifespan=lifespan,
    description="""
    This API provides easy access to Cisco device insights, such as:

    - End-of-Life (EOL) dates
    - Common Vulnerabilities and Exposures (CVEs)
    - Features and best practices

    The API automates the data collection from Cisco's publicly available site, helping users manage 
    Cisco devices without the need for formal onboarding or contracts.
    """,
    title="Cisco Device Insights API",
)


@app.get("/", include_in_schema=False)
def read_root():
    return RedirectResponse(url="/docs")


# Include the features router in the main app
app.include_router(features_router)
app.include_router(product_alerts_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

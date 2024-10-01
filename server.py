import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.responses import RedirectResponse

from jobs.get_eol_fn import CiscoEOLJob
from jobs.get_features import GetFeaturesJob
from routers.features import features_router


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
    jobs = [CiscoEOLJob(), GetFeaturesJob()]

    # Schedule the tasks to run concurrently within the current loop / no raw threading
    tasks = [asyncio.create_task(job.fetch_data()) for job in jobs]
    yield

    await asyncio.gather(*tasks)


app = FastAPI(
    lifespan=lifespan,
    description="""
    Cisco Services APIs allow partners and customers to programmatically access and consume Cisco data in a simple, secure, and scalable manner. 
        
    Cisco Services APIs remove barriers to enterprise automation, increase productivity, help shorten sales cycles, and reduce operating expenses.""",
    title="Cisco Business Critical Services",
)


@app.get("/", include_in_schema=False)
def read_root():
    return RedirectResponse(url="/docs")


# Include the features router in the main app
app.include_router(features_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

import asyncio
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.responses import RedirectResponse

from jobs.get_features import GetFeaturesJob
from routers.features import features_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    fetcher = GetFeaturesJob()
    thread = threading.Thread(target=asyncio.run, args=(fetcher.fetch_data(),))
    # thread.start()
    yield
    # thread.join()


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

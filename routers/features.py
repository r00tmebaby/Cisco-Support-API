import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from models import Platform
from utils import PaginationParams, extract_feature, paginate

features_router = APIRouter(prefix="/feature", tags=["Features"])


@features_router.get(
    "/platforms",
    summary="Get platforms",
    description="Retrieve a list of platforms",
)
@paginate
def features_platforms(
    platform: Platform = Depends(), pagination: PaginationParams = Depends()
):
    with open("data/product_features/platforms.json") as f:
        results = json.loads(f.read())

    if platform.by_name:
        search_results = [
            platform_data
            for platform_data in results[platform.platform_choice]
            if platform.by_name.lower()
            in platform_data.get("platform_name", "").lower()
        ]
        return search_results

    return results[platform.platform_choice]


@features_router.get(
    "/releases",
    summary="Get releases",
    description="Retrieve a list of releases",
)
@paginate
def get_releases(
    platform_id: Optional[int] = Query(None, description="ID of the platform"),
    pagination: PaginationParams = Depends(),
):
    with open("data/product_features/releases.json") as f:
        releases = json.loads(f.read())

    filtered_releases = []

    for release_list in releases.values():
        for release in release_list:
            if platform_id is None or release["platform_id"] == platform_id:
                filtered_releases.append(release)

    return filtered_releases


@features_router.get(
    "/features",
    summary="Get features",
    description="Retrieve features for a specific platform and release",
)
@paginate
def get_features(
    platform_id: int = Path(..., description="ID of the platform"),
    release_id: int = Path(..., description="ID of the release"),
    pagination: PaginationParams = Depends(),
):
    tar_path = "data/product_features/features.tar.gz"
    file_name = f"{platform_id}_{release_id}.json"

    if not os.path.exists(tar_path):
        raise HTTPException(status_code=404, detail="Feature archive not found.")

    features = extract_feature(tar_path, file_name)
    return features

import asyncio
import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Union

import aiofiles
import httpx

from config import GetFeaturesConfig, logging
from models import FeaturesRequestModel


class GetFeaturesJob:
    """
    The GetFeaturesJob class is responsible for retrieving and storing Cisco product data including platforms, releases,
    and features. This data is fetched from various Cisco APIs and saved locally as JSON files. The class also supports
    reading the data from local files if online fetching is disabled.

    The following data is fetched:
    - Platforms: Different types of Cisco hardware platforms.
    - Releases: Software releases available for the platforms.
    - Features: Features supported by each release for the platforms.

    The URLs used for fetching data are:
        - Platforms: https://cfnngws.cisco.com/api/v1/platform
        - Releases: https://cfnngws.cisco.com/api/v1/release
        - Features: https://cfnngws.cisco.com/api/v1/by_product_result
    """

    config = GetFeaturesConfig()

    def __init__(self):
        self.config = GetFeaturesConfig()
        self.logger = logging.getLogger("GetFeaturesJob")
        self.unique_features = {}

    async def _fetch_platforms(
        self, client: httpx.AsyncClient, each_type: str
    ) -> Dict[str, Any]:
        """
        Fetch platforms for the given type.
        :param client: The HTTP client to use for the request.
        :param each_type: The type of platform to fetch.
        :return: A dictionary of platform data.
        """
        self.logger.info(f"Fetching platforms for {each_type}")
        request = FeaturesRequestModel(mdf_product_type=each_type)
        response = await client.post(
            self.config.REQUEST_1,
            headers=self.config.HEADERS,
            json=request.model_dump(),
            timeout=None,
        )
        await asyncio.sleep(1)
        if response.status_code == 200:
            json_response = response.json()
            await self._save_to_file(
                json_response, self.config.PROJECT_DATA_DIR / "platforms.json", 4
            )
            return response.json()
        return {}

    @classmethod
    def generate_feature_hash(cls, feature: Dict[str, Any]) -> str:
        """
        Generate a unique hash for each feature based on feature_name, feature_desc, and feature_set_desc.
        :param feature: The feature object.
        :return: The hash string (4-byte hash for space efficiency).
        """
        feature_str = f"{feature['feature_name']}_{feature['feature_desc']}_{feature['feature_set_desc']}"
        return hashlib.blake2b(
            feature_str.encode(), digest_size=cls.config.HASHING_DIGEST
        ).hexdigest()

    async def _fetch_releases(
        self,
        client: httpx.AsyncClient,
        each_platform: Dict[str, Any],
        each_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch releases for the given platform.
        :param client: The HTTP client to use for the request.
        :param each_platform: The platform data to fetch releases for.
        :param each_type: The type of platform.
        :return: A list of release data.
        """
        platform_id = each_platform.get("platform_id")
        self.logger.info(f"Fetching releases for platform {platform_id}")
        request = FeaturesRequestModel(
            platform_id=platform_id, mdf_product_type=each_type
        )
        response = await client.post(
            self.config.REQUEST_2,
            headers=self.config.HEADERS,
            json=request.model_dump(),
            timeout=None,
        )
        await asyncio.sleep(10)
        if response.status_code == 200:
            releases = response.json()
            for release in releases:
                release["platform_id"] = platform_id
            return releases
        self.logger.error(
            f"Failed to fetch releases for platform {platform_id}, status code: {response.status_code}"
        )
        return []

    async def _fetch_features(
        self,
        client: httpx.AsyncClient,
        each_release: Dict[str, Any],
        mdf_product_type: str,
    ) -> None:
        """
        Fetch features for the given release.
        :param client: The HTTP client to use for the request.
        :param each_release: The release data to fetch features for.
        :param mdf_product_type: The type of product.
        """
        self.logger.info(
            f"Fetching features for platform {each_release['platform_id']} and release {each_release['release_id']}"
        )
        request = FeaturesRequestModel(
            platform_id=each_release["platform_id"],
            mdf_product_type=mdf_product_type,
            release_id=each_release["release_id"],
        )
        response = await client.post(
            self.config.REQUEST_3,
            headers=self.config.HEADERS,
            json=request.model_dump(),
            timeout=None,
        )
        await asyncio.sleep(self.config.REQUEST_DELAY)
        platform_features = []
        if response.status_code == 200:
            response_text = await response.aread()
            features_data = json.loads(response_text)
            for feature in features_data:
                make_uuid = self.generate_feature_hash(feature)
                if make_uuid not in self.unique_features.keys():
                    self.unique_features[make_uuid] = feature
                platform_features.append(make_uuid)
            file_name = (
                f"{each_release['platform_id']}_{each_release['release_id']}.json"
            )
            file_path = self.config.FEATURES_DIR / file_name
            await self._save_to_file(platform_features, file_path)

        else:
            self.logger.error(
                f"Failed to fetch features for platform "
                f"{each_release['platform_id']} and release "
                f"{each_release['release_id']}, status code: "
                f"{response.status_code}"
            )

    async def _read_file(self, filename: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Read data from a local JSON file.
        :param filename: The name of the file to read.
        :return: A dictionary of data read from the file.
        """
        self.logger.info(f"Reading {filename} from local JSON file")
        async with aiofiles.open(
            os.path.join(self.config.FEATURES_DIR, f"{filename}.json"), "r"
        ) as infile:
            contents = await infile.read()
            return json.loads(contents)

    async def _fetch_all_features(self, releases: Dict[str, List[Dict[str, Any]]]):
        """
        Fetch all features for the given releases and save them to disk.
        :param releases: The release data to fetch features for.
        """
        async with httpx.AsyncClient(timeout=None) as client:
            semaphore = asyncio.Semaphore(self.config.CONCURRENT_REQUESTS_LIMIT)

            async def fetch_features_with_semaphore(
                release: Dict[str, Any], product_type: str
            ):
                async with semaphore:
                    await self._fetch_features(client, release, product_type)

            feature_tasks = []
            for mdf_product_type, releases_list in releases.items():
                for each_release in releases_list:
                    feature_tasks.append(
                        fetch_features_with_semaphore(each_release, mdf_product_type)
                    )
            await asyncio.gather(*feature_tasks)
            self.logger.info("Fetched all features data")

    async def fetch_data(self):
        """
        Fetch platforms, releases, and features data.
        """
        try:
            platforms = await self._fetch_platforms_data()
            releases = await self._fetch_releases_data(platforms)
            if self.config.FETCH_FEATURES_ONLINE:
                await self._fetch_and_archive_features(releases)
                self.logger.info("Job completed successfully")
        except Exception as e:
            self.logger.error(
                "Job failed to fetch platforms, releases, and features. Error: %s", e
            )

    async def _fetch_platforms_data(self) -> Dict[str, Any]:
        """
        Fetch or read platforms data.
        :return: A dictionary containing platforms data.
        """
        if self.config.FETCH_PLATFORMS_ONLINE:
            return await self._fetch_online_platforms()
        return await self._read_file("platforms")

    async def _fetch_releases_data(self, platforms: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch or read releases data.
        :param platforms: A dictionary containing platforms data.
        :return: A dictionary containing releases data.
        """
        if self.config.FETCH_RELEASES_ONLINE:
            return await self._fetch_online_releases(platforms)
        return await self._read_file("releases")

    async def _fetch_and_archive_features(self, releases: Dict[str, Any]):
        """
        Fetch all features, save them to disk, and then archive them into a tar.gz file.
        :param releases: A dictionary containing releases data.
        """
        try:
            archive_path = self.config.PROJECT_DATA_DIR / "features_data.tar.gz"
            unique_features_file = self.config.FEATURES_DIR / "unique_features.json"

            # Save all feature data to disk first
            await self._fetch_all_features(releases)

            # Save the unique features to disk
            await self._save_to_file(self.unique_features, unique_features_file, 4)

            # Create the tar.gz file and add all JSON files from the directory
            with tarfile.open(archive_path, "w:gz") as tar:
                for file_path in self.config.FEATURES_DIR.glob("*.json"):
                    tar.add(file_path, arcname=file_path.name)
            shutil.rmtree(self.config.FEATURES_DIR)

            self.logger.info(
                "Successfully archived all features and unique_features.json to features.tar.gz"
            )
        except Exception as e:
            self.logger.error(f"Failed to archive {e}")

    async def _fetch_online_platforms(self) -> Dict[str, Any]:
        """
        Fetch platforms data from the online API.
        :return: A dictionary containing platforms data.
        """
        async with httpx.AsyncClient(timeout=None) as client:
            platform_tasks = [
                self._fetch_platforms(client, each_type)
                for each_type in self.config.TYPES
            ]
            platforms_results = await asyncio.gather(*platform_tasks)
            platforms = {
                each_type: data
                for each_type, data in zip(self.config.TYPES, platforms_results)
            }
        return platforms

    async def _fetch_online_releases(self, platforms: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch releases data from the online API for the given platforms.
        :param platforms: A dictionary containing platforms data.
        :return: A dictionary containing releases data.
        """
        releases = {}
        async with httpx.AsyncClient(timeout=None) as client:
            for each_type in self.config.TYPES:
                platform_data = platforms.get(each_type, [])
                release_tasks = [
                    self._fetch_releases(client, each_platform, each_type)
                    for each_platform in platform_data
                ]
                releases_results = await asyncio.gather(*release_tasks)
                releases[each_type] = [
                    release for sublist in releases_results for release in sublist
                ]
                self.logger.info(
                    f"Retrieved {len(releases[each_type])} releases for {each_type}"
                )
        await self._save_to_file(
            releases, self.config.PROJECT_DATA_DIR / "releases.json", 4
        )
        return releases

    async def _save_to_file(
        self, data: Union[List[str], Dict[str, Any]], filename: Path, indent: int = 0
    ):
        """
        Save the given data to a JSON file.
        :param data: The data to save.
        :param filename: The name of the file to save the data in.
        """
        indent = indent if indent else None

        async with aiofiles.open(filename, "w") as outfile:
            await outfile.write(json.dumps(data, indent=indent))
        self.logger.info(
            f"Saved data to {os.path.join(self.config.FEATURES_DIR, filename)}"
        )

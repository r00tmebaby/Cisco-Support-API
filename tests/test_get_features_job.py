import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jobs.get_features import GetFeaturesJob, RequestModel


@pytest.mark.asyncio
async def test_fetch_platforms_failure():
    job = GetFeaturesJob()
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_client.post.return_value = mock_response

    result = await job._fetch_platforms(mock_client, "Switches")

    assert result == {}
    mock_client.post.assert_called_once_with(
        job.config.REQUEST_1,
        headers=job.config.HEADERS,
        json=RequestModel(mdf_product_type="Switches").model_dump(),
        timeout=900,
    )


@pytest.mark.asyncio
async def test_fetch_releases_failure():
    job = GetFeaturesJob()
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_client.post.return_value = mock_response

    platform_data = {"platform_id": 1}
    result = await job._fetch_releases(mock_client, platform_data, "Switches")

    assert result == []
    mock_client.post.assert_called_once_with(
        job.config.REQUEST_2,
        headers=job.config.HEADERS,
        json=RequestModel(platform_id=1, mdf_product_type="Switches").model_dump(),
        timeout=900,
    )


@pytest.mark.asyncio
async def test_fetch_features_success():
    job = GetFeaturesJob()
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aread.return_value = json.dumps([]).encode()
    mock_client.post.return_value = mock_response
    mock_tar = MagicMock()

    release_data = {"platform_id": 1, "release_id": 1}
    await job._fetch_features(mock_client, release_data, "Switches", mock_tar)

    mock_tar.add.assert_called_once()
    mock_client.post.assert_called_once_with(
        job.config.REQUEST_3,
        headers=job.config.HEADERS,
        json=RequestModel(
            platform_id=1, mdf_product_type="Switches", release_id=1
        ).model_dump(),
        timeout=900,
    )


@pytest.mark.asyncio
async def test_fetch_features_failure():
    job = GetFeaturesJob()
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_client.post.return_value = mock_response
    mock_tar = MagicMock()

    release_data = {"platform_id": 1, "release_id": 1}
    await job._fetch_features(mock_client, release_data, "Switches", mock_tar)

    mock_tar.add.assert_not_called()
    mock_client.post.assert_called_once_with(
        job.config.REQUEST_3,
        headers=job.config.HEADERS,
        json=RequestModel(
            platform_id=1, mdf_product_type="Switches", release_id=1
        ).model_dump(),
        timeout=900,
    )


@pytest.mark.asyncio
async def test_fetch_all_features():
    job = GetFeaturesJob()
    mock_tar = MagicMock()
    releases = {"Switches": [{"platform_id": 1, "release_id": 1}]}

    with patch.object(job, "_fetch_features", new_callable=AsyncMock) as mock_fetch:
        await job._fetch_all_features(releases, mock_tar)

    assert mock_fetch.await_count == 1
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_data():
    job = GetFeaturesJob()

    with patch.object(
        job, "_fetch_platforms_data", new_callable=AsyncMock
    ) as mock_fetch_platforms, patch.object(
        job, "_fetch_releases_data", new_callable=AsyncMock
    ) as mock_fetch_releases, patch.object(
        job, "_fetch_and_archive_features", new_callable=AsyncMock
    ) as mock_fetch_features:
        platforms = {"Switches": []}
        releases = {"Switches": []}
        mock_fetch_platforms.return_value = platforms
        mock_fetch_releases.return_value = releases

        await job.fetch_data()

        mock_fetch_platforms.assert_awaited_once()
        mock_fetch_releases.assert_awaited_once_with(platforms)
        mock_fetch_features.assert_awaited_once_with(releases)


@pytest.mark.asyncio
async def test_fetch_online_platforms():
    job = GetFeaturesJob()

    with patch.object(job, "_fetch_platforms", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"platforms": []}

        result = await job._fetch_online_platforms()

    assert "Switches" in result
    mock_fetch.assert_awaited()


@pytest.mark.asyncio
async def test_fetch_online_releases():
    job = GetFeaturesJob()
    platforms = {"Switches": [{"platform_id": 1}]}

    with patch.object(job, "_fetch_releases", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [{"release_id": 1}]

        result = await job._fetch_online_releases(platforms)

    assert "Switches" in result
    mock_fetch.assert_awaited()


@pytest.mark.asyncio
async def test_fetch_and_archive_features():
    job = GetFeaturesJob()
    releases = {"Switches": [{"platform_id": 1, "release_id": 1}]}

    with patch("tarfile.open", new_callable=MagicMock) as mock_tarfile, patch.object(
        job, "_fetch_all_features", new_callable=AsyncMock
    ) as mock_fetch:
        mock_tar = mock_tarfile.return_value.__enter__.return_value

        await job._fetch_and_archive_features(releases)

        mock_fetch.assert_awaited_once_with(releases, mock_tar)


@pytest.mark.asyncio
async def test_fetch_platforms_data_online():
    job = GetFeaturesJob()
    job.config.FETCH_PLATFORMS_ONLINE = True

    with patch.object(
        job, "_fetch_online_platforms", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = {"platforms": []}

        result = await job._fetch_platforms_data()

    assert result == {"platforms": []}
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_releases_data_online():
    job = GetFeaturesJob()
    job.config.FETCH_RELEASES_ONLINE = True
    platforms = {"platforms": []}

    with patch.object(
        job, "_fetch_online_releases", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = {"releases": []}

        result = await job._fetch_releases_data(platforms)

    assert result == {"releases": []}
    mock_fetch.assert_awaited_once_with(platforms)

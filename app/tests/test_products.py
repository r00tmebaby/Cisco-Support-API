import os
import sys
from unittest.mock import AsyncMock, mock_open, patch

import pytest
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.jobs.get_cisco_products import (
    BASE_URL,
    extract_product_links,
    extract_supported_products,
    get_page_soup,
    scrape_cisco_products,
)

BASE_HTML = """
<div data-config-metrics-title="Products by Category">
    <a href="/product1.html">Product 1</a>
    <a href="/product2.html">Product 2</a>
</div>
"""

SUPPORTED_PRODUCTS_HTML = """
<div id="allSupportedProducts">
    <a href="/supported1.html">Supported Product 1</a>
    <a href="/supported2.html">Supported Product 2</a>
</div>
"""


@pytest.mark.asyncio
async def test_get_page_soup_success():
    # Mock the client and response
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = BASE_HTML.encode()
    mock_client.get.return_value = mock_response

    # Call the function
    soup = await get_page_soup(mock_client, "https://example.com")

    # Assertions
    assert isinstance(soup, BeautifulSoup)
    assert "Products by Category" in str(soup)
    mock_client.get.assert_awaited_once_with("https://example.com")


@pytest.mark.asyncio
async def test_get_page_soup_failure():
    # Mock the client and response
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response

    # Call the function
    soup = await get_page_soup(mock_client, "https://example.com")

    # Assertions
    assert soup is None
    mock_client.get.assert_awaited_once_with("https://example.com")


@pytest.mark.asyncio
async def test_extract_product_links():
    # Create a BeautifulSoup object from the base HTML
    soup = BeautifulSoup(BASE_HTML, "html.parser")

    # Call the function
    product_links = await extract_product_links(soup)

    # Assertions
    assert len(product_links) == 2
    assert product_links[0] == {
        "product": "Product 1",
        "url": "https://www.cisco.com/product1.html",
    }
    assert product_links[1] == {
        "product": "Product 2",
        "url": "https://www.cisco.com/product2.html",
    }


@pytest.mark.asyncio
async def test_extract_supported_products():
    # Mock the client and response
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = SUPPORTED_PRODUCTS_HTML.encode()
    mock_client.get.return_value = mock_response

    # Call the function
    supported_products = await extract_supported_products(
        mock_client, "https://example.com/product1.html"
    )

    # Assertions
    assert len(supported_products) == 2
    assert supported_products[0] == {
        "name": "Supported Product 1",
        "url": "https://www.cisco.com/supported1.html",
    }
    assert supported_products[1] == {
        "name": "Supported Product 2",
        "url": "https://www.cisco.com/supported2.html",
    }
    mock_client.get.assert_awaited_once_with("https://example.com/product1.html")


@pytest.mark.asyncio
async def test_scrape_cisco_products():
    # Mock the client, response, and open function
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = BASE_HTML.encode()
    mock_client.get.return_value = mock_response

    # Mock extract_supported_products to return sample data
    mock_extract_supported_products = AsyncMock()
    mock_extract_supported_products.return_value = [
        {"name": "Supported Product 1", "url": "https://www.cisco.com/supported1.html"}
    ]

    with patch(
        "app.jobs.get_cisco_products.get_page_soup",
        return_value=BeautifulSoup(BASE_HTML, "html.parser"),
    ), patch(
        "app.jobs.get_cisco_products.extract_supported_products",
        new=mock_extract_supported_products,
    ), patch(
        "httpx.AsyncClient", return_value=mock_client
    ), patch(
        "builtins.open", mock_open()
    ):

        # Run the scraping function
        await scrape_cisco_products("output.json")

    # Assertions
    mock_extract_supported_products.assert_called()
    mock_extract_supported_products.assert_awaited()

import json
import logging
import traceback
from typing import Any, Dict, Optional

import httpx
from httpx import ConnectError, HTTPStatusError, ReadTimeout

logger = logging.getLogger("mealie-mcp")


class MealieApiError(Exception):
    """Custom exception for Mealie API errors with status code and response details."""

    def __init__(self, status_code: int, message: str, response_text: str = None):
        self.status_code = status_code
        self.message = message
        self.response_text = response_text
        super().__init__(f"{message} (Status Code: {status_code})")


class MealieClient:

    def __init__(self, base_url: str, api_key: str):
        if not base_url:
            raise ValueError("Base URL cannot be empty")
        if not api_key:
            raise ValueError("API key cannot be empty")

        logger.debug({"message": "Initializing MealieClient", "base_url": base_url})
        self.base_url = base_url
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            # Test connection
            logger.debug({"message": "Testing connection to Mealie API"})
            try:
                await self._client.get("/api/app/about")
                logger.info({"message": "Successfully connected to Mealie API"})
            except ConnectError as e:
                error_msg = f"Failed to connect to Mealie API at {self.base_url}: {str(e)}"
                logger.error({"message": error_msg})
                logger.debug(
                    {"message": "Error traceback", "traceback": traceback.format_exc()}
                )
                raise ConnectionError(error_msg) from e
            except Exception as e:
                error_msg = f"Error connecting to Mealie API: {str(e)}"
                logger.error({"message": error_msg})
                logger.debug(
                    {"message": "Error traceback", "traceback": traceback.format_exc()}
                )
                raise
        return self._client

    async def close(self):
        """Close the async HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.close()

    async def _handle_request(self, method: str, url: str, **kwargs) -> Dict[str, Any] | str:
        """Common request handler with error handling for all API calls."""
        try:
            logger.debug(
                {
                    "message": "Making API request",
                    "method": method,
                    "url": url,
                    "body": kwargs.get("json"),
                }
            )

            if "params" in kwargs:
                logger.debug(
                    {"message": "Request parameters", "params": kwargs["params"]}
                )
            if "json" in kwargs:
                logger.debug({"message": "Request payload", "payload": kwargs["json"]})

            client = await self._get_client()
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()  # Raise an exception for 4XX/5XX responses

            logger.debug(
                {"message": "Request successful", "status_code": response.status_code}
            )
            # Log the response content at debug level
            try:
                response_data = response.json()
                logger.debug({"message": "Response content", "data": response_data})
                return response_data
            except json.JSONDecodeError:
                logger.debug(
                    {"message": "Response content (non-JSON)", "content": response.text}
                )
                return response.text

        except HTTPStatusError as e:
            status_code = e.response.status_code
            error_detail = f"HTTP Error {status_code}"

            # Try to parse error details from response
            try:
                error_detail = e.response.json()
            except Exception:
                error_detail = e.response.text

            error_msg = f"API error for {method} {url}: {error_detail}"
            logger.error(
                {
                    "message": "API request failed",
                    "method": method,
                    "url": url,
                    "status_code": status_code,
                    "error_detail": error_detail,
                }
            )
            logger.debug(
                {"message": "Failed Request body", "content": e.request.content}
            )
            raise MealieApiError(status_code, error_msg, e.response.text) from e

        except ReadTimeout:
            error_msg = f"Request timeout for {method} {url}"
            logger.error({"message": error_msg, "method": method, "url": url})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise TimeoutError(error_msg)

        except ConnectError as e:
            error_msg = f"Connection error for {method} {url}: {str(e)}"
            logger.error(
                {"message": error_msg, "method": method, "url": url, "error": str(e)}
            )
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ConnectionError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error for {method} {url}: {str(e)}"
            logger.error(
                {"message": error_msg, "method": method, "url": url, "error": str(e)}
            )
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise

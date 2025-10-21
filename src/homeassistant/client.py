import logging
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class HomeAssistantError(Exception):
    """Base exception for Home Assistant API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class HomeAssistantClient:
    """Base client for Home Assistant API interactions."""

    def __init__(self, base_url: str, token: str):
        """
        Initialize the Home Assistant client.

        Args:
            base_url: The base URL of the Home Assistant instance
            token: Long-lived access token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.token}"}
            )
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _handle_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle HTTP requests to Home Assistant API.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Relative URL path
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response JSON data

        Raises:
            HomeAssistantError: If the request fails
        """
        full_url = f"{self.base_url}{url}"
        session = await self._get_session()

        logger.debug(
            {
                "event": "ha_api_request",
                "method": method,
                "url": full_url,
                "params": params,
            }
        )

        try:
            async with session.request(
                method, full_url, params=params, json=json_data
            ) as response:
                response_data = await response.json()

                if response.status >= 400:
                    logger.error(
                        {
                            "event": "ha_api_error",
                            "status": response.status,
                            "url": full_url,
                            "response": response_data,
                        }
                    )
                    raise HomeAssistantError(
                        f"Home Assistant API error: {response_data}",
                        status_code=response.status,
                    )

                logger.debug(
                    {
                        "event": "ha_api_response",
                        "status": response.status,
                        "url": full_url,
                    }
                )

                return response_data

        except aiohttp.ClientError as e:
            logger.error(
                {
                    "event": "ha_api_connection_error",
                    "url": full_url,
                    "error": str(e),
                }
            )
            raise HomeAssistantError(f"Connection error: {str(e)}")
        except Exception as e:
            logger.error(
                {
                    "event": "ha_api_unexpected_error",
                    "url": full_url,
                    "error": str(e),
                }
            )
            raise HomeAssistantError(f"Unexpected error: {str(e)}")

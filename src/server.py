import logging
import os
import traceback
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

from mealie import MealieFetcher
from homeassistant import HomeAssistantFetcher
from prompts import register_prompts
from tools import register_all_tools

# Load environment variables first
load_dotenv()

# Get log level from environment variable with INFO as default
log_level_name = os.getenv("LOG_LEVEL", "INFO")
log_level = getattr(logging, log_level_name.upper(), logging.INFO)

# Configure logging handlers based on environment
# In containerized environments, only log to stdout/stderr for container-native logging
handlers = [logging.StreamHandler()]
if not os.getenv("CONTAINER"):
    # Add file handler only in non-container environments
    handlers.append(logging.FileHandler("mealie_mcp_server.log"))

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)
logger = logging.getLogger("mealie-mcp")

mcp = FastMCP("mealie")

# Mealie configuration (required)
MEALIE_BASE_URL = os.getenv("MEALIE_BASE_URL")
MEALIE_API_KEY = os.getenv("MEALIE_API_KEY")
if not MEALIE_BASE_URL or not MEALIE_API_KEY:
    raise ValueError(
        "MEALIE_BASE_URL and MEALIE_API_KEY must be set in environment variables."
    )

# Home Assistant configuration (optional)
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
ha_enabled = bool(HA_URL and HA_TOKEN)

try:
    mealie = MealieFetcher(
        base_url=MEALIE_BASE_URL,
        api_key=MEALIE_API_KEY,
    )
    logger.info({"message": "Mealie client initialized successfully"})
except Exception as e:
    logger.error({"message": "Failed to initialize Mealie client", "error": str(e)})
    logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
    raise

# Initialize Home Assistant client if credentials provided
ha_fetcher: Optional[HomeAssistantFetcher] = None
if ha_enabled:
    try:
        ha_fetcher = HomeAssistantFetcher(
            base_url=HA_URL,
            token=HA_TOKEN,
        )
        logger.info({"message": "Home Assistant integration enabled"})
    except Exception as e:
        logger.error({"message": "Failed to initialize Home Assistant client", "error": str(e)})
        logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
        # Don't fail startup if HA is optional
        logger.warning({"message": "Continuing without Home Assistant integration"})
        ha_fetcher = None
else:
    logger.info({"message": "Home Assistant integration disabled (credentials not provided)"})

register_prompts(mcp)
register_all_tools(mcp, mealie, ha_fetcher)

if __name__ == "__main__":
    try:
        # Support both stdio (local) and sse (kubernetes) transports
        transport = os.getenv("MCP_TRANSPORT", "stdio")
        port = int(os.getenv("MCP_PORT", "8000"))
        
        logger.info({
            "message": "Starting Mealie MCP Server",
            "transport": transport,
            "port": port if transport == "sse" else "N/A"
        })
        
        if transport == "sse":
            mcp.run(transport="streamable-http", port=port)
        else:
            mcp.run(transport="stdio")
    except Exception as e:
        logger.critical(
            {"message": "Fatal error in Mealie MCP Server", "error": str(e)}
        )
        logger.debug(
            {"message": "Error traceback", "traceback": traceback.format_exc()}
        )
        raise

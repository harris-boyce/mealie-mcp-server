# Extending the Mealie MCP Server

Complete implementation guide for adding Home Assistant calendar integration to the Mealie MCP server.

## Architecture Overview

The extended Mealie MCP server provides a unified interface for:
- **Mealie API**: Recipe management, meal planning, shopping lists, inventory
- **Home Assistant API**: Calendar queries, todo list management, datetime

Both APIs are accessed through a single MCP server endpoint with HTTPS transport, making it compatible with Claude mobile.

## Implementation

### 1. Add Dependencies

Update `pyproject.toml`:

```toml
dependencies = [
    "fastmcp",
    "aiohttp",  # For async HTTP requests to HA
    "python-dateutil"  # For date handling
]
```

### 2. Environment Configuration

```python
# server.py
import os
from datetime import datetime, timedelta
import aiohttp

# Mealie configuration (existing)
MEALIE_URL = os.getenv("MEALIE_URL")
MEALIE_TOKEN = os.getenv("MEALIE_TOKEN")

# Home Assistant configuration (new)
HA_URL = os.getenv("HA_URL")  
HA_TOKEN = os.getenv("HA_TOKEN")

# Validate configuration on startup
if not all([MEALIE_URL, MEALIE_TOKEN, HA_URL, HA_TOKEN]):
    raise ValueError("Missing required environment variables")
```

### 3. Home Assistant Calendar Tools

```python
@mcp.tool()
async def get_custody_schedule(
    calendar: str,
    days_ahead: int = 7
) -> dict:
    """
    Get custody schedule events from Home Assistant calendar.
    
    Args:
        calendar: Calendar name without 'calendar.' prefix 
                 ("boys_custody_schedule" or "girls_custody_schedule")
        days_ahead: Number of days to look ahead (default 7)
    
    Returns:
        List of calendar events with start, end, summary
    """
    start = datetime.now().isoformat()
    end = (datetime.now() + timedelta(days=days_ahead)).isoformat()
    
    async with aiohttp.ClientSession() as session:
        url = f"{HA_URL}/api/calendars/calendar.{calendar}"
        params = {"start": start, "end": end}
        headers = {"Authorization": f"Bearer {HA_TOKEN}"}
        
        async with session.get(url, params=params, headers=headers) as resp:
            resp.raise_for_status()
            events = await resp.json()
            return {
                "calendar": calendar,
                "start": start,
                "end": end,
                "events": events
            }

@mcp.tool()
async def get_family_events(
    calendar: str,
    days_ahead: int = 7
) -> dict:
    """
    Get family activity events from Home Assistant calendar.
    
    Args:
        calendar: Calendar name without 'calendar.' prefix
                 ("benci_boys" or "boycivengas")
        days_ahead: Number of days to look ahead (default 7)
    
    Returns:
        List of calendar events with start, end, summary
    """
    start = datetime.now().isoformat()
    end = (datetime.now() + timedelta(days=days_ahead)).isoformat()
    
    async with aiohttp.ClientSession() as session:
        url = f"{HA_URL}/api/calendars/calendar.{calendar}"
        params = {"start": start, "end": end}
        headers = {"Authorization": f"Bearer {HA_TOKEN}"}
        
        async with session.get(url, params=params, headers=headers) as resp:
            resp.raise_for_status()
            events = await resp.json()
            return {
                "calendar": calendar,
                "start": start,
                "end": end,
                "events": events
            }

@mcp.tool()
async def get_all_calendars() -> dict:
    """
    List all available calendars in Home Assistant.
    
    Returns:
        List of calendar entities with names and entity_ids
    """
    async with aiohttp.ClientSession() as session:
        url = f"{HA_URL}/api/calendars"
        headers = {"Authorization": f"Bearer {HA_TOKEN}"}
        
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            calendars = await resp.json()
            return {"calendars": calendars}
```

### 4. Error Handling

```python
import logging

logger = logging.getLogger(__name__)

async def safe_ha_request(url: str, params: dict = None) -> dict:
    """Wrapper for HA API requests with error handling"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {HA_TOKEN}"}
            async with session.get(url, params=params, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()
    except aiohttp.ClientError as e:
        logger.error(f"HA API request failed: {e}")
        return {"error": str(e), "url": url}
    except Exception as e:
        logger.error(f"Unexpected error in HA request: {e}")
        return {"error": "Internal server error"}
```

### 5. Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mealie-mcp-server
spec:
  template:
    spec:
      containers:
      - name: mealie-mcp
        image: your-registry/mealie-mcp:latest
        env:
        - name: MEALIE_URL
          value: "https://mealie-mcp-server.taildda370.ts.net"
        - name: MEALIE_TOKEN
          valueFrom:
            secretKeyRef:
              name: mealie-mcp-secrets
              key: mealie-token
        - name: HA_URL
          value: "https://home-assistant.taildda370.ts.net"
        - name: HA_TOKEN
          valueFrom:
            secretKeyRef:
              name: mealie-mcp-secrets
              key: ha-token
        ports:
        - containerPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: mealie-mcp-service
spec:
  selector:
    app: mealie-mcp
  ports:
  - port: 443
    targetPort: 8000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mealie-mcp-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - mealie-mcp-server.taildda370.ts.net
    secretName: mealie-mcp-tls
  rules:
  - host: mealie-mcp-server.taildda370.ts.net
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mealie-mcp-service
            port:
              number: 443
```

### 6. Secrets Configuration

```bash
# Create Kubernetes secret with both tokens
kubectl create secret generic mealie-mcp-secrets \
  --from-literal=mealie-token='YOUR_MEALIE_API_TOKEN' \
  --from-literal=ha-token='YOUR_HA_LONG_LIVED_TOKEN'
```

## Testing

### Test Calendar Integration

```python
# test_ha_integration.py
import asyncio
from server import get_custody_schedule, get_family_events

async def test_calendars():
    # Test custody schedule
    boys = await get_custody_schedule("boys_custody_schedule", days_ahead=7)
    print(f"Boys schedule: {len(boys['events'])} events")
    
    girls = await get_custody_schedule("girls_custody_schedule", days_ahead=7)
    print(f"Girls schedule: {len(girls['events'])} events")
    
    # Test activity calendars
    benci = await get_family_events("benci_boys", days_ahead=7)
    print(f"Benci Boys: {len(benci['events'])} events")
    
    boyci = await get_family_events("boycivengas", days_ahead=7)
    print(f"Boycivengas: {len(boyci['events'])} events")

if __name__ == "__main__":
    asyncio.run(test_calendars())
```

### Test with MCP Inspector

```bash
# Run server locally
python server.py

# In another terminal, test with MCP inspector
npx @modelcontextprotocol/inspector python server.py
```

## Claude.ai Integration

1. Deploy extended server to Kubernetes with HTTPS
2. In Claude.ai: Settings → Integrations → Add MCP Server
3. Configure:
   - **URL**: `https://mealie-mcp-server.taildda370.ts.net/sse`
   - **Name**: `Mealie` (or custom name)
   - **Transport**: HTTP/SSE

4. Test from Claude mobile:
   ```
   "Claude, check my custody schedule for next week"
   ```

## Future Enhancements

### Inventory Management Tools

```python
@mcp.tool()
async def update_food_quantity(food_id: str, quantity: float, unit: str = None):
    """Update on-hand quantity for a food item"""
    # Implementation using Mealie API PATCH /api/households/foods/{food_id}
    pass

@mcp.tool()
async def add_food_to_inventory(name: str, quantity: float = 1.0, unit: str = None):
    """Add new food to inventory"""
    # Implementation using Mealie API POST /api/foods
    pass
```

### Todo List Integration

Home Assistant MCP server already provides:
- `Home Assistant:HassListAddItem` 
- `Home Assistant:todo_get_items`

These tools work alongside the extended Mealie MCP for complete shopping list management.

## Troubleshooting

**Calendar queries return empty:**
- Verify HA_TOKEN has calendar read permissions
- Check calendar entity_ids in Home Assistant (Developer Tools → States)
- Confirm date range includes events

**HTTPS connection fails on mobile:**
- Verify TLS certificate is valid (check cert-manager logs)
- Test HTTPS endpoint: `curl https://mealie-mcp-server.taildda370.ts.net/health`
- Check Tailscale DNS resolution

**Tools not appearing in Claude:**
- Restart Claude app after connecting MCP server
- Check MCP server logs for registration errors
- Verify SSE endpoint is accessible
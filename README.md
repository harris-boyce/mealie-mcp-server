[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/rldiao-mealie-mcp-server-badge.png)](https://mseep.ai/app/rldiao-mealie-mcp-server)

# Mealie MCP Server

This project enables AI assistants to interact with your [Mealie](https://github.com/mealie-recipes/mealie) recipe database through MCP client such as Claude Desktop.

## Prerequisites

- Python 3.12+
- Running Mealie instance with API key
- Package manager [uv](https://docs.astral.sh/uv/getting-started/installation/)
- (Optional) Home Assistant instance with long-lived access token for calendar integration

## Features

### Core Features (Mealie)
- **Recipe Management**: Search, retrieve, create, and update recipes
- **Meal Planning**: Create and manage meal plans with bulk operations
- **Food Inventory**: Track foods on-hand with quantity/price management
- **Shopping Lists**: Manage shopping lists (via Home Assistant integration)

### Extended Features (Home Assistant Integration - Optional)
- **Calendar Integration**: Query custody schedules and family activity calendars
- **Context-Aware Meal Planning**: Match meal complexity to schedule events
- **Voice-Driven Workflow**: Designed for conversational meal planning

See [meal-planning-skill/SKILL.md](meal-planning-skill/SKILL.md) for the complete voice-driven meal planning workflow.

## Usage with Claude Desktop

### Option 1: Using fastmcp (Recommended)

Install the server directly with the `fastmcp` command:

**Mealie Only:**
```bash
fastmcp install src/server.py \
  --env-var MEALIE_BASE_URL=https://your-mealie-instance.com \
  --env-var MEALIE_API_KEY=your-mealie-api-key
```

**With Home Assistant Integration:**
```bash
fastmcp install src/server.py \
  --env-var MEALIE_BASE_URL=https://your-mealie-instance.com \
  --env-var MEALIE_API_KEY=your-mealie-api-key \
  --env-var HA_URL=https://your-homeassistant.com \
  --env-var HA_TOKEN=your-ha-long-lived-token
```

### Option 2: Manual Configuration

Add the server to your `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mealie-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/repo/src",
        "run",
        "server.py"
      ],
      "env": {
        "MEALIE_BASE_URL": "https://your-mealie-instance.com",
        "MEALIE_API_KEY": "your-mealie-api-key"
      }
    }
  }
}
```

## Development

1. Clone the repository and navigate to the project directory

2. Install dependencies using uv:
```bash
uv sync
```

3. Copy the provided template file:
```bash
cp .env.template .env
```

4. Edit the `.env` file with your Mealie instance details:
```bash
# Mealie configuration (required)
MEALIE_BASE_URL=https://your-mealie-instance.com
MEALIE_API_KEY=your-mealie-api-key

# Home Assistant configuration (optional)
HA_URL=https://your-homeassistant.com
HA_TOKEN=your-ha-long-lived-token
```

5. Run MCP inspector
```bash
uv run mcp dev src/server.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

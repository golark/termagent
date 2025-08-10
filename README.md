# TermAgent

A LangGraph-based agent system with intelligent routing and MCP (Model Context Protocol) integration for handling git commands.

## Features

- 🤖 **LangGraph Agent System**: Built with LangGraph for robust agent orchestration
- 🔄 **Intelligent Routing**: Automatically detects and routes git commands to specialized agents
- 🌐 **MCP Integration**: Uses Model Context Protocol for agent communication
- 🎯 **Git Command Handling**: Specialized git agent for all git operations
- 💬 **Interactive Interface**: Command-line interface for easy interaction

## Architecture

```
TermAgent
├── Router Agent (Main)
│   ├── Detects git commands
│   └── Routes via MCP to Git Agent
└── Git Agent (Specialized)
    ├── Handles all git operations
    └── Returns results via MCP
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd termagent
   ```

2. **Initialize with uv**:
   ```bash
   uv init
   ```

3. **Install dependencies**:
   ```bash
   uv add langgraph langchain langchain-openai mcp
   ```

4. **Run the application**:
   ```bash
   uv run main.py
   ```

## Usage

### Interactive Mode

Start the application and enter commands interactively:

```bash
uv run main.py
```

Example session:
```
🤖 TermAgent - LangGraph Agent System
========================================
This agent can:
  • Detect and route git commands to a specialized git agent
  • Handle regular commands
  • Use MCP for agent communication

Enter commands (or 'quit' to exit):
------------------------------
termagent> git status
🔄 Processing: git status
🤖 Response: Git command executed via MCP: On branch main...
📍 Routed to: git_agent
------------------------------
```

### Supported Commands

#### Git Commands
- `git status` - Check repository status
- `git add .` - Add all files to staging
- `git commit -m "message"` - Commit changes
- `git push` - Push to remote repository
- `git pull` - Pull from remote repository
- `git log` - Show commit history
- `git branch` - List branches
- `git checkout <branch>` - Switch branches
- `git merge <branch>` - Merge branches
- `git diff` - Show differences

#### Regular Commands
- Any non-git command will be handled by the regular command handler

## Project Structure

```
termagent/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          # Base agent class
│   ├── router_agent.py        # Router agent for command detection
│   └── git_agent.py          # Git-specific agent
├── mcp_integration.py         # MCP communication layer
├── termagent_graph.py        # LangGraph workflow definition
├── main.py                   # Main application entry point
├── pyproject.toml           # Project configuration
└── README.md               # This file
```

## Development

### Adding New Agents

1. Create a new agent class extending `BaseAgent`:
   ```python
   from termagent.agents.base_agent import BaseAgent
   
   class MyAgent(BaseAgent):
       def __init__(self):
           super().__init__("my_agent")
       
       def process(self, state):
           # Implement your agent logic
           pass
   ```

2. Update the router agent to detect and route to your new agent.

3. Add the new agent to the graph in `termagent_graph.py`.

### MCP Integration

The system uses MCP for agent communication. The `mcp_integration.py` module provides:

- `GitMCPServer`: MCP server for git operations
- `MCPClient`: Client for connecting to git agents
- `GitMCPTool`: Tool definitions for git commands

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

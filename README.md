# TermAgent

A LangGraph-based agent system with intelligent routing, MCP (Model Context Protocol) integration, and voice command input using Vosk speech recognition.

## Features

- 🤖 **LangGraph Agent System**: Built with LangGraph for robust agent orchestration
- 🔄 **Intelligent Routing**: Automatically detects and routes git commands to specialized agents
- 🌐 **MCP Integration**: Uses Model Context Protocol for agent communication
- 🎯 **Git Command Handling**: Specialized git agent for all git operations
- 💬 **Interactive Interface**: Command-line interface for easy interaction
- 🎤 **Voice Input**: Accept voice commands using Vosk speech recognition
- 📚 **Command History**: Navigate and search through command history

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

### Voice Input Setup

TermAgent supports voice commands using Vosk speech recognition. To enable voice input:

1. **Install voice dependencies**:
   ```bash
   uv add vosk pyaudio numpy
   ```

2. **Download a Vosk model** (run from project root):
   ```bash
   python scripts/setup_voice.py
   ```
   
   This will download and configure a speech recognition model (~42 MB for small model).

3. **Alternative manual setup**:
   - Download a model from [Vosk Models](https://alphacephei.com/vosk/models)
   - Extract to `~/.termagent/models/`
   - Recommended: `vosk-model-small-en-us-0.15` for basic commands

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

### Voice Commands

TermAgent supports voice input for hands-free operation:

1. **Activate voice mode**: Press `v` during input
2. **Speak your command**: Clearly state what you want to do
3. **Deactivate voice mode**: Press `v` again

**Example voice commands**:
- "list files in current directory"
- "git status"
- "create a new folder called projects"
- "show me the current working directory"
- "install package with brew"
- "update packages with apt"
- "search for packages with pip"

**Voice input features**:
- Automatic command recognition and execution
- Command history integration
- Background listening with thread safety
- Support for natural language commands

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

#### Package Management Commands
TermAgent supports a wide range of package managers across different operating systems:

**macOS - Homebrew**:
- `brew install <package>` - Install packages
- `brew update` - Update Homebrew
- `brew upgrade` - Upgrade packages
- `brew list` - List installed packages
- `brew search <query>` - Search for packages

**Ubuntu/Debian - APT**:
- `apt install <package>` - Install packages
- `apt update` - Update package lists
- `apt upgrade` - Upgrade packages
- `apt search <query>` - Search for packages
- `apt list` - List packages

**Python - pip**:
- `pip install <package>` - Install Python packages
- `pip list` - List installed packages
- `pip search <query>` - Search for packages
- `pip freeze` - Show requirements format

**Node.js - npm/yarn**:
- `npm install <package>` - Install Node.js packages
- `npm list` - List installed packages
- `npm search <query>` - Search for packages
- `yarn add <package>` - Install with Yarn

**Other Package Managers**:
- `cargo install <package>` - Rust packages
- `go get <package>` - Go modules
- `gem install <package>` - Ruby gems
- `mvn install` - Maven packages
- `pacman -S <package>` - Arch Linux packages

**Get Help**:
- `help brew` - Homebrew help
- `help apt` - APT help
- `help pip` - pip help
- `help npm` - npm help

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
├── input_handler.py          # Input handling with voice support
├── main.py                   # Main application entry point
├── scripts/
│   └── setup_voice.py        # Voice model setup script
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

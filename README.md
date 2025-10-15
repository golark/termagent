# TermAgent

An AI-powered terminal assistant that seamlessly combines shell commands with AI capabilities.

## Features

- **AI Command Execution** - Natural language commands powered by Claude
- **Shell Integration** - Execute shell commands directly
- **Command History** - Navigate and search previous commands
- **Shell Aliases** - Automatic alias resolution from your shell
- **Permissions System** - Fine-grained control over file system access
- **Message Caching** - Replay previous AI interactions
- **Autonomy Levels** - Control when permission prompts appear

## Installation

```bash
git clone <repository-url>
cd termagent
uv sync
```

## Usage

Start the agent:

```bash
make run
```

Or with debug mode:

```bash
make debug
```

Check version:

```bash
termagent --version
```

### Commands

- Type shell commands directly: `ls -la`, `git status`, etc.
- Ask AI questions: "what files changed recently?"
- Type `config` to view current settings
- Type `exit`, `quit`, or `q` to exit

## Configuration

Configuration is stored in `~/.termagent/config.json`:

```json
{
  "autonomy_level": "manual",
  "debug_mode": false,
  "max_context_length": 200000,
  "model": "claude-3-5-sonnet-20241022"
}
```

### Autonomy Levels

- **manual** - Ask permission for all operations
- **semi** - Ask only for dangerous operations
- **full** - Never ask for permission

## Environment

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=your_key_here
```

## Development

Run tests:

```bash
make test
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.



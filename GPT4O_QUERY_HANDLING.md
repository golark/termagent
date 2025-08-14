# GPT-4o Query Handling in TermAgent

TermAgent now features enhanced query handling using GPT-4o for complex reasoning tasks and GPT-3.5-turbo for simple queries. This system automatically detects query complexity and provides step-by-step guidance to answer user queries effectively.

## 🧠 Key Features

### Automatic Complexity Detection
- **Query Analysis**: Automatically detects if user input is a question or informational query
- **Complexity Scoring**: Analyzes query complexity using multiple indicators
- **Model Selection**: Automatically chooses between GPT-4o and GPT-3.5-turbo based on complexity

### GPT-4o Integration
- **Complex Reasoning**: Uses GPT-4o for queries requiring advanced analysis
- **Step-by-Step Guidance**: Provides detailed, actionable steps to answer complex queries
- **Context Awareness**: Considers current workspace structure and files for better analysis

### Smart Routing
- **Query Classification**: Routes queries to appropriate handlers (shell, general, etc.)
- **Shell Query Enhancement**: Enhanced handling for file, Docker, and system-related queries
- **Fallback Support**: Graceful fallback when LLM services are unavailable

## 🔍 Query Types Supported

### Simple Queries (GPT-3.5-turbo)
- Basic file operations: "what files are in this directory?"
- Simple counts: "how many python files are here?"
- Status checks: "show git status"

### Complex Queries (GPT-4o)
- **Analysis Requests**: "analyze the current git workflow and suggest improvements"
- **Comparison Queries**: "compare Docker vs virtual environments for this project"
- **Recommendation Requests**: "how would you recommend organizing this project structure?"
- **Hypothetical Scenarios**: "what would happen if we refactor the agent system?"
- **Best Practices**: "what are the pros and cons of different approaches?"

## 🚀 How It Works

### 1. Query Detection
```python
# The system automatically detects queries using:
- Question words (what, how, why, when, where, which, who)
- Question patterns (ends with ?, starts with question words)
- Complex query indicators (how to, what is the best way, compare, analyze)
- Length and complexity analysis
```

### 2. Complexity Analysis
```python
# Multiple factors determine complexity:
- Keyword analysis (complex vs simple keywords)
- Pattern matching (complex reasoning patterns)
- Word count and structure
- Reasoning requirements
```

### 3. Model Selection
```python
# Automatic model selection:
- GPT-4o: For complex reasoning, analysis, comparisons, recommendations
- GPT-3.5-turbo: For simple queries, basic operations, status checks
```

### 4. Query Processing
```python
# Different processing paths:
- Shell Queries: Enhanced with GPT-4o analysis when complex
- General Queries: Full GPT-4o analysis with step-by-step guidance
- Task Breakdown: LLM-powered task decomposition for complex operations
```

## 📋 Usage Examples

### Simple Query (GPT-3.5-turbo)
```
User: "what files are in this directory?"
System: Routes to shell handler, executes `ls -la`, provides formatted output
```

### Complex Query (GPT-4o)
```
User: "how would you recommend organizing this project structure for better maintainability?"
System: 
1. Detects as complex query
2. Uses GPT-4o for analysis
3. Analyzes current workspace structure
4. Provides step-by-step recommendations
5. Suggests specific commands and approaches
```

### Shell Query with GPT-4o Enhancement
```
User: "analyze the current git workflow and suggest improvements for team collaboration"
System:
1. Detects as complex shell query
2. Uses GPT-4o for comprehensive analysis
3. Examines git status, branches, remotes
4. Provides detailed workflow analysis
5. Suggests specific git commands and practices
```

## 🛠️ Configuration

### Environment Variables
```bash
# Required for GPT-4o functionality
export OPENAI_API_KEY="your-openai-api-key"
```

### Debug Mode
```bash
# Enable debug mode to see model selection and processing details
python -m termagent.main --debug
```

### No-Confirm Mode
```bash
# Skip confirmation prompts for automated testing
python -m termagent.main --no-confirm
```

## 🔧 Testing

### Run the Test Script
```bash
# Test GPT-4o query handling with various query types
python test_gpt4o_queries.py
```

### Interactive Testing
```bash
# Start interactive mode and test queries
python -m termagent.main --debug
```

## 📊 Performance Considerations

### GPT-4o Usage
- **When to Use**: Complex reasoning, analysis, recommendations, comparisons
- **Benefits**: Better understanding, more detailed guidance, comprehensive analysis
- **Cost**: Higher API cost, slightly slower response time

### GPT-3.5-turbo Usage
- **When to Use**: Simple queries, basic operations, status checks
- **Benefits**: Faster response, lower cost, efficient for simple tasks
- **Limitations**: Less detailed analysis, simpler reasoning

## 🔮 Future Enhancements

### Planned Features
- **Query History**: Track and learn from user query patterns
- **Custom Prompts**: Allow users to customize analysis approaches
- **Multi-Modal Support**: Handle queries with file content analysis
- **Performance Optimization**: Cache common query patterns and responses

### Integration Opportunities
- **MCP Integration**: Enhanced query handling through Model Context Protocol
- **Plugin System**: Extensible query handlers for specific domains
- **Learning System**: Improve complexity detection based on user feedback

## 🐛 Troubleshooting

### Common Issues
1. **GPT-4o Not Available**: Check OPENAI_API_KEY and API quota
2. **Slow Responses**: Complex queries with GPT-4o take longer
3. **Fallback Behavior**: System gracefully falls back to simpler approaches

### Debug Information
```bash
# Enable debug mode to see detailed processing information
python -m termagent.main --debug

# Look for these debug messages:
# query_detector | Detected complex query indicator: how to
# complexity_analyzer | Task complexity analysis: 15 score, 4 reasoning
# query_analyzer | 🧠 Using GPT-4o for query analysis
```

## 📚 API Reference

### Key Functions
- `QueryDetector.is_complex_query()`: Detect complex queries
- `TaskComplexityAnalyzer.analyze_complexity()`: Analyze task complexity
- `handle_query()`: Process general queries with GPT-4o
- `_handle_shell_query()`: Process shell queries with GPT-4o enhancement

### State Fields
- `is_query`: Boolean indicating if input is a query
- `query_type`: Type of query (shell_query, general_query)
- `should_use_gpt4o`: Boolean indicating GPT-4o usage
- `query_complexity`: Detailed complexity analysis results

## 🤝 Contributing

### Adding New Query Types
1. Extend `QueryDetector` with new patterns
2. Add complexity indicators to `TaskComplexityAnalyzer`
3. Update routing logic in `RouterAgent`
4. Add test cases to `test_gpt4o_queries.py`

### Improving Complexity Detection
1. Analyze user query patterns
2. Add new complexity indicators
3. Refine scoring algorithms
4. Test with various query types

---

For more information, see the main [README.md](README.md) and the [TermAgent documentation](docs/).

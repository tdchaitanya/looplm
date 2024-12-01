# Chat Mode Usage

Chat mode in LoopLM enables interactive, persistent conversations with language models. This guide covers how to effectively use chat mode for your development workflow.

## Starting a Chat Session

### Basic Start

```bash
# Start with default provider
looplm chat

# Use specific provider
looplm chat --provider anthropic

# Use specific model
looplm chat --provider openai --model gpt-4o-mini
```

## Core Features

### Session Management

```bash
# Save current session
/save
Enter session name: project-planning

# List available sessions
/list

# Load a previous session
/load

# Start a new session
/new

# Rename current session
/rename

# Delete a session
/delete
```

### Environment Control

```bash
# Clear chat history
/clear

# Change model
/model

# View token usage
/usage

# Exit chat mode
/quit
```

### System Prompt Management

System prompts allow you to give a role to the langiage model, for more details see [here](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts)
```bash
# View/modify system prompt
/system

# Available options:
1. Use saved prompt
2. Create new prompt
3. Save current prompt
4. Delete saved prompt
```

## Common Use Cases

### Interactive Development

```
> Help me design a Python class for handling HTTP requests

> Can you add error handling to that class?

> Now let's write unit tests for it
```

### Code Review Sessions

```
> I want to review this code:
[paste code]

> What potential issues do you see?

> How can we improve the error handling?
```

### Learning Sessions

```
> Explain how Python's async/await works

> Can you give me an example?

> What are some common pitfalls to avoid?
```

### Project Planning

```
> Let's design a system architecture for a web app

> What database would you recommend for this use case?

> Can you help me break this down into smaller tasks?
```

## Workflow Examples

### Development Session

```bash
# Start a development session
looplm chat --provider anthropic
> I need to build a REST API with FastAPI

# Save the session
/save
Enter session name: fastapi-development

# Later, resume the session
looplm chat
/load
Select session: fastapi-development
```

### Code Review Workflow

```bash
# Start a code review session
looplm chat --provider openai --model gpt-4
> I'm going to share some code for review

# After discussion
/save
Enter session name: code-review-sprint-1

# Share findings with team
/usage  # Check token usage for reporting
```

### Learning Session

```bash
# Start a learning session
looplm chat
> I want to learn about design patterns

# Save progress
/save
Enter session name: design-patterns-study

# Change model for deeper insights
/model
Select: anthropic/claude-3-opus

# Continue learning
> Can you explain the Factory pattern?
```

## Best Practices

### Session Organization

1. **Use Descriptive Names**
   ```
   project-backend-design
   api-security-review
   python-concurrency-learning
   ```

2. **Regular Saving**
    - Save after significant insights
    - Save before changing topics
    - Save before testing different approaches

3. **Clean Session Management**
   ```
   /list  # Review available sessions
   /delete  # Remove obsolete sessions
   /new  # Start fresh for new topics
   ```
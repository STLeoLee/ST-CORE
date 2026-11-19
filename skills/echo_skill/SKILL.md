---
name: echo
description: Echo back the user's input with optional formatting options
---

# Echo Skill

A simple skill that echoes back the user's input with various formatting options.

## Description

The Echo Skill is a utility skill that returns the user's input with optional transformations. This skill is useful for testing, demonstrations, and as a template for creating new skills.

## When to Use This Skill

Use this skill when the user asks you to:
- Echo or repeat something back to them
- Test if the system is working
- Demonstrate skill functionality
- Format text with specific options (uppercase, prefix, repeat)

**Trigger phrases**: "echo", "repeat", "say", "copy", "duplicate"

### How to Execute This Skill

When the user's request matches the above conditions, call this skill using the following parameters:

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_text` | string | ✅ Yes | - | The text to echo back (this is the user's message) |
| `uppercase` | boolean | ❌ No | `false` | Convert text to UPPERCASE |
| `prefix` | string | ❌ No | `"Echo"` | Custom prefix before the echoed text |
| `repeat_count` | integer | ❌ No | `1` | Number of times to repeat (max 10) |

### Execution Examples

**Example 1: Basic echo**
```python
skill.execute(input_text="Hello World")
# Returns: "[Test Success] Echo: Hello World"
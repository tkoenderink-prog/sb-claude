#!/usr/bin/env python3
"""Test script for tool registry."""

from core.tools import ToolRegistry, register_all_tools

print("Testing tool registry...")

# Get registry instance
registry = ToolRegistry.get_instance()

# Register all tools
register_all_tools()

# Print summary
tools = registry.get_all_tools()
print(f"\nRegistered {len(tools)} tools:")

for tool in tools:
    print(f"\n  {tool.name}")
    print(f"    Description: {tool.description[:80]}...")
    print(f"    Parameters: {len(tool.parameters.get('properties', {}))} params")

# Test provider formatting
print("\n\nAnthopic format (first tool):")
print(tools[0].to_anthropic_format())

print("\n\nOpenAI format (first tool):")
print(tools[0].to_openai_format())

print("\n\nAll tests passed!")

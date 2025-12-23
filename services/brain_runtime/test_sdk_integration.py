#!/usr/bin/env python
"""Test script for SDK integration."""

import asyncio
import logging
import os
from core.agent.sdk_runtime import SDKAgentRuntime
from core.tools import register_all_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_sdk_runtime():
    """Test the SDK agent runtime."""
    # Register tools first
    tool_count = register_all_tools()
    logger.info(f"Registered {tool_count} tools")

    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return

    # Create runtime
    runtime = SDKAgentRuntime(api_key=api_key)
    logger.info("Created SDK runtime")

    # Test with a simple task
    task = "List what tools you have available and describe what you can help me with."
    run_id = "test-001"

    logger.info(f"Starting test run: {task}")

    # Execute and collect events
    events = []
    async for event in runtime.execute(
        run_id=run_id,
        task=task,
        context=None,
        tools=None,  # All tools
        max_turns=5,
        attached_skills=[],
    ):
        event_type = event.get("type")
        logger.info(f"Event: {event_type}")

        if event_type == "text":
            print(event.get("data", ""), end="", flush=True)
        elif event_type == "tool_call":
            tool_data = event.get("data", {})
            print(f"\n[Tool: {tool_data.get('tool')}]", flush=True)
        elif event_type == "usage":
            usage = event.get("data", {})
            print(f"\n\nUsage: {usage}", flush=True)

        events.append(event)

    print("\n\nTest completed!")
    logger.info(f"Received {len(events)} events")


if __name__ == "__main__":
    asyncio.run(test_sdk_runtime())

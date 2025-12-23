"""Example usage of LLM providers with real configuration.

This script demonstrates how to use the provider system with API keys
from the application configuration.

Run with real API calls:
    uv run python example_provider_usage.py

Note: Requires valid ANTHROPIC_API_KEY and/or OPENAI_API_KEY in .env file.
"""

import asyncio
import logging

from core.config import get_settings
from core.providers import (
    get_provider,
    list_providers,
    get_provider_models,
    ProviderType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def example_basic_chat():
    """Example: Basic chat without tools."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set, skipping example")
        return

    print("\n=== Example 1: Basic Chat (No Tools) ===\n")

    # Initialize provider
    provider = get_provider(ProviderType.ANTHROPIC, api_key=settings.anthropic_api_key)

    # Send message
    messages = [
        {
            "role": "user",
            "content": "What is the capital of France? Answer in one sentence.",
        }
    ]

    print("User: What is the capital of France?\n")
    print("Assistant: ", end="", flush=True)

    async for event in provider.chat(messages=messages, stream=True, max_tokens=100):
        if event["type"] == "content":
            print(event["data"]["text"], end="", flush=True)
        elif event["type"] == "done":
            print("\n\n[Complete]")
        elif event["type"] == "error":
            logger.error(f"Error: {event['data']['error']}")


async def example_tool_calling():
    """Example: Chat with tool calling."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set, skipping example")
        return

    print("\n=== Example 2: Chat with Tools ===\n")

    # Initialize provider
    provider = get_provider(ProviderType.ANTHROPIC, api_key=settings.anthropic_api_key)

    # Define mock tools
    tools = [
        {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature units",
                    },
                },
                "required": ["location"],
            },
        }
    ]

    # Send message
    messages = [{"role": "user", "content": "What's the weather in Paris?"}]

    print("User: What's the weather in Paris?\n")

    tool_calls = []
    assistant_text = ""

    async for event in provider.chat(
        messages=messages, tools=tools, stream=True, max_tokens=500
    ):
        if event["type"] == "content":
            text = event["data"]["text"]
            assistant_text += text
            print(text, end="", flush=True)

        elif event["type"] == "tool_call_start":
            print(f"\n\n[Tool Call Started: {event['data']['name']}]")

        elif event["type"] == "tool_call":
            tool_call = event["data"]
            tool_calls.append(tool_call)
            print(f"\nCalling {tool_call['name']} with input:")
            print(f"  {tool_call['input']}")

        elif event["type"] == "stop":
            print(f"\n\n[Stop Reason: {event['data']['stop_reason']}]")

        elif event["type"] == "usage":
            print(
                f"[Tokens: {event['data']['input_tokens']} in, {event['data']['output_tokens']} out]"
            )

        elif event["type"] == "error":
            logger.error(f"Error: {event['data']['error']}")

    print("\n[Complete]")


async def example_multi_provider():
    """Example: Compare responses from different providers."""
    settings = get_settings()

    print("\n=== Example 3: Multi-Provider Comparison ===\n")

    question = "Explain quantum computing in one sentence."
    messages = [{"role": "user", "content": question}]

    print(f"Question: {question}\n")

    # Try Anthropic
    if settings.anthropic_api_key:
        print("--- Claude Sonnet 4 ---")
        provider = get_provider(
            ProviderType.ANTHROPIC, api_key=settings.anthropic_api_key
        )

        response = ""
        async for event in provider.chat(
            messages=messages, stream=True, max_tokens=100
        ):
            if event["type"] == "content":
                response += event["data"]["text"]

        print(response)
        print()

    # Try OpenAI
    if settings.openai_api_key:
        print("--- GPT-4o ---")
        provider = get_provider(ProviderType.OPENAI, api_key=settings.openai_api_key)

        response = ""
        async for event in provider.chat(
            messages=messages, stream=True, max_tokens=100
        ):
            if event["type"] == "content":
                response += event["data"]["text"]

        print(response)
        print()

    print("[Complete]")


async def example_list_capabilities():
    """Example: List all providers and their models."""
    print("\n=== Example 4: Provider Capabilities ===\n")

    providers = list_providers()
    print(f"Available providers: {len(providers)}\n")

    for provider_info in providers:
        provider_type = provider_info["type"]
        print(f"--- {provider_info['name']} ---")

        models = get_provider_models(provider_type)
        for model in models:
            print(f"  {model['name']}")
            print(f"    ID: {model['id']}")
            print(f"    Context: {model['context_window']:,} tokens")
            print(f"    Max Output: {model['max_output']:,} tokens")
            print(f"    Capabilities: {', '.join(model['capabilities'])}")
            print()


async def main():
    """Run all examples."""
    settings = get_settings()

    # Check for API keys
    has_anthropic = bool(settings.anthropic_api_key)
    has_openai = bool(settings.openai_api_key)

    if not has_anthropic and not has_openai:
        print("\n" + "=" * 70)
        print("ERROR: No API keys configured")
        print("=" * 70)
        print("\nPlease set at least one API key in your .env file:")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        print("  OPENAI_API_KEY=sk-proj-...")
        print("\nYou can still see provider metadata with Example 4.")
        print("=" * 70 + "\n")

    try:
        # Example 4 works without API keys
        await example_list_capabilities()

        # Examples 1-3 require API keys
        if has_anthropic:
            await example_basic_chat()
            await example_tool_calling()

        if has_anthropic or has_openai:
            await example_multi_provider()

    except KeyboardInterrupt:
        print("\n\n[Interrupted by user]")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

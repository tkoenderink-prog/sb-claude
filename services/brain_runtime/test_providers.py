"""Quick test script to verify provider imports and basic functionality."""

import asyncio
from core.providers import (
    get_provider,
    list_providers,
    get_provider_models,
    ProviderType,
)


async def test_providers():
    """Test provider initialization and metadata."""

    print("\n=== Testing Provider System ===\n")

    # Test 1: List providers
    print("1. Listing available providers:")
    providers = list_providers()
    for provider in providers:
        print(f"   - {provider['name']} ({provider['type']})")

    # Test 2: Get models for each provider
    print("\n2. Available models:")
    for provider_type in [ProviderType.ANTHROPIC, ProviderType.OPENAI]:
        print(f"\n   {provider_type.value.upper()}:")
        models = get_provider_models(provider_type)
        for model in models:
            caps = ", ".join(model["capabilities"])
            print(f"   - {model['name']} ({model['id']})")
            print(
                f"     Context: {model['context_window']:,} | Max Output: {model['max_output']:,}"
            )
            print(f"     Capabilities: {caps}")

    # Test 3: Initialize providers (without making API calls)
    print("\n3. Initializing providers:")

    # Use dummy API keys for import test
    try:
        anthropic_provider = get_provider(
            ProviderType.ANTHROPIC, api_key="test-key-123"
        )
        print(f"   - Anthropic provider initialized: {anthropic_provider.name}")
        print(f"     Supports tools: {anthropic_provider.supports_tools()}")
        print(f"     Default model: {anthropic_provider.get_default_model()}")
    except Exception as e:
        print(f"   - Anthropic provider error: {e}")

    try:
        openai_provider = get_provider(ProviderType.OPENAI, api_key="test-key-456")
        print(f"   - OpenAI provider initialized: {openai_provider.name}")
        print(f"     Supports tools: {openai_provider.supports_tools()}")
        print(f"     Default model: {openai_provider.get_default_model()}")
    except Exception as e:
        print(f"   - OpenAI provider error: {e}")

    # Test 4: Tool formatting
    print("\n4. Testing tool formatting:")
    test_tools = [
        {
            "name": "get_calendar_events",
            "description": "Get calendar events for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        }
    ]

    print(
        f"   - Anthropic format: {anthropic_provider.format_tools(test_tools)[0]['name']}"
    )
    print(f"   - OpenAI format: {openai_provider.format_tools(test_tools)[0]['type']}")

    print("\n=== Provider System Tests Complete ===\n")


if __name__ == "__main__":
    asyncio.run(test_providers())

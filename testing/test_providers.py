"""
Test all LLM providers to ensure they work correctly.

Usage:
    python test_providers.py
    python test_providers.py --provider gemini
    python test_providers.py --stream
"""
import asyncio
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.gemini_provider import GeminiProvider


async def test_provider(provider_name: str, streaming: bool = False):
    """Test a specific provider"""
    
    print(f"\n{'='*60}")
    print(f"Testing {provider_name.upper()}")
    print(f"Mode: {'Streaming' if streaming else 'Non-streaming'}")
    print(f"{'='*60}\n")
    
    # Create provider
    if provider_name == "openai":
        provider = OpenAIProvider()
        model = "gpt-3.5-turbo"
    elif provider_name == "anthropic":
        provider = AnthropicProvider()
        model = "claude-3-haiku-20240307"
    elif provider_name == "gemini":
        provider = GeminiProvider()
        model = "gemini-2.5-flash"
        # If provider auto-detected a model, show it
        try:
            auto = getattr(provider, 'auto_model_actual', None)
            if auto:
                print(f"Detected Gemini model for this key: {auto}")
        except Exception:
            pass
    else:
        print(f"❌ Unknown provider: {provider_name}")
        return False
    
    prompt = "Say 'Hello! I am working correctly.' in exactly those words."
    
    try:
        if streaming:
            print("🔄 Streaming response:")
            print("-" * 40)
            chunks = []
            async for chunk in provider.stream_generate(prompt, model=model, max_tokens=50):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            
            full_response = "".join(chunks)
            print("\n" + "-" * 40)
            print(f"✅ Received {len(chunks)} chunks")
            print(f"✅ Total length: {len(full_response)} characters")
            
        else:
            print("📥 Generating full response...")
            result = await provider.generate(prompt, model=model, max_tokens=50)
            
            print("-" * 40)
            print(f"Response: {result['content']}")
            print("-" * 40)
            print(f"✅ Model: {result['model']}")
            print(f"✅ Prompt tokens: {result['prompt_tokens']}")
            print(f"✅ Completion tokens: {result['completion_tokens']}")
            print(f"✅ Total tokens: {result['total_tokens']}")
            
            # Test cost estimation
            cost = provider.estimate_cost(
                result['prompt_tokens'],
                result['completion_tokens'],
                model
            )
            print(f"✅ Estimated cost: ${cost:.6f}")
        
        print(f"\n✅ {provider_name.upper()} test PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ {provider_name.upper()} test FAILED")
        print(f"Error: {str(e)}\n")
        return False


async def test_all_providers(streaming: bool = False):
    """Test all available providers"""
    
    providers = ["gemini", "openai", "anthropic"]
    results = {}
    
    print("\n" + "="*60)
    print("Testing All LLM Providers")
    print("="*60)
    
    for provider_name in providers:
        results[provider_name] = await test_provider(provider_name, streaming)
        await asyncio.sleep(2)  # Rate limiting buffer
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for provider_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{provider_name.upper():12} {status}")
    
    print("\n")
    
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    if passed_count == total_count:
        print(f"🎉 All {total_count} providers working!")
    else:
        print(f"⚠️ {passed_count}/{total_count} providers working")
        print("\nFailed providers may need:")
        print("  - API key in .env file")
        print("  - pip install <package>")
        print("  - Valid API credits")


async def check_api_keys():
    """Check which API keys are configured"""
    import os
    
    print("\n" + "="*60)
    print("API Key Configuration Check")
    print("="*60 + "\n")
    
    keys = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    }
    
    for key_name, key_value in keys.items():
        if key_value:
            # Show first/last 4 chars
            masked = f"{key_value[:8]}...{key_value[-4:]}" if len(key_value) > 12 else "****"
            print(f"✅ {key_name:20} configured ({masked})")
        else:
            print(f"❌ {key_name:20} NOT FOUND")
    
    print()


def main():
    parser = argparse.ArgumentParser(description="Test LLM providers")
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai", "anthropic", "all"],
        default="all",
        help="Which provider to test"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Test streaming mode"
    )
    parser.add_argument(
        "--check-keys",
        action="store_true",
        help="Only check API key configuration"
    )
    
    args = parser.parse_args()
    
    if args.check_keys:
        asyncio.run(check_api_keys())
        return
    
    if args.provider == "all":
        asyncio.run(test_all_providers(streaming=args.stream))
    else:
        asyncio.run(test_provider(args.provider, streaming=args.stream))


if __name__ == "__main__":
    main()

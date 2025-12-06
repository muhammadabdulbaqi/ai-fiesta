"""
Quick test to verify Gemini models work
Run this to see which models are actually available
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("❌ Please install: pip install google-generativeai")
    exit(1)

async def test_gemini_models():
    """Test which Gemini models actually work"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env")
        return
    
    genai.configure(api_key=api_key)
    
    # Models to test (from most likely to work, to least likely)
    models_to_test = [
        "gemini-1.5-flash",      # Most likely to work
        "gemini-1.5-pro",        # Should work
        "gemini-pro",            # Older, stable
        "gemini-1.5-flash-8b",   # Newer, efficient
        "gemini-2.0-flash-exp",  # Experimental (might not be available)
    ]
    
    print("Testing Gemini models...\n")
    print("=" * 60)
    
    working_models = []
    failed_models = []
    
    for model_name in models_to_test:
        print(f"\n Testing: {model_name}")
        print("-" * 60)
        
        try:
            model = genai.GenerativeModel(model_name)
            
            # Test non-streaming first
            print("   [1/2] Testing non-streaming generation...")
            response = await model.generate_content_async(
                "Say 'I work!' and nothing else.",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=50,
                    temperature=0.1
                )
            )
            
            result_text = response.text if hasattr(response, 'text') else "No text"
            print(f"   ✅ Non-streaming works: {result_text[:50]}")
            
            # Test streaming
            print("   [2/2] Testing streaming generation...")
            chunks = []
            stream = await model.generate_content_async(
                "Count to 3 slowly: 1",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=20,
                    temperature=0.1
                ),
                stream=True
            )
            
            async for chunk in stream:
                if hasattr(chunk, 'text'):
                    chunks.append(chunk.text)
            
            print(f"   ✅ Streaming works: Received {len(chunks)} chunks")
            print(f"   ✅ {model_name} - WORKING!")
            working_models.append(model_name)
            
        except Exception as e:
            error_str = str(e)
            print(f"   ❌ FAILED: {error_str[:100]}")
            failed_models.append((model_name, error_str))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if working_models:
        print(f"\n✅ WORKING MODELS ({len(working_models)}):")
        for model in working_models:
            print(f"   - {model}")
        print(f"\n👉 USE THIS IN YOUR CODE:")
        print(f'   model = "{working_models[0]}"  # Recommended')
    else:
        print("\n❌ NO WORKING MODELS FOUND")
    
    if failed_models:
        print(f"\n❌ FAILED MODELS ({len(failed_models)}):")
        for model, error in failed_models:
            print(f"   - {model}")
            if "404" in error:
                print(f"     → Not available in your region/tier")
            elif "permission" in error.lower():
                print(f"     → API key lacks permissions")
    
    print("\n" + "=" * 60)
    
    # List all available models from API
    print("\nFetching available models from Gemini API...")
    try:
        available_models = genai.list_models()
        print("\nAll available models:")
        for model in available_models:
            if "generateContent" in model.supported_generation_methods:
                print(f"   ✅ {model.name}")
    except Exception as e:
        print(f"   ❌ Could not list models: {e}")
    
    print("\n")

if __name__ == "__main__":
    asyncio.run(test_gemini_models())
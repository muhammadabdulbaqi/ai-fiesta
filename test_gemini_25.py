"""
Test Gemini 2.5 models with correct model names
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

import google.generativeai as genai

async def test_gemini_25():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found")
        return
    
    genai.configure(api_key=api_key)
    
    # Test with actual model path (what the API expects)
    models_to_test = [
        ("gemini-2.5-flash", "models/gemini-2.5-flash"),
        ("gemini-2.5-pro", "models/gemini-2.5-pro"),
    ]
    
    print("Testing Gemini 2.5 models...\n")
    
    for friendly_name, actual_path in models_to_test:
        print(f"Testing: {friendly_name} (using {actual_path})")
        print("-" * 60)
        
        try:
            # Use the actual model path with "models/" prefix
            model = genai.GenerativeModel(actual_path)
            
            # Test non-streaming
            print("  [1/2] Non-streaming test...")
            response = await model.generate_content_async(
                "Say 'Hello from Gemini 2.5!' and nothing else.",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=50,
                    temperature=0.1
                )
            )
            print(f"  ✅ Response: {response.text}")
            
            # Test streaming
            print("  [2/2] Streaming test...")
            chunks = []
            stream = await model.generate_content_async(
                "Count: 1, 2, 3",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=20,
                    temperature=0.1
                ),
                stream=True
            )
            
            async for chunk in stream:
                if hasattr(chunk, 'text'):
                    chunks.append(chunk.text)
                    print(f"  📦 Chunk: {chunk.text}")
            
            print(f"  ✅ Total chunks: {len(chunks)}")
            print(f"  ✅ {friendly_name} WORKS!\n")
            
        except Exception as e:
            error = str(e)
            print(f"  ❌ FAILED: {error[:150]}\n")
            
            if "429" in error or "quota" in error.lower():
                print("  💡 This is a rate limit - you're hitting 15 req/min")
                print("  💡 Wait 60 seconds and try again")
                print("  💡 This means the model DOES work, just rate limited!\n")

if __name__ == "__main__":
    asyncio.run(test_gemini_25())
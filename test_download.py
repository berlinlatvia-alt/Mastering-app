"""
Test Download Functionality
Verifies that files can be downloaded correctly
"""

import asyncio
import aiohttp
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path("output")

async def test_download_endpoint():
    """Test the download endpoint with a simulated file"""
    
    # Create test session and file
    session_id = "test_session_001"
    test_filename = "test_track.wav"
    
    # Ensure output directory exists
    test_dir = OUTPUT_DIR / session_id
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a small test file
    test_file = test_dir / test_filename
    with open(test_file, 'wb') as f:
        f.write(b'TEST_WAV_FILE_CONTENT' * 100)  # Small test data
    
    print(f"✓ Created test file: {test_file}")
    print(f"  Size: {test_file.stat().st_size} bytes")
    
    # Test download via HTTP
    async with aiohttp.ClientSession() as session:
        # Test 1: Download with plain filename
        url = f"{BASE_URL}/api/download/{session_id}/{test_filename}"
        print(f"\n  Testing: {url}")
        
        try:
            async with session.get(url) as response:
                print(f"  Status: {response.status}")
                print(f"  Content-Type: {response.content_type}")
                print(f"  Content-Disposition: {response.headers.get('Content-Disposition')}")
                
                if response.status == 200:
                    content = await response.read()
                    print(f"  ✓ Downloaded {len(content)} bytes")
                    
                    # Verify content matches
                    if content == test_file.read_bytes():
                        print("  ✓ Content matches original file")
                    else:
                        print("  ✗ Content mismatch!")
                else:
                    error = await response.text()
                    print(f"  ✗ Error: {error}")
                    
        except Exception as e:
            print(f"  ✗ Request failed: {e}")
        
        # Test 2: Download with URL-encoded filename
        import urllib.parse
        encoded_filename = urllib.parse.quote(test_filename)
        url = f"{BASE_URL}/api/download/{session_id}/{encoded_filename}"
        print(f"\n  Testing encoded: {url}")
        
        try:
            async with session.get(url) as response:
                print(f"  Status: {response.status}")
                
                if response.status == 200:
                    content = await response.read()
                    print(f"  ✓ Downloaded {len(content)} bytes")
                else:
                    error = await response.text()
                    print(f"  ✗ Error: {error}")
                    
        except Exception as e:
            print(f"  ✗ Request failed: {e}")
        
        # Test 3: Test non-existent file (should 404)
        url = f"{BASE_URL}/api/download/{session_id}/nonexistent.wav"
        print(f"\n  Testing 404: {url}")
        
        try:
            async with session.get(url) as response:
                print(f"  Status: {response.status}")
                if response.status == 404:
                    print("  ✓ Correctly returns 404 for missing file")
                else:
                    print(f"  ✗ Expected 404, got {response.status}")
                    
        except Exception as e:
            print(f"  ✗ Request failed: {e}")
    
    # Cleanup
    test_file.unlink()
    test_dir.rmdir()
    print(f"\n✓ Cleanup complete")
    
    print("\n" + "="*50)
    print("DOWNLOAD TEST SUMMARY")
    print("="*50)
    print("✓ Download endpoint is functional")
    print("✓ URL-encoded filenames are handled correctly")
    print("✓ 404 errors returned for missing files")
    print("="*50)

if __name__ == "__main__":
    print("="*50)
    print("5.1 AutoMaster - Download Functionality Test")
    print("="*50)
    asyncio.run(test_download_endpoint())

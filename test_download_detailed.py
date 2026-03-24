"""
Test Download with Error Details
"""

import asyncio
import aiohttp

BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api"

async def test_download_detailed():
    """Test download with detailed error reporting"""
    
    print("="*60)
    print("Download Test - Detailed")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Upload a test file
        print("\n[1/4] Uploading test file...")
        try:
            # Create minimal WAV
            wav_header = bytes([
                0x52, 0x49, 0x46, 0x46, 0x24, 0x00, 0x00, 0x00,
                0x57, 0x41, 0x56, 0x45, 0x66, 0x6D, 0x74, 0x20,
                0x10, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
                0x80, 0xBB, 0x00, 0x00, 0x00, 0xEE, 0x02, 0x00,
                0x02, 0x00, 0x10, 0x00, 0x64, 0x61, 0x74, 0x61,
                0x00, 0x00, 0x00, 0x00,
            ])
            wav_data = wav_header + (b'\x00\x00' * 4800)  # ~0.1 sec silence
            
            formData = aiohttp.FormData()
            formData.add_field('file', wav_data, filename='test.wav', content_type='audio/wav')
            
            async with session.post(f"{API_BASE}/upload", data=formData) as resp:
                if resp.status != 200:
                    print(f"  ✗ Upload failed: {resp.status}")
                    return
                data = await resp.json()
                session_id = data['session_id']
                print(f"  ✓ Uploaded: {data['filename']}")
                print(f"  Session: {session_id}")
        except Exception as e:
            print(f"  ✗ Upload error: {e}")
            return
        
        # Step 2: Try to download (will 404 since not processed)
        print("\n[2/4] Testing download endpoint...")
        try:
            async with session.get(f"{API_BASE}/download/{session_id}/test.wav") as resp:
                print(f"  Status: {resp.status}")
                print(f"  Content-Type: {resp.content_type}")
                print(f"  Content-Disposition: {resp.headers.get('Content-Disposition')}")
                print(f"  Content-Length: {resp.headers.get('Content-Length')}")
                
                if resp.status == 404:
                    print("  ✓ 404 returned (expected - file not processed)")
                elif resp.status == 200:
                    content = await resp.read()
                    print(f"  ✓ Downloaded {len(content)} bytes")
                else:
                    error = await resp.text()
                    print(f"  ✗ Unexpected: {resp.status} - {error}")
        except Exception as e:
            print(f"  ✗ Download error: {e}")
        
        # Step 3: Test output directory endpoint
        print("\n[3/4] Testing output directory API...")
        try:
            async with session.get(f"{API_BASE}/output-dir") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  ✓ Current: {data['path']}")
                    print(f"  ✓ Default: {data['default']}")
                else:
                    print(f"  ✗ Failed: {resp.status}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Step 4: Test setting output directory
        print("\n[4/4] Testing set output directory...")
        try:
            import tempfile
            import os
            test_dir = os.path.join(tempfile.gettempdir(), 'test_downloads')
            
            async with session.post(f"{API_BASE}/output-dir", 
                                   json={"path": test_dir}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  ✓ Set to: {data['path']}")
                else:
                    error = await resp.text()
                    print(f"  ✗ Failed: {resp.status} - {error}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_download_detailed())

#!/usr/bin/env python3
"""
Debug script to test compression logic
"""

import os
import tempfile
from concat_videos import get_file_size_mb, compress_video
import requests

def test_compression_logic():
    """Test compression function directly"""
    print("🔍 Testing compression logic...")
    
    # Test URL that should work
    test_url = "https://v5.airtableusercontent.com/v3/u/41/41/1748296800000/BEJ4ysyR5Qf9rcQQU6DPmg/VGXsEGvf_EcXFnCZIjuQELyAM5-GQEDsdwdOg1cEw6MlwL_MmCyJt-IFXnYG3IJsQADAM-BSVM-_ArsYhjiWYQ26S2BQsP_LjbFYSpkmhPAw9Lz7LKT6EC4JtmB5FWXXahrWlrtZbaJUzKT8J6Z4L1-bOz2PdYCOrtt34J8fAnc/sIRlNdJKZHmEVh5EpdwbUeCs1AmELav1oX9Lb8cNbcc"
    
    # Download test video
    print("📥 Downloading test video...")
    response = requests.get(test_url, stream=True)
    
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            test_video_path = temp_file.name
        
        print(f"✅ Downloaded to: {test_video_path}")
        
        # Check file size
        original_size = get_file_size_mb(test_video_path)
        print(f"📊 Original size: {original_size:.1f}MB")
        
        if original_size > 50:  # Set a lower threshold for testing
            print("🗜️ Testing compression...")
            
            compressed_path = test_video_path + '.compressed.mp4'
            
            # Test compression
            success = compress_video(test_video_path, compressed_path, target_size_mb=50)
            
            if success and os.path.exists(compressed_path):
                compressed_size = get_file_size_mb(compressed_path)
                print(f"✅ Compression successful!")
                print(f"📊 Compressed size: {compressed_size:.1f}MB")
                print(f"📉 Reduction: {((original_size - compressed_size) / original_size) * 100:.1f}%")
                
                # Clean up
                os.remove(compressed_path)
            else:
                print("❌ Compression failed!")
        else:
            print("ℹ️ File is already small enough, no compression needed")
        
        # Clean up
        os.remove(test_video_path)
        
    else:
        print(f"❌ Failed to download test video: {response.status_code}")

if __name__ == "__main__":
    test_compression_logic() 
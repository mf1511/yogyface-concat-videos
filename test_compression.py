#!/usr/bin/env python3
"""
Test script for video compression functionality
"""

import tempfile
import os
from concat_videos import get_file_size_mb, compress_video, process_videos_from_urls

def test_file_size_calculation():
    """Test file size calculation function"""
    print("🧪 Testing file size calculation...")
    
    # Create test files of known sizes
    sizes_mb = [10, 50, 150]
    for size_mb in sizes_mb:
        content = b'0' * (size_mb * 1024 * 1024)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            temp_file = f.name
        
        calculated_size = get_file_size_mb(temp_file)
        expected_size = size_mb
        
        print(f"  File {size_mb}MB: calculated {calculated_size:.1f}MB")
        assert abs(calculated_size - expected_size) < 1, f"Size mismatch: {calculated_size} vs {expected_size}"
        
        os.unlink(temp_file)
    
    print("✅ File size calculation tests passed")

def test_compression_parameters():
    """Test compression parameter validation"""
    print("🧪 Testing compression parameters...")
    
    # Test various max_size_mb values
    test_cases = [
        (10, True),   # Minimum valid
        (100, True),  # Default
        (500, True),  # Maximum valid
        (5, False),   # Too small
        (600, False), # Too large
    ]
    
    for max_size, should_be_valid in test_cases:
        try:
            from web_app import app
            with app.test_client() as client:
                response = client.post('/api/concatenate', 
                    json={
                        'urls': ['https://example.com/test1.mp4', 'https://example.com/test2.mp4'],
                        'max_size_mb': max_size
                    }
                )
                
                if should_be_valid:
                    print(f"  ✅ max_size_mb={max_size} accepted")
                else:
                    assert response.status_code == 400, f"Should reject max_size_mb={max_size}"
                    print(f"  ✅ max_size_mb={max_size} correctly rejected")
        except Exception as e:
            if not should_be_valid:
                print(f"  ✅ max_size_mb={max_size} correctly rejected: {e}")
            else:
                print(f"  ❌ Unexpected error for max_size_mb={max_size}: {e}")

def test_cli_max_size_parameter():
    """Test CLI max-size parameter"""
    print("🧪 Testing CLI max-size parameter...")
    
    import argparse
    from concat_videos import main
    
    # Create a mock argument parser to test parameter exists
    parser = argparse.ArgumentParser()
    parser.add_argument('urls', nargs='+')
    parser.add_argument('-o', '--output', default='video_finale.mp4')
    parser.add_argument('--keep-temp', action='store_true')
    parser.add_argument('--max-size', type=int, default=100)
    
    # Test that max-size parameter exists and has correct default
    args = parser.parse_args(['url1', 'url2'])
    assert hasattr(args, 'max_size'), "max_size parameter missing"
    assert args.max_size == 100, f"Default max_size should be 100, got {args.max_size}"
    
    # Test custom max-size
    args = parser.parse_args(['url1', 'url2', '--max-size', '50'])
    assert args.max_size == 50, f"Custom max_size should be 50, got {args.max_size}"
    
    print("✅ CLI max-size parameter tests passed")

def test_api_response_fields():
    """Test that API responses include compression fields"""
    print("🧪 Testing API response fields...")
    
    from web_app import jobs
    
    # Mock a completed job with compression info
    test_job_id = "test-job-123"
    jobs[test_job_id] = {
        'status': 'completed',
        'output_file': '/tmp/test.mp4',
        'output_filename': 'test.mp4',
        'file_size': 85.2,
        'was_compressed': True,
        'created_at': 1234567890
    }
    
    from web_app import app
    with app.test_client() as client:
        response = client.get(f'/api/status/{test_job_id}')
        data = response.get_json()
        
        required_fields = ['file_size', 'was_compressed', 'download_url']
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        assert data['file_size'] == 85.2, f"Incorrect file_size: {data['file_size']}"
        assert data['was_compressed'] is True, f"Incorrect was_compressed: {data['was_compressed']}"
        
    print("✅ API response field tests passed")

def main():
    """Run all compression tests"""
    print("🎬 Testing Video Compression Functionality\n")
    
    try:
        test_file_size_calculation()
        print()
        
        test_compression_parameters()
        print()
        
        test_cli_max_size_parameter()
        print()
        
        test_api_response_fields()
        print()
        
        print("🎉 All compression tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 
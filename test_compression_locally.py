#!/usr/bin/env python3
"""
Test video compression locally to verify it works before upgrading Railway plan
"""

import subprocess
import time
import os
import tempfile
import sys

def get_video_duration(video_path):
    """Get video duration in seconds"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_format', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
    except:
        pass
    return None

def compress_video_test(input_path, target_size_mb=100):
    """Test compression with Railway-optimized settings"""
    
    print(f"🔍 Testing compression of: {input_path}")
    
    # Get original file size
    original_size = os.path.getsize(input_path)
    original_mb = original_size / (1024 * 1024)
    print(f"📊 Original size: {original_mb:.1f} MB")
    
    if original_mb <= target_size_mb:
        print(f"✅ File already under {target_size_mb}MB, no compression needed")
        return True
    
    # Get video duration
    duration = get_video_duration(input_path)
    if not duration:
        print("❌ Could not get video duration")
        return False
    
    print(f"⏱️  Video duration: {duration:.1f} seconds")
    
    # Calculate target bitrate
    target_size_bits = target_size_mb * 8 * 1024 * 1024
    target_bitrate = int((target_size_bits / duration) * 0.8)  # 80% for video, 20% for audio
    
    print(f"🎯 Target bitrate: {target_bitrate} bps")
    
    # Create output file
    output_path = input_path.replace('.mp4', '_compressed.mp4')
    
    # Compression command (Railway-optimized settings)
    cmd = [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264',          # H.264 codec
        '-preset', 'ultrafast',     # Fastest encoding (Railway optimized)
        '-crf', '30',               # Aggressive compression
        '-b:v', str(target_bitrate), # Target bitrate
        '-maxrate', str(int(target_bitrate * 1.2)), # Max bitrate
        '-bufsize', str(int(target_bitrate * 2)),   # Buffer size
        '-c:a', 'aac',              # Audio codec
        '-b:a', '64k',              # Low audio bitrate
        '-threads', '0',            # Use all CPU cores
        '-y',                       # Overwrite output
        output_path
    ]
    
    print(f"🔄 Starting compression...")
    print(f"💻 Command: {' '.join(cmd[:10])}...")
    
    start_time = time.time()
    
    try:
        # Run with timeout (5 minutes max)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        if result.returncode == 0:
            # Check compressed file size
            compressed_size = os.path.getsize(output_path)
            compressed_mb = compressed_size / (1024 * 1024)
            ratio = compressed_size / original_size
            
            print(f"✅ Compression completed in {elapsed:.1f} seconds")
            print(f"📊 Compressed size: {compressed_mb:.1f} MB")
            print(f"📉 Compression ratio: {ratio:.2f}")
            print(f"💾 Size reduction: {((1-ratio)*100):.1f}%")
            print(f"📁 Output file: {output_path}")
            
            success = compressed_mb <= target_size_mb
            if success:
                print(f"🎉 SUCCESS: File is now under {target_size_mb}MB!")
            else:
                print(f"⚠️  Still over {target_size_mb}MB, might need more aggressive settings")
            
            return success
        else:
            print(f"❌ Compression failed:")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Compression timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error during compression: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_compression_locally.py <video_file.mp4>")
        print("\nThis will test video compression with Railway-optimized settings")
        print("to verify it works before upgrading your Railway plan.")
        sys.exit(1)
    
    video_file = sys.argv[1]
    
    if not os.path.exists(video_file):
        print(f"❌ File not found: {video_file}")
        sys.exit(1)
    
    print("🚀 Railway Compression Test")
    print("=" * 50)
    print(f"Testing compression with Railway Pro plan equivalent settings")
    print(f"(ultrafast preset, aggressive compression, multi-core)")
    print()
    
    success = compress_video_test(video_file)
    
    print()
    print("=" * 50)
    if success:
        print("✅ LOCAL TEST PASSED!")
        print("👍 Compression works - upgrading to Railway Pro should solve the issue")
        print("💡 Railway Pro provides 32 vCPU + 32GB RAM for heavy processing")
    else:
        print("❌ LOCAL TEST FAILED!")
        print("🤔 The issue might not be just CPU/memory limits")
        print("📞 Consider checking Railway logs for other constraints")
    
    print()
    print("Railway Plan Comparison:")
    print("• Hobby: 8 vCPU, 8GB RAM ($5/month)")
    print("• Pro: 32 vCPU, 32GB RAM ($20/month)")
    print("• Enterprise: 64 vCPU, 64GB RAM (custom pricing)")

if __name__ == "__main__":
    main() 
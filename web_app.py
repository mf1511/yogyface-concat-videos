#!/usr/bin/env python3
"""
Web API for video concatenation service with compression support
Last updated: 2025-05-26 19:20:00 - Force deployment with compression
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse
import threading
import time
import subprocess

from flask import Flask, request, jsonify, send_file, render_template_string
from concat_videos import download_video, get_video_info, concatenate_videos, get_file_size_mb, compress_video
import shutil

app = Flask(__name__)

# Store job status and results
jobs = {}
UPLOAD_FOLDER = '/tmp/videos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_base_url(request):
    """Get the base URL for building download links"""
    return f"{request.scheme}://{request.headers.get('Host', 'localhost:5000')}"

# Simple HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Video Concatenation Tool</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0; }
        input, button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #007bff; color: white; cursor: pointer; }
        button:hover { background: #0056b3; }
        .url-input { width: 100%; margin: 10px 0; }
        .size-input { width: 100px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .processing { background: #d1ecf1; color: #0c5460; }
        .compression { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <h1>🎬 Video Concatenation Tool</h1>
    
    <div class="container">
        <h2>Concatenate Videos from URLs</h2>
        <form id="videoForm">
            <div>
                <input type="url" class="url-input" placeholder="Enter video URL 1" required>
                <input type="url" class="url-input" placeholder="Enter video URL 2" required>
            </div>
            <button type="button" onclick="addUrlInput()">+ Add More URLs</button>
            <br><br>
            <input type="text" id="outputName" placeholder="Output filename (optional)" value="concatenated_video.mp4">
            <br><br>
            <label>Max file size (MB): </label>
            <input type="number" id="maxSize" class="size-input" value="100" min="10" max="500">
            <small>Files larger than this will be automatically compressed</small>
            <br><br>
            <button type="submit">🚀 Start Concatenation</button>
        </form>
    </div>

    <div id="status" class="container" style="display:none;">
        <h3>Processing Status</h3>
        <div id="statusMessage"></div>
        <div id="downloadLink"></div>
    </div>

    <script>
        function addUrlInput() {
            const form = document.getElementById('videoForm');
            const input = document.createElement('input');
            input.type = 'url';
            input.className = 'url-input';
            input.placeholder = 'Enter video URL';
            input.required = true;
            form.insertBefore(input, form.children[1]);
        }

        document.getElementById('videoForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const urls = Array.from(document.querySelectorAll('.url-input'))
                .map(input => input.value)
                .filter(url => url.trim() !== '');
            
            const outputName = document.getElementById('outputName').value || 'concatenated_video.mp4';
            const maxSize = parseInt(document.getElementById('maxSize').value) || 100;
            
            if (urls.length < 2) {
                alert('Please provide at least 2 video URLs');
                return;
            }

            // Show status container
            document.getElementById('status').style.display = 'block';
            document.getElementById('statusMessage').innerHTML = '<div class="processing">Starting video concatenation...</div>';
            
            try {
                const response = await fetch('/api/concatenate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        urls: urls, 
                        output_name: outputName,
                        max_size_mb: maxSize
                    })
                });
                
                const result = await response.json();
                
                if (result.job_id) {
                    checkJobStatus(result.job_id);
                } else {
                    document.getElementById('statusMessage').innerHTML = '<div class="error">Error: ' + result.error + '</div>';
                }
            } catch (error) {
                document.getElementById('statusMessage').innerHTML = '<div class="error">Error: ' + error.message + '</div>';
            }
        });

        async function checkJobStatus(jobId) {
            try {
                const response = await fetch(`/api/status/${jobId}`);
                const status = await response.json();
                
                let statusClass = 'processing';
                if (status.status.includes('compress')) {
                    statusClass = 'compression';
                }
                
                document.getElementById('statusMessage').innerHTML = `<div class="${statusClass}">${status.status}</div>`;
                
                if (status.status === 'completed') {
                    let sizeInfo = status.file_size ? ` (${status.file_size}MB)` : '';
                    let compressionInfo = status.was_compressed ? 
                        ` ✨ Video was automatically compressed to reduce file size!` +
                        (status.original_size ? ` Original: ${status.original_size}MB` : '') +
                        (status.compression_ratio ? ` (${status.compression_ratio}% reduction)` : '') : '';
                    
                    document.getElementById('downloadLink').innerHTML = 
                        `<div class="success">✅ Video concatenated successfully!${sizeInfo}${compressionInfo}</div>
                         <p><strong>Download URL:</strong> <a href="${status.download_url}" target="_blank">${status.download_url}</a></p>
                         <a href="${status.download_url}" download><button>📥 Download Video</button></a>`;
                } else if (status.status === 'failed') {
                    document.getElementById('statusMessage').innerHTML = `<div class="error">❌ Error: ${status.error}</div>`;
                } else {
                    // Still processing, check again in 2 seconds
                    setTimeout(() => checkJobStatus(jobId), 2000);
                }
            } catch (error) {
                document.getElementById('statusMessage').innerHTML = '<div class="error">Error checking status: ' + error.message + '</div>';
            }
        }
    </script>
</body>
</html>
"""

def process_concatenation(job_id, urls, output_name, max_size_mb=100):
    """Background task to process video concatenation with compression"""
    try:
        jobs[job_id]['status'] = 'downloading_videos'
        
        # Create temporary directory for this job
        temp_dir = tempfile.mkdtemp(prefix=f'video_concat_{job_id}_')
        downloaded_videos = []
        
        # Download each video
        for i, url in enumerate(urls):
            jobs[job_id]['status'] = f'downloading_video_{i+1}_of_{len(urls)}'
            
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or f"video_{i+1}.mp4"
            
            # Ensure file has video extension
            if not any(filename.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']):
                filename += '.mp4'
            
            temp_path = os.path.join(temp_dir, filename)
            
            if download_video(url, temp_path):
                if get_video_info(temp_path):
                    downloaded_videos.append(temp_path)
                else:
                    jobs[job_id]['status'] = 'failed'
                    jobs[job_id]['error'] = f'Invalid video file: {url}'
                    return
            else:
                jobs[job_id]['status'] = 'failed'
                jobs[job_id]['error'] = f'Failed to download: {url}'
                return
        
        if len(downloaded_videos) < 2:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = 'Need at least 2 valid videos to concatenate'
            return
        
        # Concatenate videos
        jobs[job_id]['status'] = 'concatenating_videos'
        output_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{output_name}")
        
        # Use a modified concatenate function that tracks compression
        if concatenate_videos_with_tracking(downloaded_videos, output_path, max_size_mb, job_id):
            final_size = get_file_size_mb(output_path)
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['output_file'] = output_path
            jobs[job_id]['output_filename'] = output_name
            jobs[job_id]['file_size'] = round(final_size, 1)
            # was_compressed is set by concatenate_videos_with_tracking
        else:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = 'Failed to concatenate videos'
        
        # Cleanup temporary files
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)

def concatenate_videos_with_tracking(video_paths, output_path, max_size_mb, job_id):
    """Concatenate videos with compression tracking"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        concat_file = f.name
        for video_path in video_paths:
            # Escape special characters for ffmpeg
            escaped_path = video_path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    try:
        print("Concatenating videos...")
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file,
            '-c', 'copy', '-y', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            original_size = get_file_size_mb(output_path)
            print(f"✓ Video created: {output_path} ({original_size:.1f}MB)")
            
            # Store original size before compression
            jobs[job_id]['original_size'] = round(original_size, 1)
            jobs[job_id]['was_compressed'] = False
            
            # Check if compression is needed
            if original_size > max_size_mb:
                print(f"⚠ File too large ({original_size:.1f}MB > {max_size_mb}MB), compressing...")
                jobs[job_id]['status'] = 'compressing_video'
                
                # Create compressed version
                temp_compressed = output_path + '.compressed.mp4'
                
                print(f"🔧 Starting compression: {output_path} -> {temp_compressed}")
                print(f"🎯 Target size: {max_size_mb}MB")
                
                compression_success = compress_video(output_path, temp_compressed, max_size_mb)
                print(f"🔍 Compression result: {compression_success}")
                
                if compression_success and os.path.exists(temp_compressed):
                    # Verify the compressed file is valid and smaller
                    compressed_file_size = get_file_size_mb(temp_compressed)
                    print(f"📏 Compressed file size: {compressed_file_size:.1f}MB")
                    
                    if compressed_file_size > 0:  # Valid file
                        # Replace original with compressed version
                        os.replace(temp_compressed, output_path)
                        final_size = get_file_size_mb(output_path)
                        jobs[job_id]['was_compressed'] = True
                        
                        # Add compression ratio information
                        compression_ratio = ((original_size - final_size) / original_size) * 100
                        jobs[job_id]['compression_ratio'] = round(compression_ratio, 1)
                        
                        print(f"✓ Video compressed successfully: {final_size:.1f}MB ({compression_ratio:.1f}% reduction)")
                    else:
                        print("⚠ Compressed file is invalid (0 bytes), keeping original")
                        jobs[job_id]['compression_ratio'] = 0
                        if os.path.exists(temp_compressed):
                            os.remove(temp_compressed)
                else:
                    print("⚠ Compression failed or temp file missing, keeping original")
                    print(f"   compress_video returned: {compression_success}")
                    print(f"   temp file exists: {os.path.exists(temp_compressed) if 'temp_compressed' in locals() else 'N/A'}")
                    jobs[job_id]['compression_ratio'] = 0
                    # Clean up failed compression file
                    if os.path.exists(temp_compressed):
                        os.remove(temp_compressed)
            else:
                print(f"ℹ️ File size OK ({original_size:.1f}MB <= {max_size_mb}MB), no compression needed")
            
            return True
        else:
            print(f"✗ FFmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error during concatenation: {e}")
        return False
    finally:
        # Clean up temporary file
        os.unlink(concat_file)

@app.route('/')
def index():
    """Main web interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/concatenate', methods=['POST'])
def concatenate_api():
    """API endpoint to start video concatenation"""
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        output_name = data.get('output_name', 'concatenated_video.mp4')
        max_size_mb = data.get('max_size_mb', 100)
        sync = data.get('sync', False)  # Option for synchronous processing
        
        if len(urls) < 2:
            return jsonify({'error': 'At least 2 URLs required'}), 400
        
        if max_size_mb < 10 or max_size_mb > 500:
            return jsonify({'error': 'max_size_mb must be between 10 and 500'}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            'status': 'queued',
            'created_at': time.time()
        }
        
        base_url = get_base_url(request)
        
        if sync:
            # Process synchronously and return download URL immediately
            process_concatenation(job_id, urls, output_name, max_size_mb)
            job = jobs[job_id]
            
            if job['status'] == 'completed':
                download_url = f"{base_url}/api/download/{job_id}"
                return jsonify({
                    'status': 'completed',
                    'job_id': job_id,
                    'download_url': download_url,
                    'filename': output_name,
                    'file_size': job.get('file_size'),
                    'original_size': job.get('original_size'),
                    'was_compressed': job.get('was_compressed', False),
                    'compression_ratio': job.get('compression_ratio', 0)
                })
            else:
                return jsonify({
                    'status': 'failed',
                    'job_id': job_id,
                    'error': job.get('error', 'Unknown error')
                }), 500
        else:
            # Start background processing
            thread = threading.Thread(target=process_concatenation, args=(job_id, urls, output_name, max_size_mb))
            thread.start()
            
            return jsonify({
                'job_id': job_id, 
                'status': 'queued',
                'status_url': f"{base_url}/api/status/{job_id}",
                'max_size_mb': max_size_mb
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get job status with download URL when completed"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    base_url = get_base_url(request)
    
    # Make status messages more user-friendly
    status_messages = {
        'queued': 'Queued for processing',
        'downloading_videos': 'Downloading videos from URLs',
        'concatenating_videos': 'Concatenating videos together',
        'compressing_video': 'Compressing video to reduce file size',
        'completed': 'Processing completed successfully',
        'failed': 'Processing failed'
    }
    
    display_status = status_messages.get(job['status'], job['status'])
    if job['status'].startswith('downloading_video_'):
        display_status = f"Downloading videos ({job['status'].split('_')[2]} of {job['status'].split('_')[4]})"
    
    response = {
        'status': display_status,
        'job_id': job_id
    }
    
    if 'error' in job:
        response['error'] = job['error']
    
    if job['status'] == 'completed':
        response['download_url'] = f"{base_url}/api/download/{job_id}"
        response['filename'] = job.get('output_filename', 'concatenated_video.mp4')
        response['file_size'] = job.get('file_size')
        response['original_size'] = job.get('original_size')
        response['was_compressed'] = job.get('was_compressed', False)
        response['compression_ratio'] = job.get('compression_ratio', 0)
    
    return jsonify(response)

@app.route('/api/download/<job_id>')
def download_video_file(job_id):
    """Download completed video"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    if 'output_file' not in job or not os.path.exists(job['output_file']):
        return jsonify({'error': 'Output file not found'}), 404
    
    filename = job.get('output_filename', 'concatenated_video.mp4')
    return send_file(job['output_file'], as_attachment=True, download_name=filename)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check if compression function is available
        from concat_videos import compress_video
        compression_available = True
    except ImportError:
        compression_available = False
    
    return jsonify({
        'status': 'healthy',
        'compression_available': compression_available,
        'timestamp': '2025-05-26T19:20:00Z',
        'version': 'v2.1-with-compression'
    })

@app.route('/api/version')
def version_check():
    """Version check endpoint to verify deployment"""
    try:
        from concat_videos import compress_video
        return jsonify({
            'version': 'v2.1-with-compression',
            'compression_available': True,
            'timestamp': '2025-05-26T19:20:00Z',
            'git_commit': '30482d8'
        })
    except ImportError:
        return jsonify({
            'version': 'v1.0-no-compression', 
            'compression_available': False,
            'error': 'Compression module not found'
        })

# Cleanup old jobs periodically
def cleanup_old_jobs():
    """Remove jobs older than 1 hour"""
    current_time = time.time()
    to_remove = []
    
    for job_id, job in jobs.items():
        if current_time - job.get('created_at', 0) > 3600:  # 1 hour
            # Remove output file if exists
            if 'output_file' in job and os.path.exists(job['output_file']):
                os.remove(job['output_file'])
            to_remove.append(job_id)
    
    for job_id in to_remove:
        del jobs[job_id]

# Start cleanup thread
def start_cleanup_thread():
    def cleanup_loop():
        while True:
            time.sleep(300)  # 5 minutes
            cleanup_old_jobs()
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()

if __name__ == '__main__':
    start_cleanup_thread()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 
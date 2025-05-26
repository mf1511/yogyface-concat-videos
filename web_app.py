#!/usr/bin/env python3
"""
Web API for video concatenation service
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse
import threading
import time

from flask import Flask, request, jsonify, send_file, render_template_string
from concat_videos import download_video, get_video_info, concatenate_videos
import shutil

app = Flask(__name__)

# Store job status and results
jobs = {}
UPLOAD_FOLDER = '/tmp/videos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .processing { background: #d1ecf1; color: #0c5460; }
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
                    body: JSON.stringify({ urls: urls, output_name: outputName })
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
                
                document.getElementById('statusMessage').innerHTML = `<div class="processing">${status.status}</div>`;
                
                if (status.status === 'completed') {
                    document.getElementById('downloadLink').innerHTML = 
                        `<div class="success">✅ Video concatenated successfully!</div>
                         <a href="/api/download/${jobId}" download><button>📥 Download Video</button></a>`;
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

def process_concatenation(job_id, urls, output_name):
    """Background task to process video concatenation"""
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
        
        if concatenate_videos(downloaded_videos, output_path):
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['output_file'] = output_path
        else:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = 'Failed to concatenate videos'
        
        # Cleanup temporary files
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)

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
        
        if len(urls) < 2:
            return jsonify({'error': 'At least 2 URLs required'}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            'status': 'queued',
            'created_at': time.time()
        }
        
        # Start background processing
        thread = threading.Thread(target=process_concatenation, args=(job_id, urls, output_name))
        thread.start()
        
        return jsonify({'job_id': job_id, 'status': 'queued'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    response = {'status': job['status']}
    
    if 'error' in job:
        response['error'] = job['error']
    
    return jsonify(response)

@app.route('/api/download/<job_id>')
def download_video(job_id):
    """Download completed video"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    if 'output_file' not in job or not os.path.exists(job['output_file']):
        return jsonify({'error': 'Output file not found'}), 404
    
    return send_file(job['output_file'], as_attachment=True)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

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
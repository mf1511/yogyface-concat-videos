# Railway Deployment Guide

## Overview

This guide explains how to deploy your video concatenation tool as a web service on Railway.

## What Gets Deployed

- **Web Interface**: Simple HTML form to input video URLs with compression settings
- **REST API**: Endpoints for programmatic access with downloadable URLs
- **Background Processing**: Async video processing with status tracking
- **Direct Downloads**: Download URLs included in API responses
- **Automatic Compression**: Videos larger than specified size are automatically compressed

## Pre-deployment Setup

1. **Install Flask locally** (for testing):

```bash
source venv/bin/activate
pip install Flask==3.0.3
```

2. **Test locally**:

```bash
python web_app.py
```

Visit http://localhost:5000 to test the interface.

## Railway Deployment Steps

### 1. Create Railway Account

- Go to [railway.app](https://railway.app)
- Sign up with GitHub account

### 2. Connect Repository

- Click "New Project"
- Select "Deploy from GitHub repo"
- Connect this repository

### 3. Configure Environment

Railway will automatically:

- Detect Python project via Dockerfile
- Install dependencies from `requirements.txt`
- Install ffmpeg system dependency
- Use `Dockerfile` for containerized deployment

### 4. Custom Domain (Optional)

- Go to project settings
- Add custom domain
- Configure DNS

## API Endpoints

Once deployed, your service will have these endpoints:

### Web Interface

- `GET /` - Main web interface

### API Endpoints

- `POST /api/concatenate` - Start video concatenation (returns download URL when completed)
- `GET /api/status/<job_id>` - Check job status (includes download URL when ready)
- `GET /api/download/<job_id>` - Download completed video file
- `GET /health` - Health check

### API Usage Examples

#### Asynchronous Processing (Default)

```bash
# Start concatenation with automatic compression for files > 100MB
curl -X POST https://your-app.railway.app/api/concatenate \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com/video1.mp4", "https://example.com/video2.mp4"], "output_name": "result.mp4", "max_size_mb": 100}'

# Response includes status URL
{
  "job_id": "uuid-here",
  "status": "queued",
  "status_url": "https://your-app.railway.app/api/status/uuid-here",
  "max_size_mb": 100
}

# Check status (includes download URL when completed)
curl https://your-app.railway.app/api/status/uuid-here

# Response when completed (with compression info)
{
  "status": "Processing completed successfully",
  "job_id": "uuid-here",
  "download_url": "https://your-app.railway.app/api/download/uuid-here",
  "filename": "result.mp4",
  "file_size": 85.2,
  "was_compressed": true
}
```

#### Synchronous Processing

```bash
# Process synchronously with custom max size
curl -X POST https://your-app.railway.app/api/concatenate \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com/video1.mp4", "https://example.com/video2.mp4"], "sync": true, "max_size_mb": 50}'

# Response includes download URL immediately
{
  "status": "completed",
  "job_id": "uuid-here",
  "download_url": "https://your-app.railway.app/api/download/uuid-here",
  "filename": "concatenated_video.mp4",
  "file_size": 48.7,
  "was_compressed": true
}
```

#### New API Parameters

- `max_size_mb` (optional): Maximum file size in MB before compression (default: 100, range: 10-500)
- Response includes:
  - `file_size`: Final file size in MB
  - `was_compressed`: Boolean indicating if compression was applied

## Important Notes

### Compression Feature

- **Automatic**: Videos over the specified size limit are automatically compressed
- **Quality**: Uses H.264 codec with optimized settings for web delivery
- **Bitrate Calculation**: Automatically calculates optimal bitrate based on video duration
- **Minimum Quality**: Ensures minimum quality thresholds (500kbps video, 64kbps audio)
- **Status Updates**: Real-time status updates during compression process

### File Storage

- Videos are stored temporarily (1 hour max)
- Download URLs are valid immediately after processing
- Large files may take time to process and compress
- Compression time depends on original video size and target size

### Limitations

- Maximum file size depends on Railway limits
- Processing time varies with video size and compression requirements
- Concurrent job limit: depends on Railway plan
- Sync mode may timeout for large videos requiring compression
- Max size range: 10MB - 500MB

### Monitoring

- Check Railway dashboard for logs
- Use `/health` endpoint for monitoring
- Monitor CPU/memory usage in Railway

## Troubleshooting

### Common Issues

1. **Build fails**: Check Dockerfile and requirements.txt
2. **ffmpeg not found**: Verify Dockerfile includes ffmpeg installation
3. **App won't start**: Check Railway logs for Python errors
4. **Download URLs not working**: Check base URL construction

### Logs

Check Railway deployment logs:

- Build logs for dependency issues
- Runtime logs for application errors
- Use `railway logs` CLI command

## Cost Optimization

- Use Railway's sleep mode for development
- Monitor bandwidth usage (downloads count toward limits)
- Implement file cleanup policies
- Consider caching for repeated requests

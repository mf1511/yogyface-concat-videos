# Railway Deployment Guide

## Overview

This guide explains how to deploy your video concatenation tool as a web service on Railway.

## What Gets Deployed

- **Web Interface**: Simple HTML form to input video URLs
- **REST API**: Endpoints for programmatic access
- **Background Processing**: Async video processing with status tracking
- **File Downloads**: Direct download of concatenated videos

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

- Detect Python project
- Install dependencies from `requirements.txt`
- Install ffmpeg via `nixpacks.toml`
- Use `Procfile` to start the web server

### 4. Custom Domain (Optional)

- Go to project settings
- Add custom domain
- Configure DNS

## API Endpoints

Once deployed, your service will have these endpoints:

### Web Interface

- `GET /` - Main web interface

### API Endpoints

- `POST /api/concatenate` - Start video concatenation
- `GET /api/status/<job_id>` - Check job status
- `GET /api/download/<job_id>` - Download completed video
- `GET /health` - Health check

### API Usage Example

```bash
# Start concatenation
curl -X POST https://your-app.railway.app/api/concatenate \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com/video1.mp4", "https://example.com/video2.mp4"], "output_name": "result.mp4"}'

# Check status
curl https://your-app.railway.app/api/status/<job_id>

# Download result
curl -O https://your-app.railway.app/api/download/<job_id>
```

## Important Notes

### File Storage

- Videos are stored temporarily (1 hour max)
- Downloads are available immediately after processing
- Large files may take time to process

### Limitations

- Maximum file size depends on Railway limits
- Processing time varies with video size
- Concurrent job limit: depends on Railway plan

### Monitoring

- Check Railway dashboard for logs
- Use `/health` endpoint for monitoring
- Monitor CPU/memory usage in Railway

## Troubleshooting

### Common Issues

1. **ffmpeg not found**

   - Check `nixpacks.toml` configuration
   - Verify deployment logs

2. **Out of memory**

   - Upgrade Railway plan
   - Optimize video processing

3. **Timeout errors**
   - Large videos may need more time
   - Consider splitting into smaller chunks

### Logs

Check Railway deployment logs:

- Build logs for dependency issues
- Runtime logs for application errors
- Use `railway logs` CLI command

## Cost Optimization

- Use Railway's sleep mode for development
- Monitor bandwidth usage
- Implement file cleanup policies
- Consider caching for repeated requests

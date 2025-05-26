# Video Concatenation Tool

A Python script and web service to download and concatenate videos from URLs.

## Features

- **CLI Tool**: Command-line interface for local use
- **Web Interface**: Simple HTML form for easy video concatenation
- **REST API**: Programmatic access for integration
- **Background Processing**: Async video processing with status tracking
- **Auto Cleanup**: Temporary files are automatically cleaned up
- **Multiple Formats**: Support for .mp4, .avi, .mkv, .mov, .wmv

## Prerequisites

- Python 3.6+
- ffmpeg (install with `brew install ffmpeg` on macOS)

## Local Setup

1. Create a virtual environment:

```bash
python3 -m venv venv
```

2. Activate the virtual environment:

```bash
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### CLI Tool (Local)

```bash
# Basic usage
python concat-videos.py https://example.com/video1.mp4 https://example.com/video2.mp4

# Specify output filename
python concat-videos.py -o my_output.mp4 https://example.com/video1.mp4 https://example.com/video2.mp4

# Keep temporary files
python concat-videos.py --keep-temp https://example.com/video1.mp4 https://example.com/video2.mp4

# Using wrapper script
./run.sh https://example.com/video1.mp4 https://example.com/video2.mp4
```

### Web Application (Local)

```bash
# Start web server
python web_app.py

# Visit http://localhost:5000 in your browser
```

### Web Application (Deployed)

Once deployed to Railway, you can:

- Visit the web interface at your Railway URL
- Use the REST API endpoints programmatically

## Railway Deployment 🚀

This project is ready for deployment on Railway! See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### Quick Deploy

1. Fork this repository
2. Connect to Railway
3. Deploy automatically with included configuration files

### Deployment Files

- `Procfile` - Railway process configuration
- `nixpacks.toml` - System dependencies (ffmpeg)
- `railway.json` - Railway-specific settings
- `requirements.txt` - Python dependencies

## API Reference

### Endpoints

- `GET /` - Web interface
- `POST /api/concatenate` - Start concatenation job
- `GET /api/status/<job_id>` - Check job status
- `GET /api/download/<job_id>` - Download result
- `GET /health` - Health check

### API Example

```bash
# Start concatenation
curl -X POST https://your-app.railway.app/api/concatenate \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com/video1.mp4", "https://example.com/video2.mp4"]}'

# Response: {"job_id": "uuid-here", "status": "queued"}

# Check status
curl https://your-app.railway.app/api/status/uuid-here

# Download when completed
curl -O https://your-app.railway.app/api/download/uuid-here
```

## CLI Arguments

- `urls`: One or more URLs of videos to download and concatenate
- `-o, --output`: Output filename (default: video_finale.mp4)
- `--keep-temp`: Keep temporary downloaded files (default: false)

## File Structure

```
├── concat-videos.py     # Original CLI script
├── concat_videos.py     # Refactored module for API
├── web_app.py          # Flask web application
├── run.sh              # CLI wrapper script
├── requirements.txt    # Python dependencies
├── Procfile           # Railway process config
├── nixpacks.toml      # System dependencies
├── railway.json       # Railway settings
├── README.md          # This file
└── DEPLOYMENT.md      # Deployment guide
```

## Development

### Local Testing

```bash
# Test CLI
source venv/bin/activate
python concat-videos.py --help

# Test web app
python web_app.py
# Visit http://localhost:5000
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## Troubleshooting

### Common Issues

- **ffmpeg not found**: Install with `brew install ffmpeg`
- **Virtual environment**: Always activate with `source venv/bin/activate`
- **Permissions**: Make run.sh executable with `chmod +x run.sh`

### Railway Issues

See [DEPLOYMENT.md](DEPLOYMENT.md) for Railway-specific troubleshooting.

## License

This project is open source and available under the MIT License.

# Video Concatenation Tool 🎬

Télécharge et concatène des vidéos depuis des URLs avec compression automatique.

## Fonctionnalités

- ✅ Téléchargement de vidéos depuis des URLs
- ✅ Concaténation de plusieurs vidéos
- ✅ **Compression automatique** pour les fichiers > 100MB
- ✅ Interface web moderne
- ✅ API REST avec URLs de téléchargement
- ✅ Traitement asynchrone avec suivi de statut
- ✅ Déploiement Railway ready

## Nouvelle fonctionnalité: Compression intelligente

Le système compresse automatiquement les vidéos qui dépassent la taille limite spécifiée:

- **Calcul intelligent du bitrate** basé sur la durée de la vidéo
- **Codec H.264 optimisé** pour la livraison web
- **Seuils de qualité minimale** garantis (500kbps vidéo, 64kbps audio)
- **Taille personnalisable** de 10MB à 500MB
- **Statut en temps réel** pendant la compression

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
# Basic usage (with 100MB compression limit)
python concat-videos.py https://example.com/video1.mp4 https://example.com/video2.mp4

# Specify output filename and custom compression limit
python concat-videos.py -o my_output.mp4 --max-size 50 https://example.com/video1.mp4 https://example.com/video2.mp4

# No compression (500MB limit)
python concat-videos.py --max-size 500 https://example.com/video1.mp4 https://example.com/video2.mp4

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
# Start concatenation with automatic compression
curl -X POST https://your-app.railway.app/api/concatenate \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com/video1.mp4", "https://example.com/video2.mp4"],
    "max_size_mb": 100
  }'

# Response: {"job_id": "uuid-here", "status": "queued", "max_size_mb": 100}

# Check status (includes compression info)
curl https://your-app.railway.app/api/status/uuid-here

# Response when completed:
{
  "status": "Processing completed successfully",
  "job_id": "uuid-here",
  "download_url": "https://your-app.railway.app/api/download/uuid-here",
  "filename": "concatenated_video.mp4",
  "file_size": 85.2,
  "was_compressed": true
}

# Synchronous processing with compression
curl -X POST https://your-app.railway.app/api/concatenate \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com/video1.mp4", "https://example.com/video2.mp4"],
    "sync": true,
    "max_size_mb": 75
  }'
```

## CLI Arguments

- `urls`: One or more URLs of videos to download and concatenate
- `-o, --output`: Output filename (default: video_finale.mp4)
- `--keep-temp`: Keep temporary downloaded files (default: false)
- `--max-size`: Maximum file size in MB before compression (default: 100, range: 10-500)

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

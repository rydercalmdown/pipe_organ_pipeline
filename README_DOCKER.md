# Pipe Organ Pipeline - Docker Setup

A Flask web application that converts audio files to organ-optimized MIDI using AI-powered stem separation and transcription.

## Features

- **Web Interface**: Upload MP3, WAV, M4A, or FLAC files through a modern web interface
- **AI Stem Separation**: Uses Demucs to separate audio into drums, bass, vocals, and other instruments
- **MIDI Transcription**: Converts each stem to MIDI using BasicPitch neural network
- **Organ Optimization**: Maps tracks to organ channels (Great, Swell, Pedal) for authentic sound
- **Real-time Processing**: Live progress updates during processing
- **File Management**: Automatic cleanup and organized file storage

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available for the container
- 10GB+ free disk space for processing

### Running the Application

1. **Clone and navigate to the project:**
   ```bash
   git clone <your-repo-url>
   cd pipe_organ_pipeline
   ```

2. **Start the application:**
   ```bash
   docker-compose up --build
   ```

3. **Access the web interface:**
   Open your browser and go to `http://localhost:5000`

4. **Upload and process audio:**
   - Upload an audio file (MP3, WAV, M4A, or FLAC)
   - Wait for processing to complete (may take several minutes)
   - Download your results: stems, individual MIDI files, and combined MIDI

### Data Persistence

- Uploaded files and results are stored in the `./data/` directory
- This directory is mounted as a volume, so your data persists between container restarts
- The `data/` directory contains:
  - `uploads/` - Temporary uploaded files (auto-cleaned after processing)
  - `results/` - Processed files organized by job ID

## File Structure

```
pipe_organ_pipeline/
├── app.py                 # Flask web application
├── pipeline.py           # Core processing logic
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── processing.html
│   └── results.html
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── data/                 # Volume mount (created automatically)
│   ├── uploads/
│   └── results/
└── README_DOCKER.md
```

## API Endpoints

- `GET /` - Upload page
- `POST /upload` - Upload audio file
- `GET /processing/<job_id>` - Processing status page
- `GET /api/status/<job_id>` - JSON status API
- `GET /results/<job_id>` - Results page
- `GET /download/<job_id>/<file_type>/<filename>` - Download files

## Processing Pipeline

1. **Upload**: User uploads audio file
2. **Stem Separation**: Demucs separates audio into 4 stems
3. **MIDI Transcription**: BasicPitch converts each stem to MIDI
4. **MIDI Merging**: Individual MIDI files are merged with organ channel mapping
5. **Results**: User can download all generated files

## Output Files

### Combined MIDI File
- `combined.mid` - Complete organ-optimized MIDI
- **Channel Mapping:**
  - Channel 0 (Pedal): Drums - Bass drum sounds
  - Channel 1 (Pedal): Bass - Acoustic bass sounds  
  - Channel 2 (Swell): Vocals - Piano sounds in melody range
  - Channel 3 (Great): Other - Piano sounds for accompaniment

### Audio Stems
- `{track_name}_drums.wav` - Separated drums
- `{track_name}_bass.wav` - Separated bass
- `{track_name}_vocals.wav` - Separated vocals
- `{track_name}_other.wav` - Separated other instruments

### Individual MIDI Files
- `drums.mid` - MIDI transcription of drums
- `bass.mid` - MIDI transcription of bass
- `vocals.mid` - MIDI transcription of vocals
- `other.mid` - MIDI transcription of other instruments

## Configuration

### Environment Variables
- `FLASK_ENV` - Flask environment (production/development)
- `FLASK_APP` - Flask application file
- `MAX_CONTENT_LENGTH` - Maximum upload file size (default: 100MB)

### Resource Requirements
- **CPU**: Multi-core recommended for faster processing
- **RAM**: 4GB+ recommended (8GB+ for large files)
- **Storage**: 10GB+ free space for processing and results
- **Network**: Internet required for initial model downloads

## Troubleshooting

### Common Issues

1. **Out of Memory Error**
   - Increase Docker memory limit
   - Use smaller audio files
   - Close other applications

2. **Processing Takes Too Long**
   - Large files (>50MB) take longer to process
   - Complex audio with many instruments takes longer
   - Check system resources

3. **Upload Fails**
   - Check file size (max 100MB)
   - Ensure file format is supported (MP3, WAV, M4A, FLAC)
   - Check available disk space

4. **Container Won't Start**
   - Ensure Docker has enough resources
   - Check if port 5000 is available
   - Review Docker logs: `docker-compose logs`

### Logs and Debugging

```bash
# View application logs
docker-compose logs -f

# View logs for specific service
docker-compose logs pipe-organ-pipeline

# Access container shell
docker-compose exec pipe-organ-pipeline bash

# Restart services
docker-compose restart
```

## Development

### Local Development Setup

1. **Install dependencies:**
   ```bash
   # Install UV package manager
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install Python dependencies
   uv sync
   ```

2. **Run locally:**
   ```bash
   uv run python app.py
   ```

3. **Access at:** `http://localhost:5000`

### Building Custom Docker Image

```bash
# Build image
docker build -t pipe-organ-pipeline .

# Run container
docker run -p 5000:5000 -v $(pwd)/data:/app/data pipe-organ-pipeline
```

## Security Notes

- Change the Flask secret key in production
- Consider adding authentication for production use
- Implement rate limiting for upload endpoints
- Use HTTPS in production environments
- Regularly clean up old processing results

## License

[Add your license information here]

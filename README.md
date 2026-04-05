# MTV

A simple, stateless IPTV streaming server. Think of it as a lightweight ErsatzTV that streams your movie collection as a continuous TV channel.

## Features

- **No transcoding**: Uses `-c copy` for zero CPU overhead
- **Stateless design**: Fresh scan on every startup, no database
- **Fixed epoch timetable**: Movie schedule is deterministic across restarts
- **Smart subtitle handling**: 
  - External subtitles (`.srt`, `.sub`, `.idx`, `.vtt`) take priority
  - Internal subtitles: prefers English, normal over SDH
  - First subtitle set as default in player
- **Smart audio selection**: 
  - Prefers English audio (`en` or `eng`)
  - Falls back to any audio (no mute movies)
- **Kodi optimized**: M3U playlist with `inputstream.ffmpegdirect` and EPG support
- **EPG support**: XMLTV format with fixed timetable (all movies or 24h minimum)
- **Docker support**: Ready-to-use container with FFmpeg included

## How It Works

1. On startup, scans your movie folder for `.mp4` and `.mkv` files
2. Extracts metadata using `ffprobe` (duration, codecs, audio/subtitle streams)
3. Shuffles movies randomly
4. Calculates which movie should be playing based on a fixed epoch time
5. Streams movies with `-c copy` (no transcoding)
6. When a movie ends, the connection closes (client reconnects for next movie)

## Quick Start

### Prerequisites

- Python 3.10+
- FFmpeg/FFprobe installed
- Movie folder with `.mp4`/`.mkv` files

### Installation

```bash
# Clone or download the project
cd MTV

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .

# Configure (edit config/config.yaml)
# Set your movie folder path and LAN IP
```

### Configuration

Edit `config/config.yaml`:

```yaml
server:
  host: "0.0.0.0"              # Bind to all interfaces
  port: 8555
  advertised_host: "192.168.1.100"  # ← Your LAN IP (important for EPG!)

media:
  folder: "/path/to/movies"     # ← Change this!
  prefer_english: true

timetable:
  epoch: 1704067200            # Fixed reference time (Unix timestamp)
```

**Important**: Set `advertised_host` to your server's LAN IP address. This is used in the M3U and EPG URLs so clients can connect.

### Running

```bash
# From project root
python -m mtv

# Or using the installed command
mtv
```

### Docker (Recommended)

```bash
# Update movie path in docker-compose.yml
# Then build and run
docker compose up -d --build

# Access at http://your-ip:8555/m3u
```

See [DOCKER.md](DOCKER.md) for complete Docker deployment guide.

### Kodi Setup

1. Install `inputstream.ffmpegdirect` addon in Kodi
2. Open Kodi → TV → Add-ons → PVR IPTV Simple Client → Settings
3. Set path to M3U play list: `http://YOUR_IP:8555/m3u`
4. Enable "M3U Extended Info"
5. Set path to EPG: `http://YOUR_IP:8555/epg`
6. Save and restart

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/m3u` | M3U playlist with EPG reference |
| `/epg` or `/epg.xml` | XMLTV EPG data |
| `/health` | Health check (JSON) |
| `/stream/` | Current movie stream (based on timetable) |

## Timetable Algorithm

MTV uses a **fixed epoch** approach for the timetable:

```
current_position = (now - EPOCH) MOD total_playlist_duration
```

This means:
- The schedule is deterministic regardless of server restarts
- All clients see the same movie at the same time
- EPG times are fixed and don't change on refresh
- Changing the `epoch` value shifts the entire schedule

### Example

If your playlist is 10 hours total and the epoch was January 1, 2024:
- At exactly 10 hours after epoch → Movie #1 starts
- At 15 hours after epoch → Movie #2 at 50%
- At 20 hours after epoch → Back to Movie #1 (cycle 2)

## Subtitle & Audio Selection

### Subtitles

1. **External subtitle present** (e.g., `movie.srt`):
   - Only external subtitle included
   - Set as default

2. **No external subtitle**:
   - Preferred languages from config (in order)
   - Normal subtitles before SDH for same language
   - If no preferred language: Unknown language only
   - Other languages excluded
   - First subtitle set as default

### Audio

1. **Single audio stream**: Always included (no mute movies)
2. **Multiple streams**: Preferred languages from config (in order)
3. **Fallback**: First stream if no match

### Configuration

Edit `config/config.yaml`:

```yaml
media:
  preferred_languages:
    audio: ["en", "eng", "es"]      # English first, then Spanish
    subtitle: ["en", "eng"]         # English only
```

Languages are checked in order - first match wins. Common codes:
- `en`/`eng` (English)
- `es` (Spanish)
- `fr` (French)
- `de` (German)
- `it` (Italian)
- `pt` (Portuguese)
- `ru` (Russian)
- `ja` (Japanese)

## Project Structure

```
MTV/
├── config/
│   └── config.yaml          # Configuration
├── src/mtv/
│   ├── main.py              # Entry point
│   ├── config.py            # Config loading
│   ├── scanner.py           # Media folder scanner
│   ├── library.py           # In-memory library
│   ├── scheduler.py         # Timetable algorithm
│   ├── models/
│   │   └── movie.py         # Movie data model
│   ├── server/
│   │   ├── handlers.py      # HTTP request handlers
│   │   └── streamer.py      # FFmpeg process manager
│   ├── api/
│   │   ├── playlist.py      # M3U generation
│   │   └── epg.py           # XMLTV generation
│   └── utils/
│       ├── ffprobe.py       # FFprobe wrapper
│       └── ffmpeg.py        # FFmpeg command builder
├── Dockerfile               # Docker build
├── docker-compose.yml       # Docker Compose config
├── DOCKER.md               # Docker deployment guide
├── requirements.txt
└── README.md
```

## Raspberry Pi Deployment

### 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv
```

### 2. Setup MTV

```bash
# Create installation directory
sudo mkdir -p /opt/mtv
sudo chown $USER:$USER /opt/mtv

cd /opt/mtv
# Copy project files here

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install
pip install -e .
```

### 3. Configure

Edit `/opt/mtv/config/config.yaml` with your movie folder path and LAN IP.

### 4. Create Systemd Service

```bash
sudo tee /etc/systemd/system/mtv.service << 'EOF'
[Unit]
Description=MTV Streaming Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/mtv
Environment="PATH=/opt/mtv/venv/bin:$PATH"
ExecStart=/opt/mtv/venv/bin/python -m mtv
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 5. Enable and Start

```bash
sudo systemctl enable mtv
sudo systemctl start mtv
sudo systemctl status mtv
```

## Troubleshooting

### No movies found

- Check `config/config.yaml` has correct path
- Ensure files are `.mp4` or `.mkv`
- Check file permissions

### Stream won't play in Kodi

- Ensure `inputstream.ffmpegdirect` addon is installed
- Check firewall allows port 8555
- Try accessing `http://IP:8555/health` to verify server is running
- Verify `advertised_host` is set to your LAN IP

### Wrong audio language

- Check that audio stream has `language` tag in metadata
- MTV prefers English (`en` or `eng` tags)
- If only one audio stream exists, it will be used regardless of language

### Subtitles not showing

- Ensure subtitle file has same basename as movie (for external)
- Supported formats: `.srt`, `.sub`, `.idx`, `.vtt`
- Example: `movie.mkv` → `movie.srt`
- Internal subtitles: check language tags with `ffprobe`

### EPG times keep changing

- This shouldn't happen anymore (fixed in recent version)
- EPG now uses fixed epoch timetable
- Times are deterministic and won't shift on refresh

### High CPU usage

- MTV uses `-c copy` (no transcoding)
- High CPU indicates something else is wrong
- Check you're not accidentally transcoding

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
ruff check src/
ruff format src/
```

## Philosophy

MTV is designed for simplicity:

- **No database**: Everything is in-memory, scanned fresh on startup
- **No transcoding**: Respects your hardware limitations
- **No complexity**: YAML config, standard library HTTP server
- **Pet project friendly**: Easy to understand, easy to modify
- **Docker ready**: Deploy anywhere with a single command

## License

MIT

## Acknowledgments

- Inspired by ErsatzTV but simplified
- Uses FFmpeg for streaming
- Kodi's `inputstream.ffmpegdirect` for direct MKV playback

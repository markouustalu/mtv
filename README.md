# Marko TV (MTV)

A simple, stateless IPTV streaming server for Raspberry Pi 4. Think of it as a lightweight ErsatzTV that streams your movie collection as a continuous TV channel.

## Features

- **No transcoding**: Uses `-c copy` for zero CPU overhead
- **Stateless design**: Fresh scan on every startup, no database
- **Fixed epoch timetable**: Movie schedule is deterministic across restarts
- **External subtitle support**: Auto-detects and embeds `.srt`, `.sub`, `.idx`, `.vtt`
- **Language filtering**: Prefers English audio streams when available
- **Kodi optimized**: M3U playlist with `inputstream.ffmpegdirect`
- **EPG support**: XMLTV format with 7-day program guide

## How It Works

1. On startup, scans your movie folder for `.mp4` and `.mkv` files
2. Extracts metadata using `ffprobe` (duration, codecs, audio streams)
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
# Set your movie folder path
```

### Configuration

Edit `config/config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8555

media:
  folder: "/path/to/movies"  # ← Change this!
  prefer_english: true

timetable:
  epoch: 1704067200  # Fixed reference time (Unix timestamp)
```

### Running

```bash
# From project root
python -m mtv

# Or using the installed command
mtv
```

### Kodi Setup

1. Open Kodi → TV → Add Channel
2. Enter M3U URL: `http://YOUR_IP:8555/m3u`
3. Enter EPG URL: `http://YOUR_IP:8555/epg.xml`
4. Done!

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/m3u` | M3U playlist for Kodi |
| `/epg` or `/epg.xml` | XMLTV EPG data (7 days) |
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
- Changing the `epoch` value shifts the entire schedule

### Example

If your playlist is 10 hours total and the epoch was January 1, 2024:
- At exactly 10 hours after epoch → Movie #1 starts
- At 15 hours after epoch → Movie #2 at 50%
- At 20 hours after epoch → Back to Movie #1 (cycle 2)

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
│   ├── server/
│   │   ├── handlers.py      # HTTP request handlers
│   │   └── streamer.py      # FFmpeg process manager
│   ├── api/
│   │   ├── playlist.py      # M3U generation
│   │   └── epg.py           # XMLTV generation
│   └── utils/
│       ├── ffprobe.py       # FFprobe wrapper
│       └── ffmpeg.py        # FFmpeg command builder
├── tests/                   # Unit tests
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

Edit `/opt/mtv/config/config.yaml` with your movie folder path.

### 4. Create Systemd Service

```bash
sudo tee /etc/systemd/system/mtv.service << 'EOF'
[Unit]
Description=Marko TV Streaming Server
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

### Subtitles not showing

- Ensure subtitle file has same basename as movie
- Supported formats: `.srt`, `.sub`, `.idx`, `.vtt`
- Example: `movie.mkv` → `movie.srt`

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

## License

MIT

## Acknowledgments

- Inspired by ErsatzTV but simplified for RPi 4
- Uses FFmpeg for streaming
- Kodi's `inputstream.ffmpegdirect` for direct MKV playback

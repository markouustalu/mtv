# MTV Docker Deployment Guide

This guide explains how to run MTV in a Docker container.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+ (optional but recommended)
- FFmpeg installed on host (not required inside container)

## Quick Start

### 1. Configure

Edit `docker-compose.yml` and update the movie path:

```yaml
volumes:
  - /path/to/your/movies:/movies:ro  # Change this!
```

### 2. Build and Run

```bash
# Using Docker Compose (recommended)
docker compose up -d --build

# Using Docker directly
docker build -t mtv .
docker run -d \
  --name mtv \
  -p 8555:8555 \
  -v /path/to/your/movies:/movies:ro \
  -e MTV_MEDIA_FOLDER=/movies \
  mtv
```

### 3. Access

- **M3U Playlist**: `http://your-server-ip:8555/m3u`
- **EPG**: `http://your-server-ip:8555/epg`
- **Health Check**: `http://your-server-ip:8555/health`

### 4. View Logs

```bash
# Docker Compose
docker compose logs -f

# Docker
docker logs -f mtv
```

## Configuration

### Option 1: Environment Variables

Add to `docker-compose.yml`:

```yaml
environment:
  - MTV_SERVER_HOST=0.0.0.0
  - MTV_SERVER_PORT=8555
  - MTV_MEDIA_FOLDER=/movies
  - MTV_PREFER_ENGLISH=true
  - MTV_LOG_LEVEL=INFO
  - MTV_STREAMING_TIMEOUT=300
  - MTV_TIMETABLE_EPOCH=1704067200
```

### Option 2: Custom config.yaml

Mount a custom configuration file:

```yaml
volumes:
  - ./config/custom.yaml:/app/config/config.yaml:ro
```

## Production Tips

### 1. Update advertised_host

In your `config/config.yaml` or via environment variable, set the LAN IP:

```yaml
server:
  advertised_host: "192.168.1.100"  # Your server's LAN IP
```

Or:

```bash
docker run -e MTV_SERVER_ADVERTISED_HOST=192.168.1.100 ...
```

### 2. Resource Limits

Adjust in `docker-compose.yml` based on your hardware:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Max CPU cores
      memory: 4G       # Max RAM
```

### 3. Persist Logs

Logs are stored in `./logs/mtv.log` inside the container. Mount the logs directory:

```yaml
volumes:
  - ./logs:/app/logs
```

### 4. Auto-update

```bash
# Pull latest and rebuild
docker compose pull
docker compose down
docker compose up -d --build
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs mtv

# Common issues:
# 1. Movie folder path is wrong or not accessible
# 2. FFmpeg not found (should be in container)
# 3. Port 8555 already in use
```

### No movies found

- Ensure the movie folder path is correct
- Check that movies have `.mp4` or `.mkv` extension
- Verify the volume is mounted with `:ro` (read-only)

### Stream errors

- Check container logs: `docker compose logs -f`
- Verify FFmpeg is working: `docker exec mtv ffmpeg -version`
- Ensure network connectivity to the container

## Network Modes

### Bridge (default)

```yaml
network_mode: bridge
```

### Host (better performance, exposes host ports)

```yaml
network_mode: host
```

Note: When using host mode, don't map ports.

## Security

- Container runs as non-root user (UID 1000)
- Movie folder mounted read-only (`:ro`)
- No sensitive data stored in container
- Health checks enabled for monitoring

## Example: Full Production Setup

```yaml
version: '3.8'

services:
  mtv:
    image: mtv:latest
    container_name: mtv
    restart: always
    network_mode: host
    volumes:
      - /mnt/media/movies:/movies:ro
      - ./logs:/app/logs
    environment:
      - MTV_MEDIA_FOLDER=/movies
      - MTV_SERVER_ADVERTISED_HOST=192.168.1.100
      - MTV_LOG_LEVEL=INFO
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

## Kodi Configuration

1. Open Kodi → Add-ons → Installer → Video add-ons → PVR IPTV Simple Client
2. Go to Settings → General → Set path to M3U play list
3. Enter: `http://your-server-ip:8555/m3u`
4. Enable M3U Extended Info
5. Go to Settings → EPG → Set path to EPG
6. Enter: `http://your-server-ip:8555/epg`
7. Save and restart

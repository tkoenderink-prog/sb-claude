# Docker Deployment Guide

Complete guide for deploying Second Brain with Docker.

**Last Updated:** 2025-12-23  
**Docker Compose Version:** 3.8  
**Status:** Production Ready

---

## Quick Start

```bash
# 1. Configure environment
cp .env.docker .env
# Edit .env with your values

# 2. Build images
./scripts/docker-build.sh

# 3. Start services
./scripts/docker-start.sh

# 4. Visit http://localhost:3000
```

---

## Prerequisites

- **Docker:** 20.10+ with Compose V2
- **Resources:** 4GB RAM minimum, 8GB recommended
- **Disk Space:** 10GB for images + data
- **Obsidian Vault:** Accessible path (not in iCloud!)

---

## Architecture

### Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| **frontend** | Node 20 Alpine | 3000 | Next.js UI |
| **backend** | Python 3.11 Slim | 8000 | FastAPI Runtime |
| **postgres** | Postgres 16 | 5432 | Database |
| **chromadb** | ChromaDB Latest | 8001 | Vector Store |

### Volumes

| Volume | Purpose | Persistence |
|--------|---------|-------------|
| `postgres_data` | Database | Critical - backup required |
| `chroma_data` | Vector embeddings | Regenerable |
| `backend_data` | Logs, secrets | Important |
| **Vault Mount** | Obsidian files | **Read-write (CRITICAL!)** |

---

## Configuration

### Environment Variables

Copy `.env.docker` to `.env` and configure:

```bash
# ===== Required =====

# Obsidian vault path (ABSOLUTE path, NOT iCloud!)
OBSIDIAN_VAULT_PATH=/Users/yourname/Documents/ObsidianVault

# Anthropic API key
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Database credentials
POSTGRES_USER=secondbrain
POSTGRES_PASSWORD=change-this-in-production
POSTGRES_DB=second_brain

# User permissions (run: id -u && id -g)
USER_ID=1000
GROUP_ID=1000

# Encryption key (generate with command below)
API_KEY_ENCRYPTION_KEY=your-fernet-key-here

# ===== Optional =====

# Multi-vendor AI
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=...

# Calendar sync
CALENDAR_WORK_URL=https://...
CALENDAR_PRIVATE_URL=https://...
```

### Generate Encryption Key

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Get Your User/Group ID

```bash
id -u  # USER_ID
id -g  # GROUP_ID
```

**Why?** Docker container runs as this UID/GID so files it creates match your user ownership.

---

## Critical: Vault Mount Configuration

### ❌ WRONG (Read-Only)

```yaml
volumes:
  - "${OBSIDIAN_VAULT_PATH}:/vault:ro"  # Proposals won't work!
```

### ✅ CORRECT (Read-Write)

```yaml
volumes:
  - "${OBSIDIAN_VAULT_PATH}:/vault"  # Proposals work!
```

**Why Read-Write?**
- Proposals need to write to vault
- Git auto-commit needs write access
- Application-level safety protects against bad writes
- Vault should be in git for backup

**Safety Layers:**
1. Write mode requires user approval (unless YOLO mode)
2. Path sandboxing prevents writes outside vault
3. Git auto-commit creates checkpoints before/after edits
4. Backups stored in `backend_data` volume

---

## Deployment Steps

### 1. Build Images

```bash
./scripts/docker-build.sh
```

This builds:
- Backend: Python 3.11 with uv, git, ripgrep
- Frontend: Next.js production build
- Multi-stage builds for optimal size

**Build args:**
- `USER_ID` - Matches host user
- `GROUP_ID` - Matches host group

### 2. Start Services

```bash
./scripts/docker-start.sh
```

**Startup sequence:**
1. PostgreSQL starts, runs health checks
2. ChromaDB starts
3. Backend waits for PostgreSQL healthy
4. Frontend waits for backend
5. All services report ready (~30 seconds)

### 3. Verify Deployment

```bash
# Check all services running
docker-compose ps

# Check logs
./scripts/docker-logs.sh

# Health check
curl http://localhost:8000/health

# Visit frontend
open http://localhost:3000
```

Expected health response:
```json
{
  "status": "healthy",
  "database": "connected",
  "vault": "accessible",
  "sessions_24h": 0
}
```

---

## Management

### View Logs

```bash
# All services
./scripts/docker-logs.sh

# Specific service
./scripts/docker-logs.sh backend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Stop Services

```bash
./scripts/docker-stop.sh

# Or manually
docker-compose down
```

### Restart Services

```bash
docker-compose restart backend
docker-compose restart frontend
```

### Update Code

```bash
# Pull latest code
git pull

# Rebuild and restart
./scripts/docker-build.sh
docker-compose down
docker-compose up -d
```

---

## Backup & Restore

### Database Backup

```bash
# Backup
docker-compose exec -T postgres pg_dump -U secondbrain second_brain | gzip > backup-$(date +%Y%m%d).sql.gz

# Restore
gunzip -c backup-20251223.sql.gz | docker-compose exec -T postgres psql -U secondbrain second_brain
```

### Vector Store Backup

```bash
# Backup
docker-compose exec chromadb tar czf - /chroma/chroma > chroma-backup.tar.gz

# Restore
docker-compose down
docker volume rm second-brain-app_chroma_data
docker-compose up -d chromadb
# Re-run vector indexing
```

### Full Backup Script

```bash
#!/bin/bash
BACKUP_DIR="$HOME/backups/second-brain"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"

# Database
docker-compose exec -T postgres pg_dump -U secondbrain second_brain | gzip > "$BACKUP_DIR/db-$DATE.sql.gz"

# ChromaDB
docker-compose exec chromadb tar czf - /chroma/chroma > "$BACKUP_DIR/chroma-$DATE.tar.gz"

# Keep last 7 days
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

echo "Backup complete: $BACKUP_DIR"
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Reset database
docker-compose down -v  # ⚠️ Deletes data!
docker-compose up -d
```

### Vault Not Accessible

**Symptom:** Backend logs show "Vault not found"

**Solutions:**
1. Check OBSIDIAN_VAULT_PATH in .env (use absolute path)
2. Ensure vault is NOT in iCloud (symlinks don't work)
3. Check Docker file sharing settings (macOS: Docker → Settings → Resources → File Sharing)
4. Verify permissions: `ls -la "$OBSIDIAN_VAULT_PATH"`

### Proposals Fail to Apply

**Symptom:** "Permission denied" when applying proposals

**Solution:** Vault must be mounted read-write (not `:ro`)

```yaml
# Check docker-compose.yml
volumes:
  - "${OBSIDIAN_VAULT_PATH}:/vault"  # ✅ Correct (no :ro)
```

### File Ownership Issues

**Symptom:** Files created by Docker owned by root

**Solution:** Set USER_ID and GROUP_ID in .env

```bash
# Get your IDs
id -u  # e.g., 1000
id -g  # e.g., 1000

# Update .env
USER_ID=1000
GROUP_ID=1000

# Rebuild
./scripts/docker-build.sh
docker-compose up -d
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase Docker memory (macOS)
# Docker → Settings → Resources → Memory: 8GB

# Or reduce service memory
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

---

## Production Deployment

### Security Checklist

- [ ] Change default passwords in .env
- [ ] Generate new API_KEY_ENCRYPTION_KEY
- [ ] Enable firewall (block ports 5432, 8001)
- [ ] Use HTTPS (reverse proxy with nginx/caddy)
- [ ] Set up Tailscale for remote access (not port forwarding)
- [ ] Enable Docker logging limits
- [ ] Regular backups automated
- [ ] Monitor disk space

### HTTPS with Caddy

```bash
# Install Caddy
brew install caddy  # macOS
sudo apt install caddy  # Linux

# Create Caddyfile
cat > Caddyfile << 'EOF'
secondbrain.yourdomain.com {
    reverse_proxy localhost:3000
}
EOF

# Start Caddy
sudo caddy start
```

### Systemd Service (Linux)

```bash
# Create service file
sudo tee /etc/systemd/system/second-brain.service << 'EOF'
[Unit]
Description=Second Brain App
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/second-brain-app
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=user

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable second-brain
sudo systemctl start second-brain
```

---

## Monitoring

### Resource Usage

```bash
# Real-time stats
docker stats

# Disk usage
docker system df
docker volume ls
```

### Health Checks

```bash
# All services
docker-compose ps

# Backend health
curl http://localhost:8000/health

# Check logs for errors
docker-compose logs --tail=100 | grep ERROR
```

### Uptime Monitoring

Use Uptime Kuma or similar:

```bash
docker run -d \
  --name=uptime-kuma \
  -p 3001:3001 \
  -v uptime-kuma:/app/data \
  louislam/uptime-kuma:1
```

---

## Performance Tuning

### PostgreSQL

```bash
# Edit postgresql.conf
docker-compose exec postgres nano /var/lib/postgresql/data/postgresql.conf

# Recommended settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 128MB
```

### Next.js

```javascript
// next.config.ts
export default {
  compress: true,
  poweredByHeader: false,
  generateEtags: true,
}
```

### Backend

```python
# Increase worker processes (main.py)
uvicorn.run(app, host="0.0.0.0", port=8000, workers=2)
```

---

## FAQ

**Q: Can I use Docker on Windows?**  
A: Yes, but WSL2 required. Vault path: `/mnt/c/Users/.../vault`

**Q: How much does it cost to run?**  
A: $0 infrastructure (local), ~$5-20/month for Anthropic API usage

**Q: Can I deploy to a VPS?**  
A: Yes! Use same Docker setup, add HTTPS, firewall, monitoring

**Q: What about ARM (M1/M2 Mac)?**  
A: Fully supported. Images are multi-arch.

**Q: How do I migrate from local dev?**  
A: Export database, copy vault, update .env paths, import database

---

## Support

- **Issues:** https://github.com/anthropics/claude-code/issues
- **Logs:** `./scripts/docker-logs.sh`
- **Health Check:** `curl http://localhost:8000/health`

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-23  
**Tested With:** Docker 24.0, Compose 2.23

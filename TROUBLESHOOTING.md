# Troubleshooting Guide

Common issues and solutions for the GodMode Quant Orchestrator.

## Table of Contents

- [Port Already in Use](#port-already-in-use)
- [Docker Compose Build Failures](#docker-compose-build-failures)
- [PostgreSQL Connection Issues](#postgresql-connection-issues)
- [Redis Connection Issues](#redis-connection-issues)
- [Telegram Bot Not Responding](#telegram-bot-not-responding)
- [Authentication Failed](#authentication-failed)
- [PyTorch Import Errors](#pytorch-import-errors)
- [Kubernetes Deployment Issues](#kubernetes-deployment-issues)
- [General Debugging Tips](#general-debugging-tips)

---

## Port Already in Use

### Symptoms
- `docker-compose up` fails with `Bind for 0.0.0.0:8003 failed: port is already allocated`
- `Error starting userland proxy: listen tcp 0.0.0.0:8003: bind: address already in use`

### Solutions

1. **Check what's using the port:**
   ```bash
   # Linux/Mac
   sudo lsof -i :8003
   # or
   sudo netstat -tlnp | grep 8003
   
   # Windows (PowerShell)
   netstat -ano | findstr :8003
   ```

2. **Stop the conflicting process:**
   ```bash
   # Find PID and kill (Linux/Mac)
   kill -9 <PID>
   
   # Or stop Docker containers using the port
   docker-compose down
   ```

3. **Change the host port mapping:**
   Edit `docker-compose.yml`:
   ```yaml
   services:
     trading-orchestrator:
       ports:
         - "8004:8003"  # Change 8003 to any available port
   ```
   Then access via `http://localhost:8004`.

4. **Check for orphaned containers:**
   ```bash
   docker ps -a | grep godmode
   docker rm -f <container_id>
   ```

---

## Docker Compose Build Failures

### Symptoms
- `docker-compose build` fails with dependency errors
- `pip install` fails during build
- Missing system libraries

### Solutions

1. **Clear Docker cache and rebuild:**
   ```bash
   docker-compose down -v
   docker system prune -f
   docker-compose build --no-cache
   ```

2. **Check Python version compatibility:**
   Ensure your `requirements.txt` matches Python 3.9+.

3. **Install system dependencies manually:**
   If build fails on system packages, check `Dockerfile` for required packages.

4. **Network issues during pip install:**
   ```bash
   # Add to Dockerfile before pip install:
   RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
   ```

5. **Check Docker daemon resources:**
   - Ensure Docker has enough memory (2GB+)
   - Check disk space: `docker system df`

---

## PostgreSQL Connection Issues

### Symptoms
- `could not connect to server: Connection refused`
- `FATAL: password authentication failed`
- `database "vnpy" does not exist`

### Solutions

1. **Check PostgreSQL container status:**
   ```bash
   docker-compose ps postgres
   docker-compose logs postgres
   ```

2. **Verify environment variables:**
   Ensure `.env` matches `docker-compose.yml`:
   ```bash
   grep POSTGRES .env
   ```

3. **Reset PostgreSQL data:**
   ```bash
   docker-compose down -v
   docker volume rm godmode-quant-orchestrator_postgres_data
   docker-compose up -d postgres
   ```

4. **Manual connection test:**
   ```bash
   docker-compose exec postgres psql -U postgres -d vnpy
   ```

5. **Check port mapping:**
   PostgreSQL maps to host port 5433. Connect via:
   ```bash
   psql -h localhost -p 5433 -U postgres -d vnpy
   ```

---

## Redis Connection Issues

### Symptoms
- `redis.exceptions.ConnectionError: Error 111 connecting to redis:6379`
- `MISCONF Redis is configured to save RDB snapshots`

### Solutions

1. **Check Redis container:**
   ```bash
   docker-compose ps redis
   docker-compose logs redis
   ```

2. **Test Redis connection:**
   ```bash
   docker-compose exec redis redis-cli -a your_redis_password ping
   # Should return "PONG"
   ```

3. **Check Redis password:**
   Ensure `REDIS_PASSWORD` in `.env` matches `docker-compose.yml`.

4. **Clear Redis data:**
   ```bash
   docker-compose down -v
   docker volume rm godmode-quant-orchestrator_redis_data
   docker-compose up -d redis
   ```

5. **Memory issues:**
   If Redis crashes due to memory, add to `docker-compose.yml`:
   ```yaml
   redis:
     command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
   ```

---

## Telegram Bot Not Responding

### Symptoms
- No startup message in Telegram
- Bot commands don't work
- `TelegramError: Unauthorized`

### Solutions

1. **Verify bot token:**
   - Get token from @BotFather
   - Ensure no extra spaces in `.env`
   ```bash
   echo $TELEGRAM_BOT_TOKEN | wc -c  # Should be ~35+ characters
   ```

2. **Check chat ID:**
   - Get your chat ID from @userinfobot
   - Ensure bot is started in that chat

3. **Test bot token directly:**
   ```bash
   curl -X GET "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
   ```

4. **Check webhook vs polling:**
   The system uses polling. Ensure no webhook is set:
   ```bash
   curl -X GET "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"
   ```

5. **Check logs:**
   ```bash
   docker-compose logs trading-orchestrator | grep -i telegram
   ```

6. **Firewall/proxy issues:**
   Ensure outbound HTTPS to `api.telegram.org` is allowed.

---

## Authentication Failed

### Symptoms
- `401 Unauthorized` on API endpoints
- `Invalid credentials` error

### Solutions

1. **Check API credentials:**
   ```bash
   echo $API_USERNAME
   echo $API_PASSWORD
   ```

2. **Test with curl:**
   ```bash
   curl -u admin:password http://localhost:8003/health
   ```

3. **Check authentication is enabled:**
   ```bash
   echo $AUTH_ENABLED  # Should be "true"
   ```

4. **Password hashing:**
   The system uses `werkzeug.security.generate_password_hash`. Ensure your password matches.

5. **Reset credentials:**
   Update `.env` and restart:
   ```bash
   docker-compose restart trading-orchestrator
   ```

6. **Check rate limiting:**
   If you exceed rate limits, you may get 401. Wait and retry.

---

## PyTorch Import Errors

### Symptoms
- `ModuleNotFoundError: No module named 'torch'`
- `ImportError: libcudnn.so.8: cannot open shared object file`
- `TensorFlow/PyTorch conflicts`

### Solutions

1. **Install PyTorch correctly:**
   For CPU-only:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
   ```

   For CUDA 11.8:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Use ML Dockerfile:**
   Build with ML support:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.ml.yml up -d
   ```

3. **Check Python version:**
   PyTorch requires Python 3.8-3.11.

4. **Virtual environment conflicts:**
   ```bash
   deactivate  # Exit any active venv
   pip uninstall torch tensorflow -y
   pip install torch torchvision torchaudio
   ```

5. **Docker memory issues:**
   ML models require 2GB+ memory. Increase Docker memory limit.

---

## Kubernetes Deployment Issues

### Symptoms
- Pods in `CrashLoopBackOff`
- `ImagePullBackOff`
- Service not accessible

### Solutions

1. **Check pod status:**
   ```bash
   kubectl get pods -n quant-trading
   kubectl describe pod <pod-name> -n quant-trading
   ```

2. **Check logs:**
   ```bash
   kubectl logs -f deployment/god-mode-orchestrator -n quant-trading
   ```

3. **Image pull issues:**
   - Ensure image exists in registry
   - Check image pull secrets:
     ```bash
     kubectl get secrets -n quant-trading
     ```

4. **Secrets configuration:**
   Ensure `god-mode-secrets` secret exists:
   ```bash
   kubectl get secret god-mode-secrets -n quant-trading -o yaml
   ```

5. **Port mapping mismatch:**
   Check `k8s/service.yaml` ports:
   ```yaml
   ports:
     - port: 8003
       targetPort: 8003
   ```

6. **Resource limits:**
   Increase memory/CPU limits in `k8s/deployment.yaml`:
   ```yaml
   resources:
     limits:
       memory: "2Gi"
       cpu: "1000m"
   ```

7. **Health check failures:**
   Ensure health endpoint responds:
   ```bash
   kubectl exec -it <pod-name> -n quant-trading -- curl localhost:8003/health
   ```

---

## General Debugging Tips

1. **Enable debug logging:**
   ```bash
   # In .env
   LOG_LEVEL=DEBUG
   SECURITY_LOG_LEVEL=DEBUG
   ```

2. **Check all logs at once:**
   ```bash
   docker-compose logs -f --tail=100
   ```

3. **Enter container shell:**
   ```bash
   docker-compose exec trading-orchestrator bash
   ```

4. **Test network connectivity:**
   ```bash
   docker-compose exec trading-orchestrator ping postgres
   docker-compose exec trading-orchestrator ping redis
   ```

5. **Verify environment variables:**
   ```bash
   docker-compose exec trading-orchestrator env | grep -E "POSTGRES|REDIS|TELEGRAM"
   ```

6. **Check file permissions:**
   ```bash
   ls -la .env  # Should be readable by container user
   ```

7. **Monitor resource usage:**
   ```bash
   docker stats
   ```

8. **Reset everything:**
   ```bash
   docker-compose down -v
   docker system prune -f
   docker-compose up -d
   ```

---

## Still Need Help?

1. **Check existing issues:** [GitHub Issues](https://github.com/NkhekheRepository/god-mode-quant-orchestrator/issues)
2. **Create new issue:** Include:
   - Error message
   - Steps to reproduce
   - Environment details (OS, Docker version)
   - Log snippets
3. **Join discussion:** [Telegram Community](https://t.me/godmode_quant)

---

**Last Updated:** March 28, 2026  
**Version:** 2.0.0
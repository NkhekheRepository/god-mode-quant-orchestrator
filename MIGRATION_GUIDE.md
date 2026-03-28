# Migration Guide: v2.0.0 &rarr; v2.1.0

This guide helps you migrate from GodMode Quant Orchestrator v2.0.0 to v2.1.0 with JWT authentication and enhanced security.

## Table of Contents

- [Overview](#overview)
- [Breaking Changes](#breaking-changes)
- [Prerequisites](#prerequisites)
- [Migration Process](#migration-process)
- [Authentication Changes](#authentication-changes)
- [API Changes](#api-changes)
- [Configuration Changes](#configuration-changes)
- [Data Migration](#data-migration)
- [Rollback Procedure](#rollback-procedure)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

## Overview

### What's New in v2.1.0

- **JWT Authentication**: Replaces HTTP Basic Auth with OAuth2/JWT tokens
- **Role-Based Access Control (RBAC)**: Admin, trader, viewer, auditor roles
- **Enhanced Security**: SQL injection protection, input validation, security logging
- **FasterAPI Migration**: Migrated from Flask to FastAPI for better performance
- **Improved Monitoring**: Enhanced Prometheus metrics and structured logging
- **Database Security**: Secure database manager with parameterized queries

### Migration Impact

- **API Changes**: Endpoints now require JWT tokens instead of Basic Auth
- **Authentication Flow**: New login endpoint required to obtain access tokens
- **Configuration**: New environment variables for JWT settings
- **Dependencies**: New packages required for FastAPI and JWT handling
- **Database**: Optional - automatic schema migration on startup

## Breaking Changes

### Authentication

| v2.0.0 | v2.1.0 | Action Required |
|--------|--------|-----------------|
| HTTP Basic Auth | JWT OAuth2 | Update all API calls to use JWT tokens |
| Single admin user | Multiple users with roles | Create additional users as needed |
| Static passwords | Token-based auth with refresh | Implement token refresh logic |
| `Authorization: Basic base64(user:pass)` | `Authorization: Bearer <token>` | Update authorization headers |

### API Endpoints

| Endpoint (v2.0.0) | Endpoint (v2.1.0) | Changes |
|-------------------|-------------------|---------|
| POST /api/submit_order | POST /api/orders | Renamed and enhanced |
| GET / (health) | GET /health | Restructured response format |
| Same endpoint paths | Same endpoint paths | All now require JWT tokens |

### Configuration

| Variable (v2.0.0) | Variable (v2.1.0) | Changes |
|-------------------|-------------------|---------|
| API_USERNAME | API_USERNAME | Same name but new purpose |
| API_PASSWORD | API_PASSWORD | Same name but new purpose |
| - | JWT_SECRET_KEY | New: JWT signing key |
| - | ACCESS_TOKEN_EXPIRE_MINUTES | New: Token lifetime |
| - | REFRESH_TOKEN_EXPIRE_DAYS | New: Refresh token lifetime |

## Prerequisites

Before migrating, ensure you have:

1. **Backup your data**
   ```bash
   # Backup SQLite database
   cp trading_db.sqlite trading_db.sqlite.backup
   ```

2. **Backup configuration**
   ```bash
   # Backup .env file
   cp .env .env.backup
   ```

3. **Check system compatibility**
   - Python 3.9 or higher
   - Sufficient disk space for new dependencies (~500MB)
   - Network access for dependency installation

4. **Review application status**
   ```bash
   # Check running services
   docker-compose ps
   ```

## Migration Process

### Step 1: Prepare the Environment

1. Stop the current application:
   ```bash
   docker-compose down
   ```

2. Create migration branch (for rollback safety):
   ```bash
   git checkout -b migration-v2.1.0
   ```

### Step 2: Update Dependencies

1. Update requirements.txt:
   ```bash
   # Install updated requirements
   pip install -r requirements.txt --upgrade
   ```

2. Verify new packages:
   ```bash
   # Check critical new packages
   pip list | grep -E "fastapi|uvicorn|python-jose|passlib|slowapi"
   ```

### Step 3: Update Configuration

1. Generate secure JWT secret key:
   ```bash
   # Generate a random 256-bit key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. Add to .env file:
   ```bash
   # JWT Configuration
   JWT_SECRET_KEY=<your-generated-key-here>
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   REFRESH_TOKEN_EXPIRE_DAYS=30

   # API Configuration
   API_PORT=8000
   API_HOST=0.0.0.0
   API_WORKERS=1

   # CORS Configuration
   CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.com
   ```

3. Update existing authentication:
   ```bash
   # Update or verify admin credentials
   API_USERNAME=admin
   API_PASSWORD=<strong_password_with_at_least_12_characters>
   ```

### Step 4: Database Migration

The database manager will automatically handle schema updates:

1. Review database changes:
   - New tables: `trades`, `positions`, `system_logs`
   - Enhanced indexing for performance
   - Automatic migration on first startup

2. Manual check (optional):
   ```bash
   python -c "from database.database_manager import db_manager; db_manager._setup_db()"
   ```

### Step 5: Test Authentication

1. Start the application:
   ```bash
   docker-compose up -d
   ```

2. Test health endpoint (no auth required):
   ```bash
   curl http://localhost:8000/health
   ```

3. Test login endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/auth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=<your_password>"
   ```

4. Save the access token for subsequent requests.

### Step 6: Update API Clients

**In Python:**

```python
# v2.0.0: Basic Auth
headers = {'Authorization': f'Basic {base64_credentials}'}

# v2.1.0: JWT Token
import requests
from requests.auth import HTTPBasicAuth

# First, get token
response = requests.post(
    'http://localhost:8000/api/auth/token',
    data={'username': 'admin', 'password': 'your_password'}
)
token = response.json()['access_token']

# Use token for requests
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8000/api/orders', headers=headers)
```

**In JavaScript:**

```javascript
// v2.0.0: Basic Auth
const headers = {
  'Authorization': `Basic ${base64UsernamePassword}`
};

// v2.1.0: JWT Token
async function getToken(username, password) {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);
  
  const response = await fetch('http://localhost:8000/api/auth/token', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: params
  });
  return await response.json();
}

// Use token
const tokenData = await getToken('admin', 'your_password');
const headers = {'Authorization': `Bearer ${tokenData.access_token}`};
```

**Using curl:**

```bash
# v2.0.0
curl -u admin:password http://localhost:8000/api/orders

# v2.1.0
# First get token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password" | jq -r '.access_token')

# Use token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/orders
```

### Step 7: Verify Migration

1. Test protected endpoints:
   ```bash
   # Get orders (requires auth)
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/orders
   
   # Create order (requires trader role)
   curl -X POST http://localhost:8000/api/orders \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"symbol":"BTCUSDT","side":"buy","quantity":0.01,"order_type":"LIMIT"}'
   ```

2. Check metrics:
   ```bash
   curl http://localhost:8000/metrics
   ```

3. Review logs:
   ```bash
   docker-compose logs -f api
   ```

### Step 8: Update Deployment

1. Update Docker Compose (if using):

   **v2.0.0 docker-compose.yml:**
   ```yaml
   services:
     trading-orchestrator:
       image: godmode-quant:v2.0.0
       command: python main.py
   ```

   **v2.1.0 docker-compose.yml:**
   ```yaml
   services:
     api:
       image: godmode-quant:v2.1.0
       command: python main_fastapi.py
       environment:
         - JWT_SECRET_KEY=${JWT_SECRET_KEY}
         - API_PORT=8000
       ports:
         - "8000:8000"
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
   ```

2. Update Kubernetes manifests (if using):

   **v2.1.0 deployment changes:**
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: godmode-quant-api
   spec:
     template:
       spec:
         containers:
         - name: api
           image: godmode-quant:v2.1.0
           env:
           - name: JWT_SECRET_KEY
             valueFrom:
               secretKeyRef:
                 name: jwt-secret
                 key: secret-key
           - name: API_PORT
             value: "8000"
           ports:
           - containerPort: 8000
           livenessProbe:
             httpGet:
               path: /health/live
               port: 8000
           readinessProbe:
             httpGet:
               path: /health/ready
               port: 8000
   ```

## Authentication Changes

### Login Flow

**New login process:**

1. **Get tokens:**
   ```bash
   POST /api/auth/token
   Content-Type: application/x-www-form-urlencoded
   
   username=admin&password=your_password
   
   Response:
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "expires_in": 86400,
     "refresh_token": "another_token..."
   }
   ```

2. **Use access token:**
   ```bash
   GET /api/orders
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. **Refresh token when expired:**
   ```bash
   POST /api/auth/refresh
   Content-Type: application/json
   
   {"refresh_token": "another_token..."}
   
   Response:
   {
     "access_token": "new_access_token...",
     "token_type": "bearer",
     "expires_in": 86400,
     "refresh_token": "new_refresh_token..."
   }
   ```

### Roles and Permissions

| Role | Permissions |
|------|-------------|
| **admin** | Full access to all operations |
| **trader** | Read/write trades, view positions, execute orders |
| **viewer** | Read-only access to trades and positions |
| **auditor** | Access to logs and audit information |

### User Management

**Default users:**

| Username | Password (change immediately) | Roles |
|----------|------------------------------|-------|
| admin | Your password from .env | admin, trader |
| trader1 | Set in TRADER_PASSWORD env var | trader |
| auditor | Set in AUDITOR_PASSWORD env var | auditor |

**To add new users:**

```python
import bcrypt
from database.database_manager import db_manager

# Hash password
password_hash = bcrypt.hashpw("new_password".encode(), bcrypt.gensalt())

# Store in database (example)
user_data = {
    "username": "new_trader",
    "email": "new_trader@example.com",
    "full_name": "New Trader",
    "roles": ["trader"],
    "hashed_password": password_hash.decode()
}
```

## API Changes

### Endpoint Protection

All endpoints except the following now require JWT authentication:

- `/health` - Health check (rate limited)
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe
- `/metrics` - Prometheus metrics (rate limited)
- `/docs` - Swagger UI
- `/redoc` - ReDoc
- `/api/auth/token` - Login endpoint
- `/api/auth/refresh` - Refresh token endpoint

### Response Format Changes

**v2.0.0:**
```json
{
  "status": "success",
  "data": {...}
}
```

**v2.1.0:**
```json
{
  "timestamp": "2026-03-27T12:00:00.000Z",
  "status": "order_submitted",
  "order_id": "ORDER-1711550400",
  ...
}
```

### Pagination

Pagination now uses standard query parameters:

```
GET /api/orders?limit=20&offset=0
```

**Response:**
```json
{
  "orders": [...],
  "count": 100,
  "timestamp": "2026-03-27T12:00:00.000Z"
}
```

## Configuration Changes

### Environment Variables

**New variables:**

```bash
# JWT Configuration
JWT_SECRET_KEY=random_secure_key_minimum_32_characters_longs
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
API_WORKERS=1

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://your-domain.com

# User Passwords
ADMIN_PASSWORD=StrongAdminPass123
TRADER_PASSWORD=TradingPass456
AUDITOR_PASSWORD=AuditPass789
```

**Recommended .env updates:**

```bash
# Generate JWT secrets
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Set strong passwords
ADMIN_PASSWORD=$(openssl rand -base64 16)
TRADER_PASSWORD=$(openssl rand -base64 16)
AUDITOR_PASSWORD=$(openssl rand -base64 16)
```

### Docker Compose Configuration

**New health checks:**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## Data Migration

### Database Changes

**Automatic migration:**

1. **New tables** are created automatically on startup
2. **No data loss** - existing data is preserved
3. **No manual SQL required** - migration handled by code

**Database additions:**

```sql
-- Trades table (auto-created or enhanced)
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    quantity REAL NOT NULL,
    status TEXT NOT NULL,
    client_order_id TEXT,
    execution_report TEXT
);

-- Positions table (new)
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL,
    entry_price REAL NOT NULL,
    margin REAL,
    pnl REAL,
    status TEXT NOT NULL
);

-- System logs table (new)
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT
);
```

**Data preservation:**

All existing trades and configurations are preserved. If you have custom database migrations, they should be run after the automatic migration completes.

### Backup and Restore

**Backup before migration:**
```bash
# Database backup
cp trading_db.sqlite trading_db.sqlite.backup-$(date +%Y%m%d)

# Configuration backup
cp .env .env.backup-$(date +%Y%m%d)

# Logs backup
cp output.log output.log.backup-$(date +%Y%m%d)
```

**Restore if needed:**
```bash
# Stop application
docker-compose down

# Restore database
mv trading_db.sqlite.backup-$(date +%Y%m%d) trading_db.sqlite

# Restore configuration
mv .env.backup-$(date +%Y%m%d) .env

# Rollback code
git checkout main

# Restart
docker-compose up -d
```

## Rollback Procedure

If you need to rollback from v2.1.0 to v2.0.0:

1. **Stop the current application:**
   ```bash
   docker-compose down
   ```

2. **Restore the v2.0.0 code:**
   ```bash
   git checkout main
   # or
   git checkout tags/v2.0.0
   ```

3. **Restore configuration:**
   ```bash
   cp .env.backup .env
   ```

4. **Restore database:**
   ```bash
   cp trading_db.sqlite.backup trading_db.sqlite
   ```

5. **Restore dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Restart the application:**
   ```bash
   docker-compose up -d
   ```

7. **Verify functionality:**
   ```bash
   # Test with Basic Auth (v2.0.0)
   curl -u admin:password http://localhost:8000/health
   ```

## Troubleshooting

### Common Issues

#### Issue: "Invalid credentials" on login

**Solution:**
1. Verify username and password in .env
2. Check that `AUTH_ENABLED=true` in .env
3. Restart the application
4. Check logs: `docker-compose logs api | grep authentication`

#### Issue: "Token has expired"

**Solution:**
1. Use the refresh token to get a new access token
2. Or login again at `/api/auth/token`
3. Consider increasing `ACCESS_TOKEN_EXPIRE_MINUTES` if too short

#### Issue: Rate limit errors

**Solution:**
1. Reduce request frequency
2. Adjust rate limits in configuration
3. Check if multiple IPs are being counted separately

#### Issue: CORS errors in browser

**Solution:**
1. Add your frontend URL to `CORS_ORIGINS` in .env
2. Ensure `allow_origins` includes the correct origin
3. Check for typos in origin URLs

#### Issue: Database migration failures

**Solution:**
1. Check database file permissions
2. Ensure sufficient disk space
3. Review migration logs
4. Restore from backup if needed

#### Issue: Missing dependencies

**Solution:**
1. Clear pip cache:
   ```bash
   pip cache purge
   ```
2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

#### Issue: Module import errors

**Solution:**
1. Check Python version compatibility (3.9+)
2. Verify virtual environment is activated
3. Check for path conflicts:
   ```bash
   python -c "import sys; print(sys.path)"
   ```

### Performance Issues

#### Issue: Slow authentication responses

**Solution:**
1. Check database query performance
2. Review rate limit settings
3. Ensure no blocking I/O operations

#### Issue: High memory usage

**Solution:**
1. Monitor connection pool usage
2. Adjust worker count: `API_WORKERS` variable
3. Check for memory leaks in custom code

### Logging and Debugging

**Enable debug logging:**
```bash
# In .env
LOG_LEVEL=DEBUG
```

**View authentication events:**
```bash
docker-compose logs api | grep -E "auth|token|login"
```

**Check security logs:**
```bash
docker-compose logs api | grep security
```

## Support

### Documentation

- [CHANGELOG.md](./CHANGELOG.md) - Version history
- [README.md](./README.md) - Main documentation
- [SECURITY.md](./SECURITY.md) - Security configuration

### Reporting Issues

1. Check existing [GitHub Issues](https://github.com/NkhekheRepository/REAL-GOD-MODE-QUANT/issues)
2. Include version information: v2.1.0
3. Provide error logs
4. Describe the reproduction steps

### Professional Support

- Documentation: docs@godmode-quant.com
- Security issues: security@godmode-quant.com
- Enterprise support: enterprise@godmode-quant.com

### Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [JWT Authentication Guide](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [OWASP Security Guidelines](https://owasp.org/)

---

**Migration Last Updated**: March 27, 2026  
**Version**: 2.1.0  
**Status**: Production Ready  

For questions or assistance, please refer to the documentation or contact support.
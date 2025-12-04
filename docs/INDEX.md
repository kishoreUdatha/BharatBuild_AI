# BharatBuild AI Documentation Index

## Quick Links

| Document | Description |
|----------|-------------|
| [COMPLETE_DOCUMENTATION.md](./COMPLETE_DOCUMENTATION.md) | Full system overview and architecture |
| [CONTAINER_EXECUTION_GUIDE.md](./CONTAINER_EXECUTION_GUIDE.md) | Docker container execution system |
| [EPHEMERAL_STORAGE_GUIDE.md](./EPHEMERAL_STORAGE_GUIDE.md) | Job-based ephemeral storage |
| [API_REFERENCE.md](./API_REFERENCE.md) | Complete API documentation |
| [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) | Security implementation details |
| [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | Production deployment instructions |
| [SCALING_GUIDE.md](./SCALING_GUIDE.md) | Scaling from 100 to 100,000+ users |

---

## Documentation by Topic

### Getting Started

1. **[COMPLETE_DOCUMENTATION.md](./COMPLETE_DOCUMENTATION.md)** - Start here for system overview
2. **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Local development setup
3. **[API_REFERENCE.md](./API_REFERENCE.md)** - API endpoints

### Architecture

1. **[COMPLETE_DOCUMENTATION.md](./COMPLETE_DOCUMENTATION.md)** - High-level architecture
2. **[CONTAINER_EXECUTION_GUIDE.md](./CONTAINER_EXECUTION_GUIDE.md)** - Container architecture
3. **[EPHEMERAL_STORAGE_GUIDE.md](./EPHEMERAL_STORAGE_GUIDE.md)** - Storage architecture

### Development

1. **[API_REFERENCE.md](./API_REFERENCE.md)** - Full API documentation
2. **[CONTAINER_EXECUTION_GUIDE.md](./CONTAINER_EXECUTION_GUIDE.md)** - Container API usage
3. **[EPHEMERAL_STORAGE_GUIDE.md](./EPHEMERAL_STORAGE_GUIDE.md)** - Storage API usage

### Security

1. **[SECURITY_GUIDE.md](./SECURITY_GUIDE.md)** - Security implementation
2. **[CONTAINER_EXECUTION_GUIDE.md](./CONTAINER_EXECUTION_GUIDE.md)** - Container security

### Operations

1. **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Deployment instructions
2. **[SCALING_GUIDE.md](./SCALING_GUIDE.md)** - Scaling strategies
3. **[SECURITY_GUIDE.md](./SECURITY_GUIDE.md)** - Security monitoring

---

## Key Concepts

### Ephemeral Storage

Files are stored in `/tmp/jobs/<job_id>/` during generation:
- Zero cloud storage cost
- <1ms write latency
- Auto-cleanup after 48 hours

See: [EPHEMERAL_STORAGE_GUIDE.md](./EPHEMERAL_STORAGE_GUIDE.md)

### Container Execution

Each project runs in an isolated Docker container:
- Per-project isolation
- Resource limits (512MB RAM, 0.5 CPU)
- Real-time streaming via SSE
- Auto-cleanup after 24 hours

See: [CONTAINER_EXECUTION_GUIDE.md](./CONTAINER_EXECUTION_GUIDE.md)

### Security Layers

Multiple layers protect the system:
1. Command validation (blocklist + patterns)
2. Container isolation (Docker)
3. Resource limits (cgroups)
4. Path traversal prevention

See: [SECURITY_GUIDE.md](./SECURITY_GUIDE.md)

### Scaling Path

1. **Phase 1**: Docker Compose (100-500 users)
2. **Phase 2**: Fly.io/Railway (1,000-50,000 users)
3. **Phase 3**: Kubernetes (100,000+ users)

See: [SCALING_GUIDE.md](./SCALING_GUIDE.md)

---

## API Quick Reference

### Jobs API

```
POST /api/v1/jobs/create              Create job
POST /api/v1/jobs/{id}/files          Write file
POST /api/v1/jobs/{id}/complete       Create ZIP
GET  /api/v1/jobs/{id}/download       Download ZIP
```

### Containers API

```
POST /api/v1/containers/{id}/create   Create container
POST /api/v1/containers/{id}/exec     Execute command (SSE)
POST /api/v1/containers/{id}/files    Write file
GET  /api/v1/containers/{id}/preview  Get preview URL
```

Full reference: [API_REFERENCE.md](./API_REFERENCE.md)

---

## File Structure

```
docs/
├── INDEX.md                     # This file
├── COMPLETE_DOCUMENTATION.md    # Full system overview
├── CONTAINER_EXECUTION_GUIDE.md # Container execution
├── EPHEMERAL_STORAGE_GUIDE.md   # Job storage
├── API_REFERENCE.md             # API documentation
├── SECURITY_GUIDE.md            # Security implementation
├── DEPLOYMENT_GUIDE.md          # Deployment instructions
└── SCALING_GUIDE.md             # Scaling strategies
```

---

## Support

- **API Docs**: http://localhost:8000/docs (Swagger)
- **Issues**: GitHub Issues
- **Email**: support@bharatbuild.ai

---

**BharatBuild AI - Production-grade code generation for 1,00,000+ Indian students**

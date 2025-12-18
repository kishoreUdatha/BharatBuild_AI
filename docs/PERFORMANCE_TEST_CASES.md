# BharatBuild AI - Performance Test Cases

## Document Info
- **Version:** 1.0
- **Last Updated:** 2024-12-18
- **Tool:** k6, Artillery, or JMeter

---

## Table of Contents
1. [Test Environment](#1-test-environment)
2. [Load Test Scenarios](#2-load-test-scenarios)
3. [Stress Test Scenarios](#3-stress-test-scenarios)
4. [Endurance Test Scenarios](#4-endurance-test-scenarios)
5. [API Performance Benchmarks](#5-api-performance-benchmarks)
6. [Frontend Performance](#6-frontend-performance)
7. [Database Performance](#7-database-performance)
8. [AI/LLM Performance](#8-aillm-performance)

---

## 1. Test Environment

### Infrastructure Requirements
| Component | Specification |
|-----------|---------------|
| **Backend Server** | 4 vCPU, 8GB RAM |
| **Database** | PostgreSQL RDS (db.t3.medium) |
| **Redis** | ElastiCache (cache.t3.small) |
| **Load Generator** | Separate machine/container |

### Test Data
- 1,000 pre-created user accounts
- 500 pre-generated projects
- 2,000 generated documents

### Environment Variables
```bash
BASE_URL=https://staging.bharatbuild.ai
API_URL=https://staging.bharatbuild.ai/api/v1
TEST_DURATION=300  # 5 minutes
RAMP_UP_TIME=60    # 1 minute
```

---

## 2. Load Test Scenarios

### PERF-LOAD-001: Normal Load - Authentication
| Field | Value |
|-------|-------|
| **Objective** | Verify system handles normal authentication load |
| **Virtual Users** | 100 concurrent |
| **Duration** | 5 minutes |
| **Ramp-up** | 60 seconds |
| **Scenario** | Login → Get User → Logout |
| **Pass Criteria** | - 95th percentile < 500ms<br>- Error rate < 1%<br>- Throughput > 50 req/sec |

**k6 Script:**
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 100 },  // Ramp up
    { duration: '3m', target: 100 },  // Stay at 100
    { duration: '1m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  // Login
  const loginRes = http.post(`${__ENV.API_URL}/auth/login`, {
    username: `user_${__VU}@test.com`,
    password: 'TestPassword123!',
  });
  check(loginRes, { 'login status 200': (r) => r.status === 200 });

  const token = loginRes.json('access_token');

  // Get user
  const meRes = http.get(`${__ENV.API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  check(meRes, { 'me status 200': (r) => r.status === 200 });

  sleep(1);
}
```

### PERF-LOAD-002: Normal Load - Project List
| Field | Value |
|-------|-------|
| **Objective** | Verify project listing performance |
| **Virtual Users** | 200 concurrent |
| **Duration** | 5 minutes |
| **Scenario** | Login → List Projects → Get Project Details |
| **Pass Criteria** | - 95th percentile < 800ms<br>- Error rate < 1% |

### PERF-LOAD-003: Normal Load - Document Download
| Field | Value |
|-------|-------|
| **Objective** | Verify document download performance |
| **Virtual Users** | 50 concurrent |
| **Duration** | 5 minutes |
| **Scenario** | Login → List Documents → Download Document |
| **Pass Criteria** | - 95th percentile < 2000ms<br>- Error rate < 2% |

### PERF-LOAD-004: Mixed Workload
| Field | Value |
|-------|-------|
| **Objective** | Simulate real-world usage pattern |
| **Virtual Users** | 300 concurrent |
| **Duration** | 10 minutes |
| **Scenario Mix** | - 40% Browse projects<br>- 30% View files<br>- 20% Generate (light)<br>- 10% Download |
| **Pass Criteria** | - 95th percentile < 1000ms<br>- Error rate < 2% |

---

## 3. Stress Test Scenarios

### PERF-STRESS-001: Breaking Point Test
| Field | Value |
|-------|-------|
| **Objective** | Find system breaking point |
| **Virtual Users** | 50 → 1000 (step increase) |
| **Duration** | 15 minutes |
| **Scenario** | Gradually increase load until failure |
| **Measurements** | - Record breaking point VU count<br>- Response time degradation curve<br>- Error rate spike point |

**Expected Results:**
| VU Count | Expected Response Time | Expected Error Rate |
|----------|------------------------|---------------------|
| 100 | < 500ms | < 1% |
| 300 | < 1000ms | < 2% |
| 500 | < 2000ms | < 5% |
| 1000 | Degraded | > 10% |

### PERF-STRESS-002: Spike Test
| Field | Value |
|-------|-------|
| **Objective** | Test sudden traffic spike handling |
| **Pattern** | 100 VU → 500 VU instantly → 100 VU |
| **Duration** | 5 minutes |
| **Pass Criteria** | - System recovers within 30 seconds<br>- No data corruption<br>- Error rate < 10% during spike |

### PERF-STRESS-003: Rate Limiter Stress
| Field | Value |
|-------|-------|
| **Objective** | Verify rate limiter under stress |
| **Virtual Users** | 100 concurrent (same user) |
| **Duration** | 2 minutes |
| **Scenario** | Hammer single endpoint |
| **Pass Criteria** | - Rate limiter activates correctly<br>- Returns 429 after limit<br>- No server crash |

---

## 4. Endurance Test Scenarios

### PERF-ENDURANCE-001: 24-Hour Soak Test
| Field | Value |
|-------|-------|
| **Objective** | Verify long-term stability |
| **Virtual Users** | 50 concurrent |
| **Duration** | 24 hours |
| **Scenario** | Mixed workload |
| **Measurements** | - Memory usage trend<br>- Response time drift<br>- Error accumulation<br>- DB connection pool |
| **Pass Criteria** | - No memory leak (< 10% growth)<br>- Consistent response times<br>- Error rate < 1% |

### PERF-ENDURANCE-002: Database Connection Leak Test
| Field | Value |
|-------|-------|
| **Objective** | Verify no DB connection leaks |
| **Virtual Users** | 100 concurrent |
| **Duration** | 4 hours |
| **Measurements** | - Active DB connections<br>- Connection pool usage<br>- Query latency |
| **Pass Criteria** | - Connections stay within pool limit<br>- No connection timeout errors |

---

## 5. API Performance Benchmarks

### Target Response Times (SLA)
| Endpoint Category | 50th Percentile | 95th Percentile | 99th Percentile |
|-------------------|-----------------|-----------------|-----------------|
| **Authentication** | < 100ms | < 300ms | < 500ms |
| **User CRUD** | < 100ms | < 300ms | < 500ms |
| **Project List** | < 200ms | < 500ms | < 1000ms |
| **Project Details** | < 150ms | < 400ms | < 800ms |
| **File Operations** | < 200ms | < 500ms | < 1000ms |
| **Document List** | < 200ms | < 500ms | < 1000ms |
| **Document Download** | < 1000ms | < 2000ms | < 5000ms |
| **Health Check** | < 50ms | < 100ms | < 200ms |

### PERF-API-001: Authentication Endpoints
```
POST /auth/login        - Target: < 300ms (p95)
POST /auth/register     - Target: < 500ms (p95)
POST /auth/refresh      - Target: < 200ms (p95)
GET  /auth/me           - Target: < 100ms (p95)
```

### PERF-API-002: Project Endpoints
```
GET  /projects              - Target: < 500ms (p95)
GET  /projects/{id}         - Target: < 400ms (p95)
GET  /projects/{id}/files   - Target: < 500ms (p95)
POST /projects              - Target: < 1000ms (p95)
```

### PERF-API-003: Document Endpoints
```
GET  /documents/list/{id}           - Target: < 500ms (p95)
GET  /documents/download/{id}/{type} - Target: < 2000ms (p95)
GET  /documents/download-all/{id}   - Target: < 5000ms (p95)
```

### PERF-API-004: Execution Endpoints
```
POST /execution/run/{id}      - Target: < 2000ms (initial response)
POST /execution/stop/{id}     - Target: < 1000ms (p95)
GET  /execution/export/{id}   - Target: < 5000ms (p95)
```

---

## 6. Frontend Performance

### PERF-FE-001: Initial Page Load
| Metric | Target |
|--------|--------|
| **First Contentful Paint (FCP)** | < 1.5s |
| **Largest Contentful Paint (LCP)** | < 2.5s |
| **Time to Interactive (TTI)** | < 3.5s |
| **Cumulative Layout Shift (CLS)** | < 0.1 |
| **Total Bundle Size** | < 500KB (gzipped) |

### PERF-FE-002: Build Page Performance
| Metric | Target |
|--------|--------|
| **File Explorer Render** | < 500ms |
| **Code Editor Load** | < 1000ms |
| **Terminal Render** | < 300ms |
| **Tab Switch** | < 100ms |

### PERF-FE-003: Real-time Updates
| Metric | Target |
|--------|--------|
| **SSE Event Processing** | < 50ms per event |
| **UI Update Latency** | < 100ms |
| **WebSocket Reconnection** | < 2s |

### Lighthouse Targets
| Category | Score |
|----------|-------|
| Performance | > 80 |
| Accessibility | > 90 |
| Best Practices | > 90 |
| SEO | > 80 |

---

## 7. Database Performance

### PERF-DB-001: Query Performance
| Query Type | Target |
|------------|--------|
| **User Lookup (by email)** | < 5ms |
| **Project List (paginated)** | < 20ms |
| **Project with Files** | < 50ms |
| **Document List** | < 20ms |
| **Token Balance** | < 10ms |

### PERF-DB-002: Index Effectiveness
```sql
-- These queries should use indexes
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
EXPLAIN ANALYZE SELECT * FROM projects WHERE user_id = 'uuid' ORDER BY created_at DESC LIMIT 10;
EXPLAIN ANALYZE SELECT * FROM documents WHERE project_id = 'uuid';
```

### PERF-DB-003: Connection Pool
| Metric | Target |
|--------|--------|
| **Pool Size** | 20-50 connections |
| **Max Wait Time** | < 100ms |
| **Connection Reuse Rate** | > 95% |

---

## 8. AI/LLM Performance

### PERF-AI-001: Project Generation
| Phase | Target Duration |
|-------|-----------------|
| **Abstract Generation** | < 30s |
| **Plan Generation** | < 60s |
| **Code Generation (per file)** | < 20s |
| **Total Project (small)** | < 3 minutes |
| **Total Project (medium)** | < 5 minutes |
| **Total Project (large)** | < 10 minutes |

### PERF-AI-002: Document Generation
| Document Type | Target Duration |
|---------------|-----------------|
| **Project Report (60-80 pages)** | < 5 minutes |
| **SRS Document** | < 3 minutes |
| **PPT Presentation** | < 2 minutes |
| **Viva Q&A** | < 2 minutes |

### PERF-AI-003: Auto-Fixer
| Metric | Target |
|--------|--------|
| **Error Analysis** | < 5s |
| **Fix Generation** | < 15s |
| **Total Fix Cycle** | < 30s |

### PERF-AI-004: Token Efficiency
| Metric | Target |
|--------|--------|
| **Avg Tokens per Project** | < 100K |
| **Avg Tokens per Document** | < 50K |
| **Avg Tokens per Fix** | < 10K |

---

## 9. Test Execution Schedule

### Pre-Release Testing
| Test Type | Frequency | Duration |
|-----------|-----------|----------|
| Load Tests | Every release | 30 minutes |
| Stress Tests | Every major release | 1 hour |
| API Benchmarks | Every release | 15 minutes |

### Production Monitoring
| Test Type | Frequency | Duration |
|-----------|-----------|----------|
| Synthetic Monitoring | Every 5 minutes | Continuous |
| Soak Test | Weekly | 24 hours |
| Chaos Engineering | Monthly | 2 hours |

---

## 10. k6 Test Scripts

### Complete Load Test Suite
```javascript
// k6-load-test.js
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration');
const projectListDuration = new Trend('project_list_duration');

export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    errors: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000/api/v1';

export default function () {
  let token;

  group('Authentication', () => {
    const loginStart = Date.now();
    const loginRes = http.post(`${BASE_URL}/auth/login`,
      `username=user_${__VU % 100}@test.com&password=TestPassword123!`,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    loginDuration.add(Date.now() - loginStart);

    const loginSuccess = check(loginRes, {
      'login successful': (r) => r.status === 200,
      'has access token': (r) => r.json('access_token') !== undefined,
    });
    errorRate.add(!loginSuccess);

    if (loginSuccess) {
      token = loginRes.json('access_token');
    }
  });

  if (token) {
    group('Projects', () => {
      const listStart = Date.now();
      const listRes = http.get(`${BASE_URL}/projects?page=1&page_size=10`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      projectListDuration.add(Date.now() - listStart);

      const listSuccess = check(listRes, {
        'projects list successful': (r) => r.status === 200,
        'has items array': (r) => Array.isArray(r.json('items')),
      });
      errorRate.add(!listSuccess);
    });

    group('User Info', () => {
      const meRes = http.get(`${BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      check(meRes, {
        'user info successful': (r) => r.status === 200,
      });
    });
  }

  sleep(Math.random() * 3 + 1); // 1-4 second think time
}
```

---

## 11. Reporting Template

### Performance Test Report
```
========================================
BHARATBUILD AI - PERFORMANCE TEST REPORT
========================================
Date: [DATE]
Environment: [staging/production]
Test Type: [load/stress/endurance]
Duration: [X minutes/hours]

SUMMARY
-------
Total Requests: [X]
Successful: [X] ([X]%)
Failed: [X] ([X]%)
Avg Response Time: [X]ms
95th Percentile: [X]ms
99th Percentile: [X]ms
Throughput: [X] req/sec

ENDPOINT BREAKDOWN
------------------
| Endpoint | Requests | Avg (ms) | P95 (ms) | Errors |
|----------|----------|----------|----------|--------|
| POST /auth/login | X | X | X | X |
| GET /projects | X | X | X | X |
| ... | ... | ... | ... | ... |

RESOURCE UTILIZATION
--------------------
CPU: [X]% avg, [X]% max
Memory: [X]GB avg, [X]GB max
DB Connections: [X] avg, [X] max

PASS/FAIL STATUS
----------------
[PASS/FAIL] - Response time SLA
[PASS/FAIL] - Error rate SLA
[PASS/FAIL] - Throughput SLA

RECOMMENDATIONS
---------------
1. [Recommendation 1]
2. [Recommendation 2]
========================================
```

---

## 12. Tools Setup

### k6 Installation
```bash
# macOS
brew install k6

# Windows
choco install k6

# Docker
docker run -i grafana/k6 run - <script.js
```

### Running Tests
```bash
# Basic load test
k6 run --env API_URL=http://localhost:8000/api/v1 k6-load-test.js

# With HTML report
k6 run --out json=results.json k6-load-test.js

# Cloud execution
k6 cloud k6-load-test.js
```

### Artillery Installation
```bash
npm install -g artillery
artillery run load-test.yml
```

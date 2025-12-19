/**
 * BharatBuild AI - k6 Load Test Script
 *
 * Run with: k6 run --env API_URL=http://localhost:8000/api/v1 k6-load-test.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration');
const projectListDuration = new Trend('project_list_duration');
const documentListDuration = new Trend('document_list_duration');
const successfulLogins = new Counter('successful_logins');
const failedLogins = new Counter('failed_logins');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up to 10 users
    { duration: '1m', target: 50 },    // Ramp up to 50 users
    { duration: '2m', target: 50 },    // Stay at 50 users
    { duration: '1m', target: 100 },   // Ramp up to 100 users
    { duration: '2m', target: 100 },   // Stay at 100 users
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'],  // 95% of requests should be < 1s
    http_req_failed: ['rate<0.05'],     // Less than 5% errors
    errors: ['rate<0.05'],              // Custom error rate
    login_duration: ['p(95)<500'],      // Login should be fast
    project_list_duration: ['p(95)<800'],
  },
};

// Base URL from environment or default
const BASE_URL = __ENV.API_URL || 'http://localhost:8000/api/v1';

// Test users pool
const TEST_USERS = [];
for (let i = 0; i < 100; i++) {
  TEST_USERS.push({
    email: `loadtest_user_${i}@test.com`,
    password: 'TestPassword123!'
  });
}

export function setup() {
  console.log(`Starting load test against: ${BASE_URL}`);

  // Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  if (healthRes.status !== 200) {
    console.error('API health check failed!');
  }

  return { baseUrl: BASE_URL };
}

export default function (data) {
  const user = TEST_USERS[__VU % TEST_USERS.length];
  let token = null;

  // ==================== Authentication ====================
  group('Authentication', () => {
    const loginStart = Date.now();

    const loginRes = http.post(
      `${BASE_URL}/auth/login`,
      `username=${encodeURIComponent(user.email)}&password=${encodeURIComponent(user.password)}`,
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        tags: { name: 'login' },
      }
    );

    loginDuration.add(Date.now() - loginStart);

    const loginSuccess = check(loginRes, {
      'login status is 200': (r) => r.status === 200,
      'login has access token': (r) => {
        try {
          return r.json('access_token') !== undefined;
        } catch {
          return false;
        }
      },
    });

    if (loginSuccess) {
      successfulLogins.add(1);
      try {
        token = loginRes.json('access_token');
      } catch {
        token = null;
      }
    } else {
      failedLogins.add(1);
      errorRate.add(1);
    }
  });

  // Skip remaining tests if login failed
  if (!token) {
    sleep(1);
    return;
  }

  const authHeaders = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  // ==================== User Profile ====================
  group('User Profile', () => {
    const meRes = http.get(`${BASE_URL}/auth/me`, {
      headers: authHeaders,
      tags: { name: 'get_me' },
    });

    const meSuccess = check(meRes, {
      'get me status is 200': (r) => r.status === 200,
      'get me has email': (r) => {
        try {
          return r.json('email') !== undefined;
        } catch {
          return false;
        }
      },
    });

    errorRate.add(!meSuccess);
  });

  sleep(0.5);

  // ==================== Projects ====================
  group('Projects', () => {
    // List projects
    const listStart = Date.now();

    const listRes = http.get(`${BASE_URL}/projects?page=1&page_size=10`, {
      headers: authHeaders,
      tags: { name: 'list_projects' },
    });

    projectListDuration.add(Date.now() - listStart);

    const listSuccess = check(listRes, {
      'projects list status is 200': (r) => r.status === 200,
      'projects list has items': (r) => {
        try {
          return Array.isArray(r.json('items'));
        } catch {
          return false;
        }
      },
    });

    errorRate.add(!listSuccess);

    // Get first project details if available
    if (listSuccess) {
      try {
        const items = listRes.json('items');
        if (items && items.length > 0) {
          const projectId = items[0].id;

          const detailRes = http.get(`${BASE_URL}/projects/${projectId}`, {
            headers: authHeaders,
            tags: { name: 'get_project' },
          });

          check(detailRes, {
            'project detail status is 200': (r) => r.status === 200,
          });
        }
      } catch {
        // Ignore parsing errors
      }
    }
  });

  sleep(0.5);

  // ==================== Documents ====================
  group('Documents', () => {
    // Get document types (public endpoint)
    const typesRes = http.get(`${BASE_URL}/documents/types`, {
      tags: { name: 'document_types' },
    });

    check(typesRes, {
      'document types status is 200': (r) => r.status === 200,
    });
  });

  sleep(0.5);

  // ==================== Plan Status ====================
  group('User Features', () => {
    const planRes = http.get(`${BASE_URL}/users/plan-status`, {
      headers: authHeaders,
      tags: { name: 'plan_status' },
    });

    check(planRes, {
      'plan status is 200': (r) => r.status === 200,
    });

    const balanceRes = http.get(`${BASE_URL}/users/token-balance`, {
      headers: authHeaders,
      tags: { name: 'token_balance' },
    });

    check(balanceRes, {
      'token balance is 200': (r) => r.status === 200,
    });
  });

  // Think time between iterations
  sleep(Math.random() * 2 + 1); // 1-3 seconds
}

export function teardown(data) {
  console.log('Load test completed');
  console.log(`Tested against: ${data.baseUrl}`);
}

// Handle summary
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data, null, 2),
  };
}

function textSummary(data, options) {
  const metrics = data.metrics;

  let summary = `
================================================================================
                    BHARATBUILD AI - LOAD TEST SUMMARY
================================================================================

REQUESTS
--------
Total Requests:     ${metrics.http_reqs?.values?.count || 0}
Failed Requests:    ${metrics.http_req_failed?.values?.passes || 0}
Request Rate:       ${(metrics.http_reqs?.values?.rate || 0).toFixed(2)} req/s

RESPONSE TIMES
--------------
Average:            ${(metrics.http_req_duration?.values?.avg || 0).toFixed(2)} ms
Median (p50):       ${(metrics.http_req_duration?.values?.['p(50)'] || 0).toFixed(2)} ms
95th Percentile:    ${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)} ms
99th Percentile:    ${(metrics.http_req_duration?.values?.['p(99)'] || 0).toFixed(2)} ms
Max:                ${(metrics.http_req_duration?.values?.max || 0).toFixed(2)} ms

CUSTOM METRICS
--------------
Login Duration (p95):       ${(metrics.login_duration?.values?.['p(95)'] || 0).toFixed(2)} ms
Project List Duration (p95): ${(metrics.project_list_duration?.values?.['p(95)'] || 0).toFixed(2)} ms
Successful Logins:          ${metrics.successful_logins?.values?.count || 0}
Failed Logins:              ${metrics.failed_logins?.values?.count || 0}
Error Rate:                 ${((metrics.errors?.values?.rate || 0) * 100).toFixed(2)}%

VIRTUAL USERS
-------------
Max VUs:            ${data.metrics.vus_max?.values?.max || 0}

================================================================================
`;

  return summary;
}

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

/**
 * STUDI CASE: Load Testing JSONPlaceholder API
 * 
 * JSONPlaceholder adalah REST API dummy gratis untuk testing.
 * URL: https://jsonplaceholder.typicode.com
 * 
 * Endpoints yang di-test:
 * - GET /posts        - List semua posts
 * - GET /posts/:id    - Detail post
 * - POST /posts       - Create post baru
 * - PUT /posts/:id    - Update post
 * - DELETE /posts/:id - Hapus post
 * - GET /users        - List users
 * - GET /comments     - List comments dengan filter
 */

// Custom metrics
const errorRate = new Rate('errors');
const postDuration = new Trend('post_duration');
const getDuration = new Trend('get_duration');

// Konfigurasi test scenarios
export const options = {
  scenarios: {
    // Scenario 1: Smoke test - cek basic functionality
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      startTime: '0s',
      tags: { test_type: 'smoke' },
    },
    // Scenario 2: Load test - normal load
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 20 },   // Ramp up
        { duration: '2m', target: 20 },   // Steady state
        { duration: '1m', target: 0 },    // Ramp down
      ],
      startTime: '30s',
      tags: { test_type: 'load' },
    },
    // Scenario 3: Stress test - push limits
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 },
        { duration: '1m', target: 50 },
        { duration: '30s', target: 100 },
        { duration: '1m', target: 100 },
        { duration: '30s', target: 0 },
      ],
      startTime: '5m',
      tags: { test_type: 'stress' },
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.05'],
    errors: ['rate<0.1'],
  },
};

const BASE_URL = 'https://jsonplaceholder.typicode.com';

// Helper function untuk random ID
function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export default function () {
  // ============================================
  // GROUP 1: Posts CRUD Operations
  // ============================================
  group('Posts API', () => {
    // GET - List all posts
    const listRes = http.get(`${BASE_URL}/posts`);
    check(listRes, {
      'List posts - status 200': (r) => r.status === 200,
      'List posts - has data': (r) => JSON.parse(r.body).length > 0,
    });
    getDuration.add(listRes.timings.duration);
    errorRate.add(listRes.status !== 200);

    sleep(0.5);

    // GET - Single post detail
    const postId = randomInt(1, 100);
    const detailRes = http.get(`${BASE_URL}/posts/${postId}`);
    check(detailRes, {
      'Get post detail - status 200': (r) => r.status === 200,
      'Get post detail - has title': (r) => JSON.parse(r.body).title !== undefined,
    });
    getDuration.add(detailRes.timings.duration);

    sleep(0.5);

    // POST - Create new post
    const createPayload = JSON.stringify({
      title: 'Load Test Post',
      body: 'Ini adalah post dari k6 load testing',
      userId: randomInt(1, 10),
    });
    const createRes = http.post(`${BASE_URL}/posts`, createPayload, {
      headers: { 'Content-Type': 'application/json' },
    });
    check(createRes, {
      'Create post - status 201': (r) => r.status === 201,
      'Create post - returns id': (r) => JSON.parse(r.body).id !== undefined,
    });
    postDuration.add(createRes.timings.duration);
    errorRate.add(createRes.status !== 201);

    sleep(0.5);

    // PUT - Update post
    const updatePayload = JSON.stringify({
      id: 1,
      title: 'Updated Title',
      body: 'Updated body dari k6',
      userId: 1,
    });
    const updateRes = http.put(`${BASE_URL}/posts/1`, updatePayload, {
      headers: { 'Content-Type': 'application/json' },
    });
    check(updateRes, {
      'Update post - status 200': (r) => r.status === 200,
    });

    sleep(0.5);

    // DELETE - Delete post
    const deleteRes = http.del(`${BASE_URL}/posts/1`);
    check(deleteRes, {
      'Delete post - status 200': (r) => r.status === 200,
    });
  });

  sleep(1);

  // ============================================
  // GROUP 2: Users & Comments
  // ============================================
  group('Users & Comments API', () => {
    // GET - List users
    const usersRes = http.get(`${BASE_URL}/users`);
    check(usersRes, {
      'List users - status 200': (r) => r.status === 200,
      'List users - has 10 users': (r) => JSON.parse(r.body).length === 10,
    });

    sleep(0.5);

    // GET - Comments by post (query parameter)
    const commentsRes = http.get(`${BASE_URL}/comments?postId=${randomInt(1, 100)}`);
    check(commentsRes, {
      'Get comments - status 200': (r) => r.status === 200,
      'Get comments - is array': (r) => Array.isArray(JSON.parse(r.body)),
    });

    sleep(0.5);

    // GET - Nested resource (post's comments)
    const nestedRes = http.get(`${BASE_URL}/posts/${randomInt(1, 100)}/comments`);
    check(nestedRes, {
      'Nested comments - status 200': (r) => r.status === 200,
    });
  });

  sleep(1);
}

// Lifecycle hooks
export function setup() {
  console.log('🚀 Starting load test against JSONPlaceholder API');
  // Verify API is accessible
  const res = http.get(`${BASE_URL}/posts/1`);
  if (res.status !== 200) {
    throw new Error('API tidak accessible!');
  }
  return { startTime: new Date().toISOString() };
}

export function teardown(data) {
  console.log(`✅ Load test completed. Started at: ${data.startTime}`);
}

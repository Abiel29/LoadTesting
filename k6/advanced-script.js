import http from 'k6/http';
import { check, sleep, group, fail } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import { randomItem, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

/**
 * ADVANCED LOAD TESTING SCRIPT
 * 
 * Target: JSONPlaceholder + ReqRes API
 * 
 * Features:
 * - Multiple API targets
 * - Authentication flow simulation
 * - Data-driven testing dengan SharedArray
 * - Custom metrics yang komprehensif
 * - Multiple scenarios (smoke, load, stress, spike, soak)
 * - Request batching
 * - Error handling & retry logic
 * - Response validation yang detail
 */

// ============================================
// CUSTOM METRICS
// ============================================
const errorRate = new Rate('custom_error_rate');
const successRate = new Rate('custom_success_rate');
const authDuration = new Trend('auth_duration_ms');
const crudDuration = new Trend('crud_duration_ms');
const searchDuration = new Trend('search_duration_ms');
const totalRequests = new Counter('total_requests');
const failedRequests = new Counter('failed_requests');
const activeUsers = new Gauge('active_users');

// ============================================
// TEST DATA (SharedArray untuk efisiensi memory)
// ============================================
const testUsers = new SharedArray('users', function () {
  return [
    { email: 'eve.holt@reqres.in', password: 'cityslicka' },
    { email: 'emma.wong@reqres.in', password: 'pistol' },
    { email: 'charles.morris@reqres.in', password: 'pistol' },
  ];
});

const postTitles = new SharedArray('titles', function () {
  return [
    'Performance Testing Best Practices',
    'Scaling Microservices Architecture',
    'DevOps Pipeline Optimization',
    'Cloud Native Development',
    'API Design Patterns',
    'Database Performance Tuning',
    'Container Orchestration Guide',
    'Security in Modern Applications',
  ];
});

// ============================================
// CONFIGURATION
// ============================================
const CONFIG = {
  jsonPlaceholder: 'https://jsonplaceholder.typicode.com',
  reqRes: 'https://reqres.in/api',
  thinkTime: { min: 0.5, max: 2 },
  retryAttempts: 3,
  retryDelay: 1,
};

export const options = {
  scenarios: {
    // Smoke Test - Quick sanity check
    smoke_test: {
      executor: 'constant-vus',
      vus: 2,
      duration: '1m',
      startTime: '0s',
      tags: { scenario: 'smoke' },
      env: { SCENARIO: 'smoke' },
    },

    // Load Test - Normal expected load
    load_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 30 },
        { duration: '5m', target: 30 },
        { duration: '2m', target: 0 },
      ],
      startTime: '1m',
      tags: { scenario: 'load' },
      env: { SCENARIO: 'load' },
    },

    // Stress Test - Beyond normal capacity
    stress_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },
        { duration: '3m', target: 50 },
        { duration: '2m', target: 100 },
        { duration: '3m', target: 100 },
        { duration: '2m', target: 150 },
        { duration: '3m', target: 150 },
        { duration: '2m', target: 0 },
      ],
      startTime: '10m',
      tags: { scenario: 'stress' },
      env: { SCENARIO: 'stress' },
    },

    // Spike Test - Sudden traffic surge
    spike_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 10 },
        { duration: '30s', target: 200 },  // Spike!
        { duration: '1m', target: 200 },
        { duration: '30s', target: 10 },
        { duration: '30s', target: 0 },
      ],
      startTime: '27m',
      tags: { scenario: 'spike' },
      env: { SCENARIO: 'spike' },
    },

    // Soak Test - Extended duration
    soak_test: {
      executor: 'constant-vus',
      vus: 20,
      duration: '30m',
      startTime: '30m',
      tags: { scenario: 'soak' },
      env: { SCENARIO: 'soak' },
    },

    // Breakpoint Test - Find the limit
    breakpoint_test: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 500,
      stages: [
        { duration: '2m', target: 50 },
        { duration: '2m', target: 100 },
        { duration: '2m', target: 200 },
        { duration: '2m', target: 300 },
      ],
      startTime: '60m',
      tags: { scenario: 'breakpoint' },
      env: { SCENARIO: 'breakpoint' },
    },
  },

  thresholds: {
    http_req_duration: ['p(50)<200', 'p(90)<500', 'p(95)<800', 'p(99)<1500'],
    http_req_failed: ['rate<0.05'],
    custom_error_rate: ['rate<0.1'],
    custom_success_rate: ['rate>0.9'],
    auth_duration_ms: ['p(95)<1000'],
    crud_duration_ms: ['p(95)<600'],
    search_duration_ms: ['p(95)<400'],
    iteration_duration: ['p(95)<10000'],
  },
};

// ============================================
// HELPER FUNCTIONS
// ============================================
function think() {
  sleep(randomIntBetween(CONFIG.thinkTime.min * 1000, CONFIG.thinkTime.max * 1000) / 1000);
}

function retryRequest(requestFn, maxAttempts = CONFIG.retryAttempts) {
  let lastError;
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = requestFn();
      if (response.status >= 200 && response.status < 300) {
        return response;
      }
      if (response.status >= 400 && response.status < 500) {
        return response; // Client error, don't retry
      }
      lastError = `Status ${response.status}`;
    } catch (e) {
      lastError = e.message;
    }
    if (i < maxAttempts - 1) {
      sleep(CONFIG.retryDelay);
    }
  }
  console.warn(`Request failed after ${maxAttempts} attempts: ${lastError}`);
  return null;
}

function validateResponse(response, checks, metricTrend) {
  totalRequests.add(1);
  const passed = check(response, checks);
  
  if (!passed) {
    failedRequests.add(1);
    errorRate.add(1);
    successRate.add(0);
  } else {
    errorRate.add(0);
    successRate.add(1);
  }
  
  if (metricTrend && response) {
    metricTrend.add(response.timings.duration);
  }
  
  return passed;
}

// ============================================
// API MODULES
// ============================================
const AuthAPI = {
  login(user) {
    const response = http.post(
      `${CONFIG.reqRes}/login`,
      JSON.stringify({ email: user.email, password: user.password }),
      { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: 'login' } }
    );
    
    validateResponse(response, {
      'Login successful': (r) => r.status === 200,
      'Token received': (r) => r.json('token') !== undefined,
    }, authDuration);
    
    return response.status === 200 ? response.json('token') : null;
  },

  register(email, password) {
    const response = http.post(
      `${CONFIG.reqRes}/register`,
      JSON.stringify({ email, password }),
      { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: 'register' } }
    );
    
    validateResponse(response, {
      'Registration successful': (r) => r.status === 200,
      'User ID received': (r) => r.json('id') !== undefined,
    }, authDuration);
    
    return response;
  },
};


const PostsAPI = {
  list(params = {}) {
    const queryString = Object.entries(params)
      .map(([k, v]) => `${k}=${v}`)
      .join('&');
    const url = queryString 
      ? `${CONFIG.jsonPlaceholder}/posts?${queryString}`
      : `${CONFIG.jsonPlaceholder}/posts`;
    
    const response = http.get(url, { tags: { endpoint: 'posts_list' } });
    
    validateResponse(response, {
      'Posts list - status 200': (r) => r.status === 200,
      'Posts list - is array': (r) => Array.isArray(r.json()),
      'Posts list - has items': (r) => r.json().length > 0,
    }, searchDuration);
    
    return response;
  },

  get(id) {
    const response = http.get(
      `${CONFIG.jsonPlaceholder}/posts/${id}`,
      { tags: { endpoint: 'posts_get' } }
    );
    
    validateResponse(response, {
      'Post detail - status 200': (r) => r.status === 200,
      'Post detail - has id': (r) => r.json('id') === id,
      'Post detail - has title': (r) => r.json('title') !== undefined,
      'Post detail - has body': (r) => r.json('body') !== undefined,
    }, crudDuration);
    
    return response;
  },

  create(data) {
    const response = http.post(
      `${CONFIG.jsonPlaceholder}/posts`,
      JSON.stringify(data),
      { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: 'posts_create' } }
    );
    
    validateResponse(response, {
      'Post create - status 201': (r) => r.status === 201,
      'Post create - has id': (r) => r.json('id') !== undefined,
      'Post create - title matches': (r) => r.json('title') === data.title,
    }, crudDuration);
    
    return response;
  },

  update(id, data) {
    const response = http.put(
      `${CONFIG.jsonPlaceholder}/posts/${id}`,
      JSON.stringify({ id, ...data }),
      { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: 'posts_update' } }
    );
    
    validateResponse(response, {
      'Post update - status 200': (r) => r.status === 200,
      'Post update - id matches': (r) => r.json('id') === id,
    }, crudDuration);
    
    return response;
  },

  patch(id, data) {
    const response = http.patch(
      `${CONFIG.jsonPlaceholder}/posts/${id}`,
      JSON.stringify(data),
      { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: 'posts_patch' } }
    );
    
    validateResponse(response, {
      'Post patch - status 200': (r) => r.status === 200,
    }, crudDuration);
    
    return response;
  },

  delete(id) {
    const response = http.del(
      `${CONFIG.jsonPlaceholder}/posts/${id}`,
      null,
      { tags: { endpoint: 'posts_delete' } }
    );
    
    validateResponse(response, {
      'Post delete - status 200': (r) => r.status === 200,
    }, crudDuration);
    
    return response;
  },

  getComments(postId) {
    const response = http.get(
      `${CONFIG.jsonPlaceholder}/posts/${postId}/comments`,
      { tags: { endpoint: 'posts_comments' } }
    );
    
    validateResponse(response, {
      'Post comments - status 200': (r) => r.status === 200,
      'Post comments - is array': (r) => Array.isArray(r.json()),
    }, searchDuration);
    
    return response;
  },
};

const UsersAPI = {
  list(page = 1) {
    const response = http.get(
      `${CONFIG.reqRes}/users?page=${page}`,
      { tags: { endpoint: 'users_list' } }
    );
    
    validateResponse(response, {
      'Users list - status 200': (r) => r.status === 200,
      'Users list - has data': (r) => r.json('data') !== undefined,
      'Users list - has pagination': (r) => r.json('total_pages') !== undefined,
    }, searchDuration);
    
    return response;
  },

  get(id) {
    const response = http.get(
      `${CONFIG.reqRes}/users/${id}`,
      { tags: { endpoint: 'users_get' } }
    );
    
    validateResponse(response, {
      'User detail - status 200': (r) => r.status === 200,
      'User detail - has data': (r) => r.json('data') !== undefined,
    }, crudDuration);
    
    return response;
  },

  create(data) {
    const response = http.post(
      `${CONFIG.reqRes}/users`,
      JSON.stringify(data),
      { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: 'users_create' } }
    );
    
    validateResponse(response, {
      'User create - status 201': (r) => r.status === 201,
      'User create - has id': (r) => r.json('id') !== undefined,
      'User create - has createdAt': (r) => r.json('createdAt') !== undefined,
    }, crudDuration);
    
    return response;
  },

  update(id, data) {
    const response = http.put(
      `${CONFIG.reqRes}/users/${id}`,
      JSON.stringify(data),
      { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: 'users_update' } }
    );
    
    validateResponse(response, {
      'User update - status 200': (r) => r.status === 200,
      'User update - has updatedAt': (r) => r.json('updatedAt') !== undefined,
    }, crudDuration);
    
    return response;
  },

  delete(id) {
    const response = http.del(
      `${CONFIG.reqRes}/users/${id}`,
      null,
      { tags: { endpoint: 'users_delete' } }
    );
    
    validateResponse(response, {
      'User delete - status 204': (r) => r.status === 204,
    }, crudDuration);
    
    return response;
  },
};


const ResourcesAPI = {
  listAlbums() {
    return http.get(`${CONFIG.jsonPlaceholder}/albums`, { tags: { endpoint: 'albums_list' } });
  },

  getAlbumPhotos(albumId) {
    return http.get(`${CONFIG.jsonPlaceholder}/albums/${albumId}/photos`, { tags: { endpoint: 'album_photos' } });
  },

  listTodos(userId = null) {
    const url = userId 
      ? `${CONFIG.jsonPlaceholder}/todos?userId=${userId}`
      : `${CONFIG.jsonPlaceholder}/todos`;
    return http.get(url, { tags: { endpoint: 'todos_list' } });
  },

  getColors() {
    return http.get(`${CONFIG.reqRes}/unknown`, { tags: { endpoint: 'colors_list' } });
  },

  getColor(id) {
    return http.get(`${CONFIG.reqRes}/unknown/${id}`, { tags: { endpoint: 'color_get' } });
  },

  delayedResponse(seconds = 3) {
    return http.get(`${CONFIG.reqRes}/users?delay=${seconds}`, { 
      tags: { endpoint: 'delayed' },
      timeout: '10s',
    });
  },
};

// ============================================
// BATCH REQUESTS
// ============================================
function batchGetPosts(ids) {
  const requests = ids.map(id => ({
    method: 'GET',
    url: `${CONFIG.jsonPlaceholder}/posts/${id}`,
    params: { tags: { endpoint: 'batch_posts' } },
  }));
  
  const responses = http.batch(requests);
  
  responses.forEach((response, index) => {
    validateResponse(response, {
      [`Batch post ${ids[index]} - status 200`]: (r) => r.status === 200,
    }, crudDuration);
  });
  
  return responses;
}

function batchGetUsers(ids) {
  const requests = ids.map(id => ({
    method: 'GET',
    url: `${CONFIG.reqRes}/users/${id}`,
    params: { tags: { endpoint: 'batch_users' } },
  }));
  
  return http.batch(requests);
}

// ============================================
// USER FLOWS / SCENARIOS
// ============================================
function browsingUserFlow() {
  group('Browsing User Flow', () => {
    // 1. Browse posts
    const postsRes = PostsAPI.list();
    think();
    
    // 2. View random post detail
    if (postsRes.status === 200) {
      const posts = postsRes.json();
      const randomPost = posts[randomIntBetween(0, Math.min(posts.length - 1, 99))];
      PostsAPI.get(randomPost.id);
      think();
      
      // 3. View post comments
      PostsAPI.getComments(randomPost.id);
      think();
    }
    
    // 4. Browse users
    UsersAPI.list(randomIntBetween(1, 2));
    think();
    
    // 5. View random user
    UsersAPI.get(randomIntBetween(1, 12));
  });
}

function contentCreatorFlow() {
  group('Content Creator Flow', () => {
    // 1. Login
    const user = randomItem(testUsers);
    const token = AuthAPI.login(user);
    think();
    
    if (!token) {
      console.warn('Login failed, skipping content creation');
      return;
    }
    
    // 2. Create new post
    const newPost = {
      title: randomItem(postTitles),
      body: `Content created during load test at ${new Date().toISOString()}`,
      userId: randomIntBetween(1, 10),
    };
    const createRes = PostsAPI.create(newPost);
    think();
    
    // 3. Update the post
    if (createRes.status === 201) {
      const postId = createRes.json('id');
      PostsAPI.update(postId, {
        ...newPost,
        title: `Updated: ${newPost.title}`,
      });
      think();
      
      // 4. Partial update
      PostsAPI.patch(postId, { title: `Final: ${newPost.title}` });
      think();
    }
    
    // 5. Create user
    UsersAPI.create({
      name: `Test User ${randomIntBetween(1000, 9999)}`,
      job: 'Load Tester',
    });
  });
}

function searchAndFilterFlow() {
  group('Search and Filter Flow', () => {
    // 1. Filter posts by user
    PostsAPI.list({ userId: randomIntBetween(1, 10) });
    think();
    
    // 2. Get user's todos
    ResourcesAPI.listTodos(randomIntBetween(1, 10));
    think();
    
    // 3. Browse albums
    ResourcesAPI.listAlbums();
    think();
    
    // 4. Get album photos
    ResourcesAPI.getAlbumPhotos(randomIntBetween(1, 100));
    think();
    
    // 5. Get colors (resources)
    ResourcesAPI.getColors();
    think();
    
    // 6. Get specific color
    ResourcesAPI.getColor(randomIntBetween(1, 12));
  });
}

function adminFlow() {
  group('Admin Flow', () => {
    // 1. Batch get multiple posts
    const postIds = Array.from({ length: 5 }, () => randomIntBetween(1, 100));
    batchGetPosts(postIds);
    think();
    
    // 2. Batch get multiple users
    const userIds = Array.from({ length: 3 }, () => randomIntBetween(1, 12));
    batchGetUsers(userIds);
    think();
    
    // 3. Delete operations
    PostsAPI.delete(randomIntBetween(1, 100));
    think();
    
    UsersAPI.delete(randomIntBetween(1, 12));
    think();
    
    // 4. Update user
    UsersAPI.update(randomIntBetween(1, 12), {
      name: 'Updated Admin User',
      job: 'System Administrator',
    });
  });
}

function stressTestFlow() {
  group('Stress Test - Rapid Requests', () => {
    // Rapid fire requests without think time
    for (let i = 0; i < 5; i++) {
      PostsAPI.list();
      UsersAPI.list();
      ResourcesAPI.getColors();
    }
  });
}

function delayedResponseFlow() {
  group('Delayed Response Test', () => {
    // Test dengan response yang di-delay
    ResourcesAPI.delayedResponse(2);
  });
}

// ============================================
// MAIN EXECUTION
// ============================================
export default function () {
  activeUsers.add(1);
  
  const scenario = __ENV.SCENARIO || 'load';
  
  // Pilih flow berdasarkan weighted random
  const flowSelector = Math.random();
  
  if (scenario === 'stress' || scenario === 'spike' || scenario === 'breakpoint') {
    // Stress scenarios - more aggressive
    if (flowSelector < 0.4) {
      stressTestFlow();
    } else if (flowSelector < 0.7) {
      browsingUserFlow();
    } else {
      contentCreatorFlow();
    }
  } else if (scenario === 'soak') {
    // Soak test - balanced, realistic
    if (flowSelector < 0.5) {
      browsingUserFlow();
    } else if (flowSelector < 0.75) {
      searchAndFilterFlow();
    } else if (flowSelector < 0.9) {
      contentCreatorFlow();
    } else {
      adminFlow();
    }
  } else {
    // Default (smoke, load) - all flows
    if (flowSelector < 0.35) {
      browsingUserFlow();
    } else if (flowSelector < 0.55) {
      searchAndFilterFlow();
    } else if (flowSelector < 0.75) {
      contentCreatorFlow();
    } else if (flowSelector < 0.9) {
      adminFlow();
    } else {
      delayedResponseFlow();
    }
  }
  
  activeUsers.add(-1);
}

// ============================================
// LIFECYCLE HOOKS
// ============================================
export function setup() {
  console.log('🚀 Advanced Load Test Starting...');
  console.log(`📍 Targets: ${CONFIG.jsonPlaceholder}, ${CONFIG.reqRes}`);
  
  // Verify APIs are accessible
  const checks = [
    http.get(`${CONFIG.jsonPlaceholder}/posts/1`),
    http.get(`${CONFIG.reqRes}/users/1`),
  ];
  
  const allHealthy = checks.every(r => r.status === 200);
  if (!allHealthy) {
    fail('One or more APIs are not accessible!');
  }
  
  return {
    startTime: new Date().toISOString(),
    targets: [CONFIG.jsonPlaceholder, CONFIG.reqRes],
  };
}

export function teardown(data) {
  console.log('✅ Load Test Completed');
  console.log(`⏱️  Started: ${data.startTime}`);
  console.log(`⏱️  Ended: ${new Date().toISOString()}`);
}

// Import k6-reporter untuk HTML report yang lebih bagus
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";

export function handleSummary(data) {
  return {
    'stdout': textSummary(data),
    'results/summary.json': JSON.stringify(data, null, 2),
    'results/summary.html': htmlReport(data),
  };
}

function textSummary(data) {
  const { metrics } = data;
  let output = '\n========== LOAD TEST SUMMARY ==========\n\n';
  output += `Total Requests: ${metrics.http_reqs?.values?.count || 0}\n`;
  output += `Failed Requests: ${metrics.http_req_failed?.values?.passes || 0}\n`;
  output += `Avg Duration: ${(metrics.http_req_duration?.values?.avg || 0).toFixed(2)}ms\n`;
  output += `P95 Duration: ${(metrics.http_req_duration?.values?.['p(95)'] || 0).toFixed(2)}ms\n`;
  output += `P99 Duration: ${(metrics.http_req_duration?.values?.['p(99)'] || 0).toFixed(2)}ms\n`;
  return output;
}

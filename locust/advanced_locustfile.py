"""
============================================
ADVANCED LOAD TESTING - LOCUST
============================================

Features:
- Multiple API targets (JSONPlaceholder + ReqRes)
- Authentication dengan token management
- Sequential task flows
- Custom event handlers & metrics
- Load shape customization
- Distributed testing support
- Response validation
- Data-driven testing

Cara run:
    locust -f advanced_locustfile.py

Distributed mode (master):
    locust -f advanced_locustfile.py --master

Distributed mode (worker):
    locust -f advanced_locustfile.py --worker --master-host=<master-ip>

Headless dengan custom load shape:
    locust -f advanced_locustfile.py --headless --users 100 --spawn-rate 10 -t 10m
"""

import random
import json
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from locust import (
    HttpUser, TaskSet, task, between, tag, events,
    LoadTestShape, FastHttpUser
)
from locust.runners import MasterRunner, WorkerRunner

# ============================================
# CONFIGURATION
# ============================================
@dataclass
class APIConfig:
    json_placeholder: str = "https://jsonplaceholder.typicode.com"
    # Using httpbin.org as fallback since reqres.in has rate limiting
    httpbin: str = "https://httpbin.org"

CONFIG = APIConfig()

POST_TITLES = [
    "Performance Testing Best Practices",
    "Scaling Microservices Architecture",
    "DevOps Pipeline Optimization",
    "Cloud Native Development",
    "API Design Patterns",
]

# ============================================
# CUSTOM METRICS & LOGGING
# ============================================
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Custom metrics collector untuk tracking tambahan."""
    
    def __init__(self):
        self.auth_success = 0
        self.auth_failure = 0
        self.crud_operations = {"create": 0, "read": 0, "update": 0, "delete": 0}
        self.response_codes: Dict[int, int] = {}
        self.start_time: Optional[datetime] = None
    
    def record_auth(self, success: bool):
        if success:
            self.auth_success += 1
        else:
            self.auth_failure += 1
    
    def record_crud(self, operation: str):
        if operation in self.crud_operations:
            self.crud_operations[operation] += 1
    
    def record_response(self, status_code: int):
        self.response_codes[status_code] = self.response_codes.get(status_code, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "auth_success_rate": self.auth_success / max(self.auth_success + self.auth_failure, 1),
            "crud_operations": self.crud_operations,
            "response_codes": self.response_codes,
        }

metrics = MetricsCollector()

# ============================================
# EVENT HANDLERS
# ============================================
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    metrics.start_time = datetime.now()
    logger.info("🚀 Advanced Load Test Started")
    logger.info(f"   Targets: {CONFIG.json_placeholder}, {CONFIG.httpbin}")
    
    if isinstance(environment.runner, MasterRunner):
        logger.info("   Running in MASTER mode")
    elif isinstance(environment.runner, WorkerRunner):
        logger.info("   Running in WORKER mode")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    logger.info("✅ Load Test Completed")
    logger.info(f"   Summary: {json.dumps(metrics.get_summary(), indent=2)}")

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, 
               context, exception, start_time, url, **kwargs):
    """Called for every request."""
    if response is not None and hasattr(response, 'status_code'):
        metrics.record_response(response.status_code)

@events.user_error.add_listener
def on_user_error(user_instance, exception, tb, **kwargs):
    """Called when user encounters an error."""
    logger.error(f"User error: {exception}")


# ============================================
# API CLIENT MIXINS
# ============================================
class AuthMixin:
    """Mixin untuk authentication operations (simulated)."""
    
    token: Optional[str] = None
    
    def login(self, email: str = "test@example.com", password: str = "password") -> bool:
        """Simulated login using httpbin."""
        with self.client.post(
            f"{CONFIG.httpbin}/post",
            json={"email": email, "password": password},
            name="[AUTH] POST /login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                self.token = "simulated_token_12345"
                metrics.record_auth(True)
                response.success()
                return True
            else:
                metrics.record_auth(False)
                response.failure(f"Login failed: {response.status_code}")
                return False
    
    def register(self, email: str, password: str) -> Optional[Dict]:
        """Simulated register using httpbin."""
        with self.client.post(
            f"{CONFIG.httpbin}/post",
            json={"email": email, "password": password},
            name="[AUTH] POST /register",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                return {"id": random.randint(1, 1000), "token": "fake_token"}
            else:
                response.failure(f"Register failed: {response.status_code}")
                return None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers dengan token."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers


class PostsMixin:
    """Mixin untuk Posts API operations."""
    
    def list_posts(self, user_id: Optional[int] = None) -> List[Dict]:
        """GET - List posts dengan optional filter."""
        url = f"{CONFIG.json_placeholder}/posts"
        if user_id:
            url += f"?userId={user_id}"
        
        with self.client.get(url, name="[POSTS] GET /posts", catch_response=True) as response:
            if response.status_code == 200:
                metrics.record_crud("read")
                response.success()
                return response.json()
            else:
                response.failure(f"Status: {response.status_code}")
                return []
    
    def get_post(self, post_id: int) -> Optional[Dict]:
        """GET - Detail post."""
        with self.client.get(
            f"{CONFIG.json_placeholder}/posts/{post_id}",
            name="[POSTS] GET /posts/:id",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "title" in data and "body" in data:
                    metrics.record_crud("read")
                    response.success()
                    return data
                else:
                    response.failure("Missing required fields")
            else:
                response.failure(f"Status: {response.status_code}")
            return None
    
    def create_post(self, title: str, body: str, user_id: int) -> Optional[Dict]:
        """POST - Create post baru."""
        payload = {"title": title, "body": body, "userId": user_id}
        
        with self.client.post(
            f"{CONFIG.json_placeholder}/posts",
            json=payload,
            name="[POSTS] POST /posts",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                metrics.record_crud("create")
                response.success()
                return response.json()
            else:
                response.failure(f"Status: {response.status_code}")
                return None
    
    def update_post(self, post_id: int, title: str, body: str, user_id: int) -> bool:
        """PUT - Full update post."""
        payload = {"id": post_id, "title": title, "body": body, "userId": user_id}
        
        with self.client.put(
            f"{CONFIG.json_placeholder}/posts/{post_id}",
            json=payload,
            name="[POSTS] PUT /posts/:id",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                metrics.record_crud("update")
                response.success()
                return True
            else:
                response.failure(f"Status: {response.status_code}")
                return False
    
    def patch_post(self, post_id: int, updates: Dict) -> bool:
        """PATCH - Partial update post."""
        with self.client.patch(
            f"{CONFIG.json_placeholder}/posts/{post_id}",
            json=updates,
            name="[POSTS] PATCH /posts/:id",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                metrics.record_crud("update")
                response.success()
                return True
            else:
                response.failure(f"Status: {response.status_code}")
                return False
    
    def delete_post(self, post_id: int) -> bool:
        """DELETE - Hapus post."""
        with self.client.delete(
            f"{CONFIG.json_placeholder}/posts/{post_id}",
            name="[POSTS] DELETE /posts/:id",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                metrics.record_crud("delete")
                response.success()
                return True
            else:
                response.failure(f"Status: {response.status_code}")
                return False
    
    def get_post_comments(self, post_id: int) -> List[Dict]:
        """GET - Comments dari post."""
        with self.client.get(
            f"{CONFIG.json_placeholder}/posts/{post_id}/comments",
            name="[POSTS] GET /posts/:id/comments",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                return response.json()
            else:
                response.failure(f"Status: {response.status_code}")
                return []


class UsersMixin:
    """Mixin untuk Users API operations (using JSONPlaceholder)."""
    
    def list_users(self, page: int = 1) -> List[Dict]:
        """GET - List users."""
        with self.client.get(
            f"{CONFIG.json_placeholder}/users",
            name="[USERS] GET /users",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                return response.json()
            else:
                response.failure(f"Status: {response.status_code}")
            return []
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """GET - Detail user."""
        with self.client.get(
            f"{CONFIG.json_placeholder}/users/{user_id}",
            name="[USERS] GET /users/:id",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                return response.json()
            else:
                response.failure(f"Status: {response.status_code}")
                return None
    
    def create_user(self, name: str, job: str) -> Optional[Dict]:
        """POST - Create user baru."""
        with self.client.post(
            f"{CONFIG.json_placeholder}/users",
            json={"name": name, "job": job},
            name="[USERS] POST /users",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
                return response.json()
            else:
                response.failure(f"Status: {response.status_code}")
                return None
    
    def update_user(self, user_id: int, name: str, job: str) -> bool:
        """PUT - Update user."""
        with self.client.put(
            f"{CONFIG.json_placeholder}/users/{user_id}",
            json={"name": name, "job": job},
            name="[USERS] PUT /users/:id",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                return True
            else:
                response.failure(f"Status: {response.status_code}")
                return False
    
    def delete_user(self, user_id: int) -> bool:
        """DELETE - Hapus user."""
        with self.client.delete(
            f"{CONFIG.json_placeholder}/users/{user_id}",
            name="[USERS] DELETE /users/:id",
            catch_response=True
        ) as response:
            # JSONPlaceholder returns 200 for delete
            if response.status_code == 200:
                response.success()
                return True
            else:
                response.failure(f"Status: {response.status_code}")
                return False


class ResourcesMixin:
    """Mixin untuk additional resources."""
    
    def list_albums(self) -> List[Dict]:
        """GET - List albums."""
        response = self.client.get(
            f"{CONFIG.json_placeholder}/albums",
            name="[RESOURCES] GET /albums"
        )
        return response.json() if response.status_code == 200 else []
    
    def get_album_photos(self, album_id: int) -> List[Dict]:
        """GET - Photos dari album."""
        response = self.client.get(
            f"{CONFIG.json_placeholder}/albums/{album_id}/photos",
            name="[RESOURCES] GET /albums/:id/photos"
        )
        return response.json() if response.status_code == 200 else []
    
    def list_todos(self, user_id: Optional[int] = None) -> List[Dict]:
        """GET - List todos."""
        url = f"{CONFIG.json_placeholder}/todos"
        if user_id:
            url += f"?userId={user_id}"
        response = self.client.get(url, name="[RESOURCES] GET /todos")
        return response.json() if response.status_code == 200 else []
    
    def list_colors(self) -> List[Dict]:
        """GET - List comments as alternative resource."""
        response = self.client.get(
            f"{CONFIG.json_placeholder}/comments?_limit=10",
            name="[RESOURCES] GET /comments"
        )
        return response.json() if response.status_code == 200 else []
    
    def delayed_request(self, seconds: int = 3):
        """GET - Request dengan delay using httpbin."""
        self.client.get(
            f"{CONFIG.httpbin}/delay/{seconds}",
            name=f"[RESOURCES] GET /delay/{seconds}",
            timeout=seconds + 5
        )


# ============================================
# TASK SETS (Grouped behaviors)
# ============================================
class BrowsingTasks(TaskSet):
    """Tasks untuk browsing behavior."""
    
    @tag("browse", "posts")
    @task(10)
    def browse_posts(self):
        """Browse dan baca posts."""
        posts = self.user.list_posts()
        if posts:
            post = random.choice(posts)
            self.user.get_post(post["id"])
            self.user.get_post_comments(post["id"])
    
    @tag("browse", "users")
    @task(5)
    def browse_users(self):
        """Browse users."""
        users = self.user.list_users(page=random.randint(1, 2))
        if users:
            user = random.choice(users)
            self.user.get_user(user["id"])
    
    @tag("browse", "resources")
    @task(3)
    def browse_resources(self):
        """Browse albums dan photos."""
        albums = self.user.list_albums()
        if albums:
            album = random.choice(albums[:10])
            self.user.get_album_photos(album["id"])
    
    @task(1)
    def stop(self):
        """Occasionally switch to different behavior."""
        self.interrupt()


class ContentCreationTasks(TaskSet):
    """Tasks untuk content creation."""
    
    def on_start(self):
        """Login sebelum create content."""
        self.user.login()
    
    @tag("write", "posts")
    @task(5)
    def create_and_update_post(self):
        """Create dan update post."""
        title = random.choice(POST_TITLES)
        body = f"Content created at {datetime.now().isoformat()}"
        user_id = random.randint(1, 10)
        
        result = self.user.create_post(title, body, user_id)
        if result:
            # Update post
            self.user.update_post(
                result["id"],
                f"Updated: {title}",
                f"Updated: {body}",
                user_id
            )
            # Partial update
            self.user.patch_post(result["id"], {"title": f"Final: {title}"})
    
    @tag("write", "users")
    @task(3)
    def create_user(self):
        """Create user baru."""
        self.user.create_user(
            name=f"Test User {random.randint(1000, 9999)}",
            job="Load Tester"
        )
    
    @tag("write", "posts")
    @task(2)
    def delete_post(self):
        """Delete random post."""
        self.user.delete_post(random.randint(1, 100))
    
    @task(1)
    def stop(self):
        self.interrupt()


class SearchTasks(TaskSet):
    """Tasks untuk search dan filter."""
    
    @tag("search", "posts")
    @task(5)
    def search_posts_by_user(self):
        """Filter posts by user."""
        self.user.list_posts(user_id=random.randint(1, 10))
    
    @tag("search", "todos")
    @task(4)
    def search_todos(self):
        """Get user's todos."""
        self.user.list_todos(user_id=random.randint(1, 10))
    
    @tag("search", "resources")
    @task(3)
    def search_colors(self):
        """Get colors."""
        self.user.list_colors()
    
    @task(1)
    def stop(self):
        self.interrupt()


class AdminTasks(TaskSet):
    """Tasks untuk admin operations."""
    
    def on_start(self):
        self.user.login()
    
    @tag("admin", "users")
    @task(3)
    def manage_users(self):
        """CRUD operations pada users."""
        # Create
        result = self.user.create_user("Admin Created User", "Manager")
        
        # Update
        self.user.update_user(
            random.randint(1, 12),
            "Updated User",
            "Senior Manager"
        )
        
        # Delete
        self.user.delete_user(random.randint(1, 12))
    
    @tag("admin", "posts")
    @task(2)
    def bulk_operations(self):
        """Bulk read operations."""
        for _ in range(5):
            self.user.get_post(random.randint(1, 100))
    
    @task(1)
    def stop(self):
        self.interrupt()


# ============================================
# USER CLASSES
# ============================================
class BrowsingUser(HttpUser, AuthMixin, PostsMixin, UsersMixin, ResourcesMixin):
    """User yang fokus browsing content."""
    
    weight = 5
    wait_time = between(1, 3)
    tasks = [BrowsingTasks]
    
    def on_start(self):
        logger.info(f"BrowsingUser spawned")


class ContentCreatorUser(HttpUser, AuthMixin, PostsMixin, UsersMixin, ResourcesMixin):
    """User yang aktif membuat content."""
    
    weight = 2
    wait_time = between(2, 5)
    tasks = [ContentCreationTasks]
    
    def on_start(self):
        logger.info(f"ContentCreatorUser spawned")


class SearchUser(HttpUser, AuthMixin, PostsMixin, UsersMixin, ResourcesMixin):
    """User yang fokus search dan filter."""
    
    weight = 2
    wait_time = between(1, 2)
    tasks = [SearchTasks]
    
    def on_start(self):
        logger.info(f"SearchUser spawned")


class AdminUser(HttpUser, AuthMixin, PostsMixin, UsersMixin, ResourcesMixin):
    """Admin user dengan akses penuh."""
    
    weight = 1
    wait_time = between(0.5, 1.5)
    tasks = [AdminTasks]
    
    def on_start(self):
        logger.info(f"AdminUser spawned")


class AggressiveUser(FastHttpUser, AuthMixin, PostsMixin, UsersMixin, ResourcesMixin):
    """User agresif untuk stress testing (menggunakan FastHttpUser)."""
    
    weight = 1
    wait_time = between(0.1, 0.3)
    
    @task(1)
    def rapid_fire(self):
        """Rapid requests tanpa jeda."""
        self.client.get(f"{CONFIG.json_placeholder}/posts")
        self.client.get(f"{CONFIG.json_placeholder}/users")
        self.client.get(f"{CONFIG.json_placeholder}/todos")
        self.client.get(f"{CONFIG.json_placeholder}/comments")


# ============================================
# CUSTOM LOAD SHAPES
# ============================================
class StagesLoadShape(LoadTestShape):
    """
    Custom load shape dengan multiple stages.
    
    Stages:
    1. Warm up: 0-30s, ramp to 10 users
    2. Normal load: 30s-3m, maintain 50 users
    3. Spike: 3m-4m, spike to 150 users
    4. Recovery: 4m-5m, back to 50 users
    5. Stress: 5m-7m, ramp to 200 users
    6. Cool down: 7m-8m, ramp down to 0
    """
    
    stages = [
        {"duration": 30, "users": 10, "spawn_rate": 1},
        {"duration": 180, "users": 50, "spawn_rate": 5},
        {"duration": 240, "users": 150, "spawn_rate": 20},
        {"duration": 300, "users": 50, "spawn_rate": 10},
        {"duration": 420, "users": 200, "spawn_rate": 10},
        {"duration": 480, "users": 0, "spawn_rate": 10},
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        
        return None


class DoubleWaveLoadShape(LoadTestShape):
    """
    Load shape dengan dua wave traffic.
    Simulasi traffic pattern dengan dua peak hours.
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        # Wave 1: 0-5 minutes
        if run_time < 60:
            return (int(run_time / 2), 2)  # Ramp up
        elif run_time < 180:
            return (30, 2)  # Steady
        elif run_time < 240:
            return (max(0, 30 - int((run_time - 180) / 2)), 2)  # Ramp down
        
        # Wave 2: 5-10 minutes
        elif run_time < 300:
            return (int((run_time - 240) / 1.5), 3)  # Ramp up faster
        elif run_time < 420:
            return (40, 3)  # Higher steady
        elif run_time < 480:
            return (max(0, 40 - int((run_time - 420) / 1.5)), 3)  # Ramp down
        
        return None


# ============================================
# UNTUK MENJALANKAN DENGAN CUSTOM SHAPE
# ============================================
# Uncomment salah satu untuk menggunakan custom load shape:
# 
# class CustomShapeUser(BrowsingUser):
#     """User dengan custom load shape."""
#     pass
# 
# Kemudian jalankan dengan:
# locust -f advanced_locustfile.py --class-picker

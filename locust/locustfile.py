"""
============================================
STUDI CASE: Load Testing JSONPlaceholder API
============================================

JSONPlaceholder adalah REST API dummy gratis untuk testing.
URL: https://jsonplaceholder.typicode.com

Endpoints yang di-test:
- GET /posts        - List semua posts
- GET /posts/:id    - Detail post
- POST /posts       - Create post baru
- PUT /posts/:id    - Update post
- DELETE /posts/:id - Hapus post
- GET /users        - List users
- GET /comments     - List comments dengan filter

Cara run:
    locust -f locustfile.py --host=https://jsonplaceholder.typicode.com

Dengan Web UI:
    Buka http://localhost:8089

Headless mode:
    locust -f locustfile.py --host=https://jsonplaceholder.typicode.com \
        --headless -u 100 -r 10 -t 5m
"""

import random
import json
from locust import HttpUser, task, between, tag, events
from locust.runners import MasterRunner


# ============================================
# EVENT HOOKS
# ============================================
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Dipanggil saat test dimulai."""
    print("🚀 Load test dimulai!")
    print(f"   Target: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Dipanggil saat test selesai."""
    print("✅ Load test selesai!")


# ============================================
# USER CLASSES
# ============================================
class BrowsingUser(HttpUser):
    """
    User yang fokus browsing/reading content.
    Simulasi user yang hanya melihat-lihat posts dan comments.
    """
    
    weight = 5  # 50% dari total users
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup awal saat user spawn."""
        self.post_ids = list(range(1, 101))
        self.user_ids = list(range(1, 11))
    
    @tag('read', 'posts')
    @task(5)
    def browse_posts_list(self):
        """GET - List semua posts."""
        with self.client.get("/posts", name="GET /posts", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if len(data) > 0:
                    response.success()
                else:
                    response.failure("Empty posts list")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @tag('read', 'posts')
    @task(10)
    def view_post_detail(self):
        """GET - Lihat detail post."""
        post_id = random.choice(self.post_ids)
        with self.client.get(
            f"/posts/{post_id}",
            name="GET /posts/:id",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if 'title' in data and 'body' in data:
                    response.success()
                else:
                    response.failure("Missing required fields")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @tag('read', 'comments')
    @task(5)
    def view_post_comments(self):
        """GET - Lihat comments dari post."""
        post_id = random.choice(self.post_ids)
        with self.client.get(
            f"/posts/{post_id}/comments",
            name="GET /posts/:id/comments",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @tag('read', 'users')
    @task(3)
    def view_user_profile(self):
        """GET - Lihat profile user."""
        user_id = random.choice(self.user_ids)
        self.client.get(f"/users/{user_id}", name="GET /users/:id")
    
    @tag('read', 'users')
    @task(2)
    def browse_users_list(self):
        """GET - List semua users."""
        self.client.get("/users", name="GET /users")


class ContentCreatorUser(HttpUser):
    """
    User yang aktif membuat dan mengedit content.
    Simulasi user yang sering posting dan update.
    """
    
    weight = 2  # 20% dari total users
    wait_time = between(2, 5)
    
    def on_start(self):
        """Setup awal."""
        self.user_id = random.randint(1, 10)
        self.created_posts = []
    
    @tag('write', 'posts')
    @task(5)
    def create_post(self):
        """POST - Buat post baru."""
        payload = {
            "title": f"Locust Test Post #{random.randint(1000, 9999)}",
            "body": "Ini adalah post yang dibuat dari Locust load testing untuk studi case belajar.",
            "userId": self.user_id
        }
        
        with self.client.post(
            "/posts",
            json=payload,
            name="POST /posts",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                data = response.json()
                if 'id' in data:
                    self.created_posts.append(data['id'])
                    response.success()
                else:
                    response.failure("No ID returned")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @tag('write', 'posts')
    @task(3)
    def update_post(self):
        """PUT - Update post."""
        post_id = random.randint(1, 100)
        payload = {
            "id": post_id,
            "title": f"Updated Post #{post_id}",
            "body": "Post ini sudah di-update via Locust load testing.",
            "userId": self.user_id
        }
        
        with self.client.put(
            f"/posts/{post_id}",
            json=payload,
            name="PUT /posts/:id",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @tag('write', 'posts')
    @task(2)
    def patch_post(self):
        """PATCH - Partial update post."""
        post_id = random.randint(1, 100)
        payload = {
            "title": f"Patched Title #{random.randint(100, 999)}"
        }
        
        self.client.patch(
            f"/posts/{post_id}",
            json=payload,
            name="PATCH /posts/:id"
        )
    
    @tag('write', 'posts')
    @task(1)
    def delete_post(self):
        """DELETE - Hapus post."""
        post_id = random.randint(1, 100)
        self.client.delete(f"/posts/{post_id}", name="DELETE /posts/:id")
    
    @tag('read', 'posts')
    @task(3)
    def view_own_posts(self):
        """GET - Lihat posts milik sendiri."""
        self.client.get(
            f"/posts?userId={self.user_id}",
            name="GET /posts?userId=:id"
        )


class SearchUser(HttpUser):
    """
    User yang fokus mencari dan filter content.
    Simulasi user yang sering menggunakan fitur search/filter.
    """
    
    weight = 2  # 20% dari total users
    wait_time = between(1, 2)
    
    @tag('search', 'comments')
    @task(5)
    def search_comments_by_post(self):
        """GET - Filter comments berdasarkan postId."""
        post_id = random.randint(1, 100)
        with self.client.get(
            f"/comments?postId={post_id}",
            name="GET /comments?postId=:id",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Verify all comments belong to the post
                if all(c.get('postId') == post_id for c in data):
                    response.success()
                else:
                    response.failure("Filter not working correctly")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @tag('search', 'posts')
    @task(4)
    def search_posts_by_user(self):
        """GET - Filter posts berdasarkan userId."""
        user_id = random.randint(1, 10)
        self.client.get(
            f"/posts?userId={user_id}",
            name="GET /posts?userId=:id"
        )
    
    @tag('search', 'todos')
    @task(3)
    def get_user_todos(self):
        """GET - Ambil todos dari user tertentu."""
        user_id = random.randint(1, 10)
        self.client.get(
            f"/users/{user_id}/todos",
            name="GET /users/:id/todos"
        )
    
    @tag('search', 'albums')
    @task(3)
    def get_user_albums(self):
        """GET - Ambil albums dari user tertentu."""
        user_id = random.randint(1, 10)
        self.client.get(
            f"/users/{user_id}/albums",
            name="GET /users/:id/albums"
        )
    
    @tag('search', 'photos')
    @task(2)
    def get_album_photos(self):
        """GET - Ambil photos dari album tertentu."""
        album_id = random.randint(1, 100)
        self.client.get(
            f"/albums/{album_id}/photos",
            name="GET /albums/:id/photos"
        )


class AggressiveUser(HttpUser):
    """
    User dengan behavior agresif - request cepat tanpa jeda.
    Untuk stress testing.
    """
    
    weight = 1  # 10% dari total users
    wait_time = between(0.1, 0.5)  # Very short wait
    
    @tag('stress')
    @task(1)
    def rapid_requests(self):
        """Rapid fire requests untuk stress test."""
        # Batch of quick requests
        self.client.get("/posts", name="[STRESS] GET /posts")
        self.client.get(f"/posts/{random.randint(1, 100)}", name="[STRESS] GET /posts/:id")
        self.client.get(f"/users/{random.randint(1, 10)}", name="[STRESS] GET /users/:id")
        self.client.get("/comments", name="[STRESS] GET /comments")

# Lost and Found Backend (Python + MySQL)

## 1. Prerequisites
- Node.js 18+
- MySQL server running (WAMP is fine)

## 2. Setup
1. Open terminal in `backend` folder.
2. Create `.env` from `.env.example` and fill your values.
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Run migration:
   - `python migrate.py`
5. Optional: run `database/seed.sql` manually.

## 3. Run
- `python app.py`

## 4. API Routes
- `GET /api/health`
- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/items`
- `GET /api/items/:id`
- `POST /api/items` (Bearer token required)
- `POST /api/claims` (Bearer token required)
- `GET /api/users/me` (Bearer token required)
- `GET /api/users/me/stats` (Bearer token required)

## 5. Frontend Integration Notes
- Frontend API base URL is in `frontend/js/api.js`.
- Token is stored as `authToken` in localStorage after login/signup.
- `post.html` submits multipart form data to `/api/items`.

## 6. Credentials Used
- DB Host: `127.0.0.1`
- DB Port: `3306`
- DB User: `root`
- DB Password: empty
- DB Name: `maindatabase`

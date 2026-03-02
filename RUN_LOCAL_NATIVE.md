# Native System Execution Guide

This guide explains how to run the Compliance Engine directly on your host operating system (macOS/Linux) for rapid development, using Docker **only** for the FalkorDB database instance. 

This approach completely bypasses macOS Docker volume permission issues and provides instant hot-reloading for both the frontend and backend.

## Prerequisites
- **Node.js**: v20+ (`nvm use 20` or install via Homebrew `brew install node@20`)
- **Python**: 3.10+
- **Docker**: For running FalkorDB and RedisInsight.

---

## Step 1: Start FalkorDB (Docker)

You only need the database layer running in Docker. We will explicitly target the `falkordb` service from the existing compose file.

1. Open a terminal in the root `compliance_engine` directory.
2. Run FalkorDB in the background:
```bash
docker compose up -d falkordb
```
*Note: This exposes FalkorDB on `localhost:6379` directly to your host OS.*

---

## Step 2: Run the Python Backend (Native)

The backend is built with FastAPI and runs on port `5001`.

1. Open a new terminal and navigate to the `api` folder:
   ```bash
   cd api
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the Uvicorn server directly:
   ```bash
   # Ensure you are in the compliance_engine root directory when executing this so paths resolve correctly
   cd ..
   python3 api/main.py
   # Or alternatively: uvicorn api.main:app --host 0.0.0.0 --port 5001 --reload
   ```

**Backend is now running at**: `http://localhost:5001`
**API Documentation**: `http://localhost:5001/docs`

---

## Step 3: Run the React Frontend (Native)

The frontend is a Vite + React application.

1. Open a new terminal and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install Node.js dependencies:
   ```bash
   # If you use enterprise registries, ensure your .npmrc is in this folder
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

**Frontend is now running at**: `http://localhost:3001` (or whichever port Vite allocates if 3001 is busy).

---

## Environment Configuration

When running natively, the `.env` variables in your backend and frontend need to point to `localhost` rather than internal Docker service names.

### Backend Configurations (`.env` or exported variables):
The backend defaults should generally work since they assume `localhost` if not inside Docker compose, but ensure these values are set:
```env
# Point to your local native frontend
FRONTEND_URL=http://localhost:3001
# Keep database host as localhost since FalkorDB Docker maps port 6379 to your Mac
DB_HOST=127.0.0.1
DB_PORT=6379
```

### Frontend Configurations (`frontend/.env`):
Ensure the React application knows to hit the native localhost port `5001` for the API.
```env
VITE_API_URL=http://localhost:5001/api
```

---

## Troubleshooting

- **`EPERM` / `npm build` errors**: Since you are running natively on macOS now instead of inside a Docker mount, you should not encounter any Linux `node_modules` permission errors. If you do, delete the folder `rm -rf node_modules package-lock.json` and run `npm install` again.
- **Backend cannot connect to FalkorDB**: Ensure `docker ps` shows the `compliance-engine-falkordb` container is running and healthy. If it crashed, restarting the container `docker start compliance-engine-falkordb` should fix it.

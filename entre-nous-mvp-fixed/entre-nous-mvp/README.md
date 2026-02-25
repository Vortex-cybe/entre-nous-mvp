# Entre Nous — MVP (fullstack scaffold)

This repository contains:
- `backend/` FastAPI API with encrypted content storage, moderation layers, RGPD primitives
- `frontend/` simple Vite+React MVP client

## Run
Backend:
```bash
cd backend
cp .env.example .env
# IMPORTANT: set random secrets before production
docker compose up --build
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Then:
- Open `http://localhost:5173`
- Create account (email+password)
- Login, post, view feed


Backend initializes DB schema automatically on container start (alembic upgrade head).

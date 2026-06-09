# AI-Powered Multimodal Interview Behavioral Analysis System

## Overview

This repository contains a backend service and a frontend application for an AI-powered interview behavioral analysis system.

- `backend/`: Python FastAPI backend
- `frontend/`: Next.js frontend

## Getting Started

Open a terminal and navigate to the repository root:

```bash
cd "c:\Users\l\OneDrive\Documents\PROJECTS\AI-Powered Multimodal Interview Behavioral Analysis System"
```
## Activate Venv
1. Activate your Python virtual environment if needed.

.venv\Scripts\activate

## Backend

2. Change to the backend directory:

```bash
cd backend
```

2. Activate your Python virtual environment if needed.

3. Install backend dependencies (if not already installed):

```bash
pip install -r requirements.txt
```

4. Start the backend server using Uvicorn:

```bash
py -3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> If you have a `uvicorn.ini` file and want to use it, you can also run:
>
> ```bash
> uvicorn --config uvicorn.ini
> ```

## Frontend

1. Open a new terminal and change to the frontend directory:

```bash
cd frontend
```

2. Install frontend dependencies (if not already installed):

```bash
npm install
```

3. Start the frontend development server:

```bash
npm run dev
```

## Notes

- Run the backend and frontend servers in separate terminal windows.
- The frontend should be able to connect to the backend once both are running.

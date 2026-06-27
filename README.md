# Last-Minute Life Saver ⚡

An AI-powered productivity assistant built for the **Coding Ninjas AI Hackathon**. It helps users avoid missing deadlines through automated decomposition, circadian-aligned scheduling, and panic-mode triage (recovery planning).

---

## 🚀 Key Features

1.  **AI Deadline Decomposition**: Break large goals down into manageable, hour-estimated checklists via Gemini API.
2.  **Bio-Clock Scheduler**: Fit tasks into your active hours, avoiding sleep periods and adapting to Ealy Bird/Night Owl energy profiles.
3.  **Panic Button & AI Recovery Advisor**: Got distracted? Fell behind? One-click "Panic Mode" trims low-priority work, splits tasks, and reschedules remaining deliverables to rescue your deadline.
4.  **Premium Glassmorphic Dashboard**: Real-time progress tracking, interactive checkboards, and colored-coded timeline schedules.

---

## 🛠️ Tech Stack
*   **Backend**: FastAPI (Python), `google-genai` SDK, `firebase-admin`
*   **Database**: Google Cloud Firestore (NoSQL)
*   **Frontend**: React (Vite, TypeScript, Custom Vanilla CSS)
*   **Hosting**: Google Cloud Run (Backend) & Firebase Hosting (Frontend)

---

## 💻 Local Setup & Run

### 1. Backend Setup
1.  Open a terminal inside the `backend/` folder.
2.  Initialize the Python Virtual Environment:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create your environment file:
    *   Copy `.env.example` to `.env`
    *   Add your `GEMINI_API_KEY` (Get it from [Google AI Studio](https://aistudio.google.com/)).
    *   Optional: If you want to connect to a live Firebase instance, supply your service credentials file to `FIREBASE_CREDENTIALS_PATH` or set `FIRESTORE_PROJECT_ID`.
    *   *Note*: If no keys are specified, the backend will automatically launch in an **offline mock mode** for local demonstration.
5.  Start the server:
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```

### 2. Frontend Setup
The project contains a local, self-contained portable Node.js runtime inside `.node/` for seamless offline running if Node.js is not globally installed.

1.  Open a terminal inside the `frontend/` folder.
2.  Install dependencies:
    ```bash
    # If Node.js is installed globally:
    npm install
    
    # If using the portable Node.js runtime:
    $env:PATH = "D:\antigravity_project\.node\node-v20.11.1-win-x64;" + $env:PATH
    npm install
    ```
3.  Start the development server:
    ```bash
    # If Node.js is installed globally:
    npm run dev
    
    # If using the portable Node.js runtime:
    $env:PATH = "D:\antigravity_project\.node\node-v20.11.1-win-x64;" + $env:PATH
    npm run dev
    ```
4.  Open `http://localhost:5173/` in your browser.

---

## ☁️ Google Cloud Deployment

### Backend (Google Cloud Run)
1.  Build and push the docker container to Google Artifact Registry:
    ```bash
    gcloud builds submit --tag gcr.io/your-project-id/life-saver-backend ./backend
    ```
2.  Deploy to Cloud Run:
    ```bash
    gcloud run deploy life-saver-backend \
      --image gcr.io/your-project-id/life-saver-backend \
      --platform managed \
      --allow-unauthenticated \
      --set-env-vars GEMINI_API_KEY="your_api_key_here"
    ```

### Database (Firestore)
1.  Create a Cloud Firestore database in Native Mode via the GCP console under the same Project ID.
2.  No schema creation is needed; Firestore will automatically create the `users` and `deadlines` collections on first write!

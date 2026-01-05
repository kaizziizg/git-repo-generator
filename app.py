import os
import subprocess
import shutil
import tempfile
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from git import Repo

app = FastAPI(title="Git Repo Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],   # POST / GET / OPTIONS 都允許
    allow_headers=["*"],   # Content-Type / Authorization 等
)

class Contribution(BaseModel):
    date: str
    count: int
    time: str

class RepoRequest(BaseModel):
    repoName: str
    user: str
    email: str
    total: int
    contributions: List[Contribution]

def git(*args, cwd: str, env: dict | None = None):
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True)

def cleanup_temp_dir(temp_dir: str):
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@app.post("/generate-repo")
async def generate_repo(data: RepoRequest, background_tasks: BackgroundTasks):
    # 1. create unique temp folder
    base_dir = tempfile.mkdtemp()
    repo_path = os.path.join(base_dir, data.repoName)
    os.makedirs(repo_path)

    try:
        # 2. initialize Git Repository
        # set git user info
        git_cmds = []
        git_cmds.append('git init -b main')
        git_cmds.append(f'git config user.name "{data.user}"')
        git_cmds.append(f'git config user.email "{data.email}"')
        
        for entry in data.contributions:
            dt = f"{entry.date}T{entry.time}+08:00"
            for _ in range(entry.count):
                env = os.environ | {
                    "GIT_AUTHOR_DATE": dt,
                    "GIT_COMMITTER_DATE": dt,
                }
                subprocess.run(
                    ["git", "commit", "--allow-empty", "-m", "chore: contribution graph"],
                    cwd=repo_path,
                    env=env,
                    check=True,
                )

        # 4. Compress to ZIP
        zip_base_name = os.path.join(base_dir, data.repoName)
        zip_full_path = shutil.make_archive(zip_base_name, 'zip', repo_path)

        # 5. Set up a background task to delete temporary files after the response is sent.
        # background_tasks.add_task(cleanup_temp_dir, base_dir)

        return FileResponse(
            path=zip_full_path,
            filename=f"{data.repoName}.zip",
            media_type="application/zip"
        )

    except Exception as e:
        # cleanup_temp_dir(base_dir)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
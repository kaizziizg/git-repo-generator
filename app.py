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
        "",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

def git_in(repo_dir: str, *args, env: dict | None = None):
    p = subprocess.run(
        ["git", "-C", repo_dir, *args],
        env=env,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"git -C {repo_dir} {' '.join(args)} failed (code={p.returncode})\n"
            f"stdout:\n{p.stdout}\n"
            f"stderr:\n{p.stderr}\n"
        )
    return p.stdout

def cleanup_temp_dir(temp_dir: str):
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@app.post("/generate-repo")
async def generate_repo(data: RepoRequest, background_tasks: BackgroundTasks):
    base_dir = tempfile.mkdtemp()
    repo_path = os.path.join(base_dir, data.repoName)
    os.makedirs(repo_path, exist_ok=True)

    try:
        # 1) init repo (must happen before any commit)
        git_in(repo_path, "init", "-b", "main")

        # 2) sanity check: ensure it's really a git repo
        git_in(repo_path, "rev-parse", "--is-inside-work-tree")

        # 3) create commits (empty commits; no files needed)
        for entry in data.contributions:
            dt = f"{entry.date}T{entry.time}+08:00"

            for _ in range(entry.count):
                env = os.environ.copy()
                env["GIT_AUTHOR_DATE"] = dt
                env["GIT_COMMITTER_DATE"] = dt

                git_in(
                    repo_path,
                    "-c", f"user.name={data.user}",
                    "-c", f"user.email={data.email}",
                    "commit", "--allow-empty",
                    "-m", "chore: contribution graph",
                    env=env,
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
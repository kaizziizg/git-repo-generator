import os
import shutil
import tempfile
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
from git import Repo

app = FastAPI(title="Git Repo Generator")

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
        repo = Repo.init(repo_path, initial_branch='main')
        
        # set git user info
        with repo.config_writer() as cw:
            cw.set_value("user", "name", data.user).release()
            cw.set_value("user", "email", data.email).release()

        # 3. create Commits
        for entry in data.contributions:
            iso_datetime = f"{entry.date}T{entry.time}"
            
            for i in range(entry.count):
                file_name = "contribution.log"
                file_path = os.path.join(repo_path, file_name)
                
                with open(file_path, "a") as f:
                    f.write(f"Commit: {iso_datetime} seq:{i}\n")
                
                repo.index.add([file_name])
                repo.index.commit(
                    "chore: contribution graph",
                    author_date=iso_datetime,
                    commit_date=iso_datetime
                )

        # 4. Compress to ZIP
        zip_base_name = os.path.join(base_dir, data.repoName)
        zip_full_path = shutil.make_archive(zip_base_name, 'zip', repo_path)

        # 5. Set up a background task to delete temporary files after the response is sent.
        background_tasks.add_task(cleanup_temp_dir, base_dir)

        return FileResponse(
            path=zip_full_path,
            filename=f"{data.repoName}.zip",
            media_type="application/zip"
        )

    except Exception as e:
        cleanup_temp_dir(base_dir)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
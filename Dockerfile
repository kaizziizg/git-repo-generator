# syntax=docker/dockerfile:1

FROM python:3.12-slim

# 1) 安裝 git（你要用 git commit / init 一定要有）
RUN apt-get update \
  && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

# 2) 建立工作目錄
WORKDIR /app

# 3) 先裝依賴（利用 Docker layer cache）
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4) 再複製程式碼
COPY . /app

# 5) 服務埠（你程式跑 8000）
EXPOSE 8000

# 6) 用 uvicorn 啟動
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
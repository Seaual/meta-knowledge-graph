@echo off
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
cd /d D:\meta-knowledge-graph-main
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8089

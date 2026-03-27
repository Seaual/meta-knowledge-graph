@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo   Meta Knowledge Graph 一键部署
echo ==========================================

:: 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Docker 未安装
    echo 请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

:: 检查 Docker 是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo 错误: Docker 未运行
    echo 请启动 Docker Desktop
    pause
    exit /b 1
)

:: 设置端口
set PORT=8088
if not "%1"=="" set PORT=%1

echo.
echo 部署配置:
echo   - 端口: %PORT%
echo   - 镜像: danceinsophy/meta-knowledge-graph:latest
echo.

:: 拉取镜像
echo ^>^>^> 拉取 Docker 镜像...
docker pull danceinsophy/meta-knowledge-graph:latest
if errorlevel 1 (
    echo 错误: 拉取镜像失败
    pause
    exit /b 1
)

:: 停止并删除旧容器
echo ^>^>^> 停止并删除旧容器...
docker stop meta-knowledge-graph >nul 2>&1
docker rm meta-knowledge-graph >nul 2>&1

:: 创建数据目录
echo ^>^>^> 创建数据目录...
if not exist "mkg-data" mkdir mkg-data
if not exist "mkg-papers" mkdir mkg-papers

:: 启动容器
echo ^>^>^> 启动容器...
docker run -d ^
    --name meta-knowledge-graph ^
    -p %PORT%:8088 ^
    -v "%cd%\mkg-data:/app/data" ^
    -v "%cd%\mkg-papers:/app/papers" ^
    --restart unless-stopped ^
    danceinsophy/meta-knowledge-graph:latest

if errorlevel 1 (
    echo 错误: 启动容器失败
    pause
    exit /b 1
)

:: 等待服务启动
echo ^>^>^> 等待服务启动...
timeout /t 5 /nobreak >nul

echo.
echo ==========================================
echo   部署成功!
echo ==========================================
echo.
echo 访问地址: http://localhost:%PORT%
echo.
echo 常用命令:
echo   查看日志:   docker logs meta-knowledge-graph
echo   停止服务:   docker stop meta-knowledge-graph
echo   启动服务:   docker start meta-knowledge-graph
echo   删除服务:   docker rm -f meta-knowledge-graph
echo.

:: 自动打开浏览器
echo 按任意键打开浏览器访问...
pause >nul
start http://localhost:%PORT%
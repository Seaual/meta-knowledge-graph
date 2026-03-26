#!/bin/bash
# Build and push Docker image to Docker Hub

IMAGE_NAME="danceinsophy/meta-knowledge-graph"
VERSION=${1:-"latest"}

echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:${VERSION} .

if [ "$VERSION" = "latest" ]; then
    # Also tag with version number
    docker tag ${IMAGE_NAME}:latest ${IMAGE_NAME}:1.2.0
fi

echo "Pushing to Docker Hub..."
docker push ${IMAGE_NAME}:${VERSION}

if [ "$VERSION" = "latest" ]; then
    docker push ${IMAGE_NAME}:1.2.0
fi

echo "Done! Image pushed to ${IMAGE_NAME}:${VERSION}"
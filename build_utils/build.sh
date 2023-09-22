#!/bin/sh

function build() {
  BUILD_PATH="$1"
  if [[ "$BUILD_PATH" == "" ]]
  then
    echo "MISSING ARGUMENT: BUILD_PATH"
    return 1
  fi
  docker build -t "${BUILD_PATH}" "${BUILD_PATH}"
  docker run "${BUILD_PATH}"
  container_id=`docker ps --last 1 --format "{{.ID}}"`
  docker cp $container_id:/app/zip.zip "./${BUILD_PATH}/build.zip"
}
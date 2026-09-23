#!/usr/bin/env bash
# 打包 fatjar 并以毫秒时间戳后缀复制到项目根目录
# 用法: ./build-with-timestamp.sh
set -euo pipefail

cd "$(dirname "$0")"

./gradlew shadowJar --console=plain -q

JAR=$(ls -t build/libs/autoweld-vision-*.jar | head -1)
if [ -z "$JAR" ]; then
    echo "ERROR: 未找到构建产物 build/libs/autoweld-vision-*.jar" >&2
    exit 1
fi

TS=$(date +%Y%m%d%H%M%S%3N)
OUT="autoweld-vision-${TS}.jar"
cp "$JAR" "$OUT"
echo "OK: $OUT"

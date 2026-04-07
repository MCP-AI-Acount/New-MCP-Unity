#!/usr/bin/env bash
set -euo pipefail

UNITY_PATH="${UNITY_PATH:-/Applications/Unity/Hub/Editor/6000.2.10f1/Unity.app/Contents/MacOS/Unity}"
UNITY_LICENSE_FILE="${UNITY_LICENSE_FILE:-}"
UNITY_EMAIL="${UNITY_EMAIL:-}"
UNITY_PASSWORD="${UNITY_PASSWORD:-}"
UNITY_SERIAL="${UNITY_SERIAL:-}"
UNITY_LOG_FILE="${UNITY_LOG_FILE:-/tmp/unity-license.log}"

if [[ -n "$UNITY_LICENSE_FILE" && -f "$UNITY_LICENSE_FILE" ]]; then
  "$UNITY_PATH" -batchmode -nographics -quit -manualLicenseFile "$UNITY_LICENSE_FILE" -logFile "$UNITY_LOG_FILE"
  exit 0
fi

if [[ -n "$UNITY_EMAIL" && -n "$UNITY_PASSWORD" && -n "$UNITY_SERIAL" ]]; then
  "$UNITY_PATH" -batchmode -nographics -quit -username "$UNITY_EMAIL" -password "$UNITY_PASSWORD" -serial "$UNITY_SERIAL" -logFile "$UNITY_LOG_FILE"
  exit 0
fi

echo "UNITY_LICENSE_FILE 또는 UNITY_EMAIL/UNITY_PASSWORD/UNITY_SERIAL 필요"
exit 1

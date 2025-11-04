#!/bin/sh
set -eu

PROP_DEFAULT="0.125"
MAX_BYTES_DEFAULT="4096MB"

PROP="${REDIS_MAX_MEMORY_PROPORTION:-$PROP_DEFAULT}"
MAX_BYTES_RAW="${REDIS_MAX_MEMORY_BYTES:-${MAX_BYTES_DEFAULT}}"

case "$MAX_BYTES_RAW" in
  *[!0-9]*)
    NUM=$(echo "$MAX_BYTES_RAW" | sed -E 's/[^0-9.]//g')
    UNIT=$(echo "$MAX_BYTES_RAW" | sed -E 's/[0-9.]//g' | tr '[:upper:]' '[:lower:]')
    case "$UNIT" in
      gib|gb|g) MAX_BYTES=$(expr "$NUM * 1024 * 1024 * 1024") ;;
      mib|mb|m) MAX_BYTES=$(expr "$NUM * 1024 * 1024") ;;
      kib|kb|k) MAX_BYTES=$(expr "$NUM * 1024")  ;;
      b|'') MAX_BYTES="$NUM" ;;
      *) echo "Unknown unit in REDIS_MAX_MEMORY_BYTES: $UNIT" >&2; exit 1 ;;
    esac
    ;;
  *) MAX_BYTES="$MAX_BYTES_RAW" ;;
esac

TOTAL_BYTES=$( \
  if [ -f /sys/fs/cgroup/memory.max ]; then \
    MEM=$(cat /sys/fs/cgroup/memory.max); \
    [ "$MEM" != "max" ] && [ "$MEM" -lt 1000000000000 ] && echo "$MEM" && exit 0; \
  fi; \
  if [ -f /sys/fs/cgroup/memory/memory.limit_in_bytes ]; then \
    MEM=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes); \
    [ "$MEM" -lt 1000000000000 ] && echo "$MEM" && exit 0; \
  fi; \
  read LINE < /proc/meminfo; \
  set -- $LINE; \
  echo $(( $2 * 1024 )) \
)

PROP_BYTES=$(expr "$TOTAL_BYTES * $PROP")

if [ "$PROP_BYTES" -lt "$MAX_BYTES" ]; then
  USE_BYTES="$PROP_BYTES"
else
  USE_BYTES="$MAX_BYTES"
fi

USE_MB=$(($USE_BYTES/1024/1024))

echo "Detected total memory: $((TOTAL_BYTES/1024/1024))MB"
echo "Using maxmemory: $USE_MB MB (min of proportion=${PROP}, fixed=$(($MAX_BYTES/1024/1024))MB)"

exec redis-server --maxmemory "${USE_MB}mb" --maxmemory-policy allkeys-lru

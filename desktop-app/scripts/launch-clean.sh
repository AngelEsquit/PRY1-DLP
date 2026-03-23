#!/bin/bash
# Clean launch wrapper - removes snap interference for Tauri app

# Source rustup environment FIRST to get correct Rust toolchain
if [ -f "$HOME/.cargo/env" ]; then
  source "$HOME/.cargo/env"
fi

# Unset all snap-related variables completely
unset SNAP SNAP_COMMON SNAP_DATA SNAP_NAME SNAP_REVISION SNAP_VERSION \
    SNAP_ARCH SNAP_KERNEL_RELEASE SNAP_REEXEC SNAP_USER_COMMON \
    SNAP_USER_DATA SNAP_LIBRARY_PATH SNAP_CONTEXT SNAP_COOKIE

# CRITICAL: Remove snap paths entirely from PATH and library paths
export PATH="$HOME/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Override ALL library paths - SNAP PATHS MUST BE REMOVED
# Use only system libraries, explicitly exclude snap
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu"

# Find actual system glibc (not snap version)
SYSTEM_LIBC=$(find /usr/lib /lib -name "libc.so.6" -type f 2>/dev/null | grep -v snap | head -1)
SYSTEM_LIBPTHREAD=$(find /usr/lib /lib -name "libpthread.so.0" -type f 2>/dev/null | grep -v snap | head -1)

# Use proper LD_PRELOAD if found
if [ -n "$SYSTEM_LIBC" ] && [ -n "$SYSTEM_LIBPTHREAD" ]; then
  export LD_PRELOAD="$SYSTEM_LIBPTHREAD:$SYSTEM_LIBC"
  echo "[INFO] Using system libc: $SYSTEM_LIBC"
  echo "[INFO] Using system libpthread: $SYSTEM_LIBPTHREAD"
else
  echo "[WARN] Could not locate system glibc, proceeding anyway"
fi

# Disable snap/apparmor if in snap environment
if [ -d /snap ]; then
  # Try to isolate from snap environment
  export SNAP="/nonexistent"
  export SNAP_NAME="not-in-snap"
fi

export PKG_CONFIG_PATH="/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/share/pkgconfig:$PKG_CONFIG_PATH"

echo "[INFO] Environment cleaned for system glibc"
echo "[INFO] Using cargo: $(which cargo)"
echo "[INFO] Cargo version: $(cargo --version 2>&1)"

# Run Tauri dev without watcher to avoid app restarts when saving workspace data files
exec npm run tauri -- dev --no-watch "$@"

# Snap/Glibc Workaround for Tauri on Ubuntu with Snaps

## Problem

When running YALex Studio on Ubuntu systems with snap packages installed, the Tauri app fails to start with:

```
symbol lookup error: /snap/core20/current/lib/x86_64-linux-gnu/libpthread.so.0: 
undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE
```

### Root Cause

This occurs because:
1. Ubuntu snap environments include an old, incompatible version of glibc (C library) in `/snap/core20/`
2. The Tauri binary and GTK native libraries link against system glibc
3. At runtime, snap's glibc takes priority, causing symbol mismatches between the binary and loaded libraries
4. Snap-specific libraries can't find symbols they expect from the C library

This is a known issue on systems with both:
- snap packages installed (e.g., VS Code, Chromium via snap)
- Tauri 2.x with GTK-based windowing (linux)

## Solutions

### Recommended: Use Launch Script (No sudo required)

A clean launch script has been provided that sets up the correct environment:

```bash
cd desktop-app
bash scripts/launch-clean.sh
```

**What the script does:**
1. Sources rustup's Rust environment (ensures correct cargo version)
2. Unsets snap environment variables
3. Prepends system library paths to `LD_LIBRARY_PATH`
4. Uses `LD_PRELOAD` to force correct system glibc at runtime
5. Prioritizes rustup's cargo in PATH over any system installation

### Alternative: Manual Environment Setup

If you prefer not to use the script, you can run npm directly with environment overrides:

```bash
export LD_PRELOAD="/lib/x86_64-linux-gnu/libc.so.6:/lib/x86_64-linux-gnu/libpthread.so.0"
export LD_LIBRARY_PATH="/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
cd desktop-app
npm run tauri -- dev
```

### More Aggressive: Remove System Cargo (Optional)

If you have both rustup and system cargo (via `apt install cargo`), the system version may interfere:

```bash
# Check which cargo is being used first
which cargo  # Should show ~/.cargo/bin/cargo

# If system cargo exists and interferes:
# sudo mv /usr/bin/cargo /usr/bin/cargo.bak
# sudo mv /usr/bin/rustc /usr/bin/rustc.bak

# Then verify rustup is used:
cargo --version  # Should show rustup's version (1.94.0 or newer)
```

## Technical Details

### Why `LD_PRELOAD` Works

`LD_PRELOAD` forces the dynamic linker to load specific libraries first before any others. By preloading the system glibc:

```bash
LD_PRELOAD="/lib/x86_64-linux-gnu/libc.so.6:/lib/x86_64-linux-gnu/libpthread.so.0"
```

We ensure that:
- System glibc symbols are loaded first
- snap's glibc in `/snap/core20/` is bypassed
- All binaries and shared libraries use the same, compatible glibc version

### Files Involved

- `desktop-app/scripts/launch-clean.sh` - Clean environment launcher
- `desktop-app/scripts/tauri-run.mjs` - npm wrapper for Tauri CLI
- `desktop-app/package.json` - npm scripts pointing to tauri-run.mjs

### Verification

To verify the fix is working:

1. Check the yalex_studio process is running:
   ```bash
   ps aux | grep yalex_studio
   ```

2. Verify the Vite dev server responds:
   ```bash
   curl http://localhost:1420/ | head -5
   ```

3. The Tauri window should appear on your desktop (if you have a display)

## Prevention for Future Installs

If you're setting up Tauri in a new snap-equipped Ubuntu system:

1. Install system development tools BEFORE snaps when possible
2. Use rustup (official Rust installer) instead of `apt install cargo` or snap packages
3. Avoid installing rustup-provided tools via snap
4. Keep the launch script as a standard part of your development workflow

## Related Issues

- Tauri GitHub: https://github.com/tauri-apps/tauri/issues (search "glibc" or "snap")
- Ubuntu snaps and containers: Known limitation where snap provides incompatible system libraries

## Getting Help

If `bash scripts/launch-clean.sh` still doesn't work:

1. Verify `~/.cargo/env` exists and rustup is installed:
   ```bash
   cat ~/.cargo/env
   cargo --version
   ```

2. Check that native dependencies are installed:
   ```bash
   pkg-config --list-all | grep -i gtk
   ```

3. Try the manual LD_PRELOAD approach above

4. Run with verbose output to diagnose:
   ```bash
   LD_DEBUG=all bash scripts/launch-clean.sh 2>&1 | head -100
   ```


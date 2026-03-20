use serde::Serialize;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct FileNode {
    name: String,
    path: String,
    is_dir: bool,
}

fn detect_workspace_root() -> PathBuf {
    let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let name = cwd
        .file_name()
        .map(|v| v.to_string_lossy().to_string())
        .unwrap_or_default();
    if name == "desktop-app" {
        cwd.parent().map(Path::to_path_buf).unwrap_or(cwd)
    } else {
        cwd
    }
}

#[tauri::command]
fn get_workspace_root(_app: tauri::AppHandle) -> Result<String, String> {
    let root = detect_workspace_root();
    let normalized = root.canonicalize().unwrap_or(root);
    Ok(normalized.to_string_lossy().to_string())
}

#[tauri::command]
fn list_entries(path: String) -> Result<Vec<FileNode>, String> {
    let mut nodes: Vec<FileNode> = fs::read_dir(Path::new(&path))
        .map_err(|e| format!("No se pudo abrir directorio: {e}"))?
        .filter_map(Result::ok)
        .filter_map(|entry| {
            let file_type = entry.file_type().ok()?;
            Some(FileNode {
                name: entry.file_name().to_string_lossy().to_string(),
                path: entry.path().to_string_lossy().to_string(),
                is_dir: file_type.is_dir(),
            })
        })
        .collect();

    nodes.sort_by(|a, b| match (a.is_dir, b.is_dir) {
        (true, false) => std::cmp::Ordering::Less,
        (false, true) => std::cmp::Ordering::Greater,
        _ => a.name.to_lowercase().cmp(&b.name.to_lowercase()),
    });

    Ok(nodes)
}

#[tauri::command]
fn read_text_file(path: String) -> Result<String, String> {
    fs::read_to_string(Path::new(&path)).map_err(|e| format!("Error leyendo archivo: {e}"))
}

#[tauri::command]
fn write_text_file(path: String, content: String) -> Result<(), String> {
    fs::write(Path::new(&path), content).map_err(|e| format!("Error escribiendo archivo: {e}"))
}

#[tauri::command]
fn create_directory(path: String) -> Result<(), String> {
    fs::create_dir_all(Path::new(&path))
        .map_err(|e| format!("Error creando directorio: {e}"))
}

#[tauri::command]
fn pick_directory() -> Option<String> {
    rfd::FileDialog::new()
        .pick_folder()
        .map(|path| path.to_string_lossy().to_string())
}

fn run_python_command(program: &str, args: &[&str], payload: &str) -> Result<String, String> {
    let mut child = Command::new(program)
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("No se pudo iniciar {program}: {e}"))?;

    if let Some(stdin) = child.stdin.as_mut() {
        stdin
            .write_all(payload.as_bytes())
            .map_err(|e| format!("No se pudo escribir en stdin: {e}"))?;
    }

    let output = child
        .wait_with_output()
        .map_err(|e| format!("Error esperando proceso Python: {e}"))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        Err(format!(
            "Bridge Python falló (status {:?}): {} {}",
            output.status.code(),
            stderr,
            stdout
        ))
    }
}

#[tauri::command]
fn run_yalex_bridge(payload_json: String) -> Result<String, String> {
    let script = detect_workspace_root().join("src").join("bridge_cli.py");
    let script_str = script
        .to_str()
        .ok_or_else(|| "Ruta de bridge inválida".to_string())?;

    let first_try = run_python_command("python", &[script_str], &payload_json);
    if let Ok(ok) = first_try {
        return Ok(ok);
    }

    // Fallback común en Windows: py -3
    run_python_command("py", &["-3", script_str], &payload_json)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_workspace_root,
            list_entries,
            read_text_file,
            write_text_file,
            create_directory,
            pick_directory,
            run_yalex_bridge
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

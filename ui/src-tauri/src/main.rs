// Tauri shell for the mdtx workbench.
//
// Responsibilities:
// 1. pick a free 127.0.0.1 port,
// 2. spawn the Python API sidecar on it (dev: the repo's .venv mdtx CLI;
//    release: the PyInstaller-built `mdtx-api` binary placed next to the app),
// 3. wait until the port accepts TCP, then expose the port to the frontend —
//    primarily via the `api_ready_state` command (race-free: the frontend
//    invokes it after mount), with an `api-ready` event as a push fallback,
// 4. kill the sidecar when the app exits; the sidecar additionally watches
//    its parent PID and self-exits if the shell dies.
//
// Spawn failures must NOT panic (that would show a blank window); the shell
// emits `api-error` instead and the UI renders a connection-lost screen.

use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{Emitter, Manager};

/// Port of the sidecar once it accepts connections; None until then.
struct ApiPort(Mutex<Option<u16>>);

#[tauri::command]
fn api_ready_state(port: tauri::State<ApiPort>) -> Option<u16> {
    *port.0.lock().unwrap()
}

fn pick_free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .expect("bind 127.0.0.1:0")
        .local_addr()
        .expect("local addr")
        .port()
}

fn sidecar_command(port: u16) -> Result<Command, String> {
    let port_arg = port.to_string();
    #[cfg(debug_assertions)]
    {
        // ui/src-tauri -> ui -> repo root
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let repo = manifest
            .parent()
            .and_then(|p| p.parent())
            .ok_or("cannot locate repo root")?
            .to_path_buf();
        let mut command = Command::new(repo.join(".venv/bin/mdtx"));
        command
            .args(["--ui-port", &port_arg, "--ui-headless"])
            .current_dir(repo);
        Ok(command)
    }
    #[cfg(not(debug_assertions))]
    {
        let exe = std::env::current_exe()
            .expect("current exe")
            .parent()
            .expect("exe dir")
            .join("mdtx-api");
        let mut command = Command::new(exe);
        command.args([
            "--port",
            &port_arg,
            "--parent-pid",
            &std::process::id().to_string(),
        ]);
        // GUI apps start with cwd=/ (read-only); run the sidecar from the
        // user's home so relative config paths (output dir, memory db)
        // resolve somewhere writable.
        let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
        command.current_dir(home);
        Ok(command)
    }
}

fn wait_for_port(port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    let target = format!("127.0.0.1:{port}");
    while Instant::now() < deadline {
        if TcpStream::connect(&target).is_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    false
}

fn kill_sidecar(sidecar: &Mutex<Option<Child>>) {
    if let Some(mut child) = sidecar.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

fn main() {
    let port = pick_free_port();

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .manage(ApiPort(Mutex::new(None)))
        .manage(Mutex::<Option<Child>>::new(None))
        .invoke_handler(tauri::generate_handler![api_ready_state])
        .setup(move |app| {
            let outcome = (|| -> Result<bool, String> {
                let mut command = sidecar_command(port)?;
                let child = command
                    .spawn()
                    .map_err(|err| format!("sidecar spawn failed: {err}"))?;
                *app.state::<Mutex<Option<Child>>>().lock().unwrap() = Some(child);
                Ok(wait_for_port(port, Duration::from_secs(60)))
            })();
            match outcome {
                Ok(true) => {
                    *app.state::<ApiPort>().0.lock().unwrap() = Some(port);
                    app.emit("api-ready", port)?;
                }
                Ok(false) => {
                    app.emit(
                        "api-error",
                        format!("后端服务未能在 60 秒内启动（端口 {port}）"),
                    )?;
                }
                Err(message) => {
                    app.emit("api-error", message)?;
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app, event| match event {
        tauri::RunEvent::Exit => {
            kill_sidecar(app.state::<Mutex<Option<Child>>>().inner());
        }
        tauri::RunEvent::WindowEvent { event: tauri::WindowEvent::Destroyed, .. } => {
            kill_sidecar(app.state::<Mutex<Option<Child>>>().inner());
        }
        _ => {}
    });
}

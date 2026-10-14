// Tauri shell for the mdtx workbench.
//
// Responsibilities:
// 1. pick a free 127.0.0.1 port,
// 2. spawn the Python API sidecar on it (dev: the repo's .venv mdtx CLI;
//    release: the PyInstaller-built `mdtx-api` binary placed next to the app),
// 3. wait until the port accepts TCP, then emit `api-ready` so the frontend
//    can point its HTTP/SSE client at the right base URL,
// 4. kill the sidecar when the app exits.
//
// Spawn failures must NOT panic (that would show a blank window); the shell
// emits `api-error` instead and the UI renders a connection-lost screen.

use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{Emitter, Manager};

struct Sidecar(Mutex<Option<Child>>);

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
        command.args(["--port", &port_arg]);
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

fn main() {
    let port = pick_free_port();

    let app = tauri::Builder::default()
        .manage(Sidecar(Mutex::new(None)))
        .setup(move |app| {
            let outcome = (|| -> Result<bool, String> {
                let mut command = sidecar_command(port)?;
                let child = command
                    .spawn()
                    .map_err(|err| format!("sidecar spawn failed: {err}"))?;
                *app.state::<Sidecar>().0.lock().unwrap() = Some(child);
                Ok(wait_for_port(port, Duration::from_secs(30)))
            })();
            match outcome {
                Ok(true) => app.emit("api-ready", port)?,
                Ok(false) => {
                    app.emit("api-error", format!("sidecar did not listen on {port} in time"))?;
                }
                Err(message) => {
                    app.emit("api-error", message)?;
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app, event| {
        if let tauri::RunEvent::Exit = event {
            if let Some(mut child) = app.state::<Sidecar>().0.lock().unwrap().take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    });
}

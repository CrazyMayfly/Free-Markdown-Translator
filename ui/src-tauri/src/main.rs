// Tauri shell for the mdtx workbench.
//
// Responsibilities:
// 1. pick a free 127.0.0.1 port,
// 2. spawn the Python API sidecar on it (dev: the repo's .venv mdtx CLI;
//    release: the PyInstaller-built `mdtx-api` binary placed next to the app),
// 3. wait until the port accepts TCP, then emit `api-ready` so the frontend
//    can point its HTTP/SSE client at the right base URL,
// 4. kill the sidecar when the app exits.

use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::time::{Duration, Instant};
use tauri::Emitter;

fn pick_free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .expect("bind 127.0.0.1:0")
        .local_addr()
        .expect("local addr")
        .port()
}

fn spawn_api(port: u16) -> Child {
    let port_arg = port.to_string();
    #[cfg(debug_assertions)]
    {
        // ui/src-tauri -> ui -> repo root
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let repo = manifest
            .parent()
            .and_then(|p| p.parent())
            .expect("repo root")
            .to_path_buf();
        Command::new(repo.join(".venv/bin/mdtx"))
            .args(["--ui-port", &port_arg, "--ui-headless"])
            .current_dir(repo)
            .spawn()
            .expect("spawn mdtx API (dev)")
    }
    #[cfg(not(debug_assertions))]
    {
        let exe = std::env::current_exe()
            .expect("current exe")
            .parent()
            .expect("exe dir")
            .join("mdtx-api");
        Command::new(exe)
            .args(["--port", &port_arg])
            .spawn()
            .expect("spawn mdtx API sidecar")
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
    let mut child = spawn_api(port);

    let app = tauri::Builder::default()
        .setup(move |app| {
            if wait_for_port(port, Duration::from_secs(30)) {
                app.emit("api-ready", port)?;
            } else {
                app.emit("api-error", port)?;
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(move |_app, event| {
        if let tauri::RunEvent::Exit = event {
            let _ = child.kill();
            let _ = child.wait();
        }
    });
}

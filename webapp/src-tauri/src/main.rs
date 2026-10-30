//! ZJCSAutoScript 桌面壳：双击 zjcs.exe → 后台启动配置服务（gui.py）→ 在独立窗口里打开配置界面。
//! 结构参考 NIKKEAutoScript 的 webapp/src-tauri，只保留启动、窗口和单实例。

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;

use anyhow::{Context, Result};
use backend::Backend;
use std::env;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::thread;
use tauri::webview::{NewWindowResponse, PageLoadEvent};
use tauri::{AppHandle, Manager, RunEvent, Url, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

#[cfg(windows)]
use windows::core::HSTRING;
#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONERROR, MB_OK};

struct BackendState(Mutex<Option<Backend>>);

/// 启动页还没加载完时先攒着消息，加载完再一起发过去
#[derive(Clone, Default)]
struct Reporter(Arc<Mutex<ReporterState>>);

#[derive(Default)]
struct ReporterState {
    window: Option<WebviewWindow>,
    pending: Vec<String>,
}

impl Reporter {
    fn stage(&self, text: &str) {
        self.send(format!("window.zjcsStartup && window.zjcsStartup.stage({});", json(text)));
    }

    fn error(&self, title: &str, detail: &str) {
        self.send(format!("window.zjcsStartup && window.zjcsStartup.error({}, {});", json(title), json(detail)));
    }

    fn send(&self, script: String) {
        let window = {
            let Ok(mut state) = self.0.lock() else { return };
            match &state.window {
                Some(window) => window.clone(),
                None => {
                    state.pending.push(script);
                    return;
                }
            }
        };
        let _ = window.eval(&script);
    }

    fn page_ready(&self, window: WebviewWindow) {
        let pending = {
            let Ok(mut state) = self.0.lock() else { return };
            state.window = Some(window.clone());
            std::mem::take(&mut state.pending)
        };
        for script in pending {
            let _ = window.eval(&script);
        }
    }
}

fn json(text: &str) -> String {
    serde_json::to_string(text).unwrap_or_else(|_| "\"\"".into())
}

fn show_native_message(title: &str, message: &str) {
    #[cfg(windows)]
    unsafe {
        let _ = MessageBoxW(None, &HSTRING::from(message), &HSTRING::from(title), MB_OK | MB_ICONERROR);
    }
    #[cfg(not(windows))]
    eprintln!("{title}: {message}");
}

/// 项目根目录：exe 所在目录往上找（也兼容从 target/release 里直接运行），再看当前目录
fn locate_root() -> Result<PathBuf> {
    let executable = env::current_exe().context("找不到 zjcs.exe 自己的位置")?;
    let cwd = env::current_dir().context("读不到当前目录")?;
    let candidates = executable
        .parent()
        .into_iter()
        .flat_map(|dir| dir.ancestors().take(6))
        .chain(cwd.ancestors().take(4));
    for dir in candidates {
        if dir.join("gui.py").is_file() && dir.join("zjcs.py").is_file() {
            return Ok(dir.to_path_buf());
        }
    }
    anyhow::bail!("找不到 ZJCSAutoScript 的项目目录（里面要有 gui.py 和 zjcs.py）。把 zjcs.exe 放在项目根目录里再打开。")
}

/// 只允许留在本机配置服务和内置启动页，其他链接交给系统浏览器
fn is_local_webui(url: &Url) -> bool {
    url.scheme() == "http" && url.host_str() == Some("127.0.0.1") && url.port_or_known_default() == Some(backend::PORT)
}

fn is_startup_page(url: &Url) -> bool {
    url.scheme() == "tauri" || url.host_str() == Some("tauri.localhost")
}

fn create_window(app: &AppHandle, reporter: Reporter) -> Result<WebviewWindow> {
    WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
        .title("ZJCSAutoScript")
        .inner_size(1440.0, 900.0)
        .min_inner_size(1120.0, 680.0)
        .center()
        .on_page_load(move |window, payload| {
            if payload.event() == PageLoadEvent::Finished && is_startup_page(payload.url()) {
                reporter.page_ready(window);
            }
        })
        .on_navigation(|url| {
            let allowed = is_local_webui(url) || is_startup_page(url);
            if !allowed && matches!(url.scheme(), "http" | "https") {
                let _ = open::that_detached(url.as_str());
            }
            allowed
        })
        // 页面里 target=_blank 的链接（例如错误截图原图）用系统默认程序打开
        .on_new_window(|url, _features| {
            if matches!(url.scheme(), "http" | "https") {
                let _ = open::that_detached(url.as_str());
            }
            NewWindowResponse::Deny
        })
        .build()
        .context("创建窗口失败")
}

fn start_application(app: AppHandle, window: WebviewWindow, root: PathBuf, reporter: Reporter) {
    let stage_reporter = reporter.clone();
    match backend::start_and_wait(&root, move |text| stage_reporter.stage(text)) {
        Ok(backend) => {
            if let Some(state) = app.try_state::<BackendState>() {
                if let Ok(mut current) = state.0.lock() {
                    *current = Some(backend);
                }
            }
            reporter.stage("正在打开…");
            if let Ok(url) = Url::parse(&backend::url("/")) {
                let _ = window.navigate(url);
            }
        }
        Err(error) => reporter.error(&error.title, &error.detail),
    }
}

fn run() -> Result<()> {
    let root = locate_root()?;
    let app = tauri::Builder::default()
        // 再双击 zjcs.exe 时不开第二个，把已有窗口拿到前面
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .setup(move |app| {
            app.manage(BackendState(Mutex::new(None)));
            let reporter = Reporter::default();
            let window = create_window(app.handle(), reporter.clone())?;
            let handle = app.handle().clone();
            thread::spawn(move || start_application(handle, window, root, reporter));
            Ok(())
        })
        .build(tauri::generate_context!())
        .context("桌面窗口初始化失败")?;

    app.run(|app, event| {
        if matches!(event, RunEvent::Exit) {
            if let Some(state) = app.try_state::<BackendState>() {
                if let Ok(mut backend) = state.0.lock() {
                    if let Some(mut backend) = backend.take() {
                        backend.shutdown();
                    }
                }
            }
        }
    });
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        show_native_message(
            "ZJCSAutoScript 启动失败",
            &format!(
                "{error:#}\n\n如果提示和 WebView2 有关：这台电脑缺少 Microsoft Edge WebView2 运行时（Windows 10/11 一般自带），到 https://developer.microsoft.com/microsoft-edge/webview2/ 下载「常青版运行时」装上即可。"
            ),
        );
    }
}

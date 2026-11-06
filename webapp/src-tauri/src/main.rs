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
use std::time::Duration;
use tauri::webview::{NewWindowResponse, PageLoadEvent};
use tauri::{
    AppHandle, LogicalSize, Manager, PhysicalPosition, PhysicalSize, RunEvent, State, Url, WebviewUrl, WebviewWindow,
    WebviewWindowBuilder,
};

#[cfg(windows)]
use windows::core::HSTRING;
#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONERROR, MB_OK};

struct BackendState(Mutex<Option<Backend>>);

// 完整窗口和迷你模式的尺寸（逻辑像素）。迷你模式照 300HeroAutoScript：窄高小窗贴到当前显示器工作区右侧
const FULL_SIZE: (f64, f64) = (1440.0, 900.0);
const FULL_MIN: (f64, f64) = (1120.0, 680.0);
const MINI_SIZE: (f64, f64) = (360.0, 720.0);
const MINI_MIN: (f64, f64) = (300.0, 480.0);

/// 迷你模式：进入前记下窗口位置、大小和是否最大化，还原时放回去
#[derive(Default)]
struct Compact {
    on: bool,
    saved: Option<(PhysicalPosition<i32>, PhysicalSize<u32>, bool)>,
}

struct CompactState(Mutex<Compact>);

/// Windows 去掉系统标题栏，最小化、最大化、关闭按钮画在页面顶栏里；Mac 保留红绿灯，内容延伸到标题栏下面
const FRAMELESS: bool = cfg!(windows);

fn platform() -> &'static str {
    if cfg!(windows) {
        "windows"
    } else if cfg!(target_os = "macos") {
        "macos"
    } else {
        "linux"
    }
}

/// 页面启动时问一次：哪个平台、要不要自己画窗口按钮、现在是不是迷你模式（迷你模式下刷新页面要接着用迷你布局）。
/// async：不在主线程上等锁。切迷你模式时 window_action 拿着锁调窗口方法（要主线程处理），这里在主线程等锁会互相卡死
#[tauri::command]
async fn desktop_info(state: State<'_, CompactState>) -> Result<serde_json::Value, String> {
    let compact = state.0.lock().map(|c| c.on).unwrap_or(false);
    Ok(serde_json::json!({ "platform": platform(), "frameless": FRAMELESS, "compact": compact }))
}

/// 页面顶栏的窗口按钮。async：在后台线程跑，窗口操作由 Tauri 转到主线程
#[tauri::command]
async fn window_action(window: WebviewWindow, state: State<'_, CompactState>, action: String) -> Result<(), String> {
    let result = match action.as_str() {
        "min" => window.minimize(),
        "max" => match window.is_maximized() {
            Ok(true) => window.unmaximize(),
            Ok(false) => window.maximize(),
            Err(e) => Err(e),
        },
        "close" => window.close(),
        "drag" => window.start_dragging(),
        "compact" => enter_compact(&window, &state),
        "full" => exit_compact(&window, &state),
        _ => return Err(format!("没有这个窗口操作：{action}")),
    };
    result.map_err(|e| e.to_string())
}

fn enter_compact(window: &WebviewWindow, state: &CompactState) -> tauri::Result<()> {
    let mut compact = state.0.lock().unwrap_or_else(|e| e.into_inner());
    if compact.on {
        return Ok(());
    }
    // 全屏（Mac 绿灯）下改不了大小，先退出全屏，等动画走完
    if window.is_fullscreen()? {
        window.set_fullscreen(false)?;
        thread::sleep(Duration::from_millis(800));
    }
    let maximized = window.is_maximized()?;
    if maximized {
        window.unmaximize()?;
        thread::sleep(Duration::from_millis(200));
    }
    let position = window.outer_position()?;
    let inner = window.inner_size()?;
    let outer = window.outer_size()?;
    compact.saved = Some((position, inner, maximized));
    compact.on = true;

    let scale = window.scale_factor()?;
    window.set_min_size(Some(LogicalSize::new(MINI_MIN.0, MINI_MIN.1)))?;
    let Some(monitor) = window.current_monitor()?.or(window.primary_monitor()?) else {
        return window.set_size(LogicalSize::new(MINI_SIZE.0, MINI_SIZE.1));
    };
    let area = monitor.work_area();
    // 标题栏和边框占的地方（Windows 无边框、Mac 叠加标题栏时都是 0）
    let frame_w = outer.width.saturating_sub(inner.width);
    let frame_h = outer.height.saturating_sub(inner.height);
    let width = (MINI_SIZE.0 * scale).round() as u32;
    // 屏幕太矮时不超出工作区
    let height = ((MINI_SIZE.1 * scale).round() as u32).min(area.size.height.saturating_sub(frame_h));
    window.set_size(PhysicalSize::new(width, height))?;
    let x = area.position.x + area.size.width as i32 - (width + frame_w) as i32;
    let y = area.position.y + (area.size.height as i32 - (height + frame_h) as i32) / 2;
    window.set_position(PhysicalPosition::new(x, y))
}

fn exit_compact(window: &WebviewWindow, state: &CompactState) -> tauri::Result<()> {
    let mut compact = state.0.lock().unwrap_or_else(|e| e.into_inner());
    if !compact.on {
        return Ok(());
    }
    compact.on = false;
    window.set_min_size(Some(LogicalSize::new(FULL_MIN.0, FULL_MIN.1)))?;
    match compact.saved.take() {
        Some((position, size, maximized)) => {
            window.set_size(size)?;
            window.set_position(position)?;
            if maximized {
                window.maximize()?;
            }
            Ok(())
        }
        None => {
            window.set_size(LogicalSize::new(FULL_SIZE.0, FULL_SIZE.1))?;
            window.center()
        }
    }
}

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
    #[cfg(target_os = "macos")]
    {
        // 窗口都没建起来，用系统对话框说一声
        let script = format!(
            "display dialog {} with title {} buttons {{\"好\"}} default button 1 with icon stop",
            applescript(message),
            applescript(title)
        );
        let _ = std::process::Command::new("osascript").args(["-e", &script]).status();
    }
    #[cfg(not(any(windows, target_os = "macos")))]
    eprintln!("{title}: {message}");
}

#[cfg(target_os = "macos")]
fn applescript(text: &str) -> String {
    format!("\"{}\"", text.replace('\\', "\\\\").replace('"', "\\\""))
}

/// 项目根目录：桌面壳所在目录往上找，再看当前目录。桌面壳可能在项目根目录（zjcs.exe）、
/// toolkit/（Mac 分发包的 toolkit/zjcs）或 webapp/src-tauri/target/release/（源码编译），都在往上 6 层以内
fn locate_root() -> Result<PathBuf> {
    let executable = env::current_exe().context("找不到桌面壳自己的位置")?;
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
    anyhow::bail!("找不到 ZJCSAutoScript 的项目目录（里面要有 gui.py 和 zjcs.py）。把 {} 放在项目根目录里再打开。", backend::APP_NAME)
}

/// 只允许留在本机配置服务和内置启动页，其他链接交给系统浏览器
fn is_local_webui(url: &Url) -> bool {
    url.scheme() == "http" && url.host_str() == Some("127.0.0.1") && url.port_or_known_default() == Some(backend::PORT)
}

fn is_startup_page(url: &Url) -> bool {
    url.scheme() == "tauri" || url.host_str() == Some("tauri.localhost")
}

fn create_window(app: &AppHandle, reporter: Reporter) -> Result<WebviewWindow> {
    let builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
        .title("ZJCSAutoScript")
        .inner_size(FULL_SIZE.0, FULL_SIZE.1)
        .min_inner_size(FULL_MIN.0, FULL_MIN.1)
        .center()
        .decorations(!FRAMELESS);
    // 红绿灯放到页面 52px 高的顶栏中间（关闭按钮左边距 18；y 是标题栏容器高减按钮高，11-06 实测 28 时居中）
    #[cfg(target_os = "macos")]
    let builder = builder
        .title_bar_style(tauri::TitleBarStyle::Overlay)
        .hidden_title(true)
        .traffic_light_position(tauri::LogicalPosition::new(18.0, 28.0));
    builder
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
        // 再双击桌面壳时不开第二个，把已有窗口拿到前面
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .invoke_handler(tauri::generate_handler![desktop_info, window_action])
        .setup(move |app| {
            app.manage(BackendState(Mutex::new(None)));
            app.manage(CompactState(Mutex::new(Compact::default())));
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
        #[cfg(windows)]
        let message = format!(
            "{error:#}\n\n如果提示和 WebView2 有关：这台电脑缺少 Microsoft Edge WebView2 运行时（Windows 10/11 一般自带），到 https://developer.microsoft.com/microsoft-edge/webview2/ 下载「常青版运行时」装上即可。"
        );
        #[cfg(not(windows))]
        let message = format!("{error:#}");
        show_native_message("ZJCSAutoScript 启动失败", &message);
    }
}

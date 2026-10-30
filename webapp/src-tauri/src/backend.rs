//! 配置服务（gui.py）：已经在跑就直接连，没在跑就用项目里的 Python 在后台启动它。

use std::env;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

#[cfg(windows)]
use std::os::windows::process::CommandExt;
#[cfg(windows)]
use windows::core::PCWSTR;
#[cfg(windows)]
use windows::Win32::Foundation::{CloseHandle, HANDLE};
#[cfg(windows)]
use windows::Win32::System::JobObjects::{
    AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
    SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JOB_OBJECT_LIMIT_BREAKAWAY_OK,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
};
#[cfg(windows)]
use windows::Win32::System::Threading::{OpenProcess, PROCESS_SET_QUOTA, PROCESS_TERMINATE};

/// 和 gui.py 的默认端口一致
pub const PORT: u16 = 22367;
const STARTUP_TIMEOUT: Duration = Duration::from_secs(40);

pub fn url(path: &str) -> String {
    format!("http://127.0.0.1:{PORT}{path}")
}

/// 启动失败：title 显示在启动页大标题，detail 是怎么处理和原始输出
pub struct StartError {
    pub title: String,
    pub detail: String,
}

impl StartError {
    fn new(title: impl Into<String>, detail: impl Into<String>) -> Self {
        Self { title: title.into(), detail: detail.into() }
    }
}

pub struct Backend {
    child: Option<Child>,
    #[cfg(windows)]
    job: Option<HANDLE>,
}

// HANDLE 只在退出时关闭一次，不会被多个线程同时用
unsafe impl Send for Backend {}

impl Backend {
    /// 配置服务是别处启动的（命令行、上次没关的），桌面壳退出时不去动它
    fn external() -> Self {
        Self {
            child: None,
            #[cfg(windows)]
            job: None,
        }
    }

    pub fn shutdown(&mut self) {
        // 关掉作业对象会结束 gui.py 和它没脱离作业的子进程；
        // 调度脚本启动时脱离了作业（gui.py 里的 CREATE_BREAKAWAY_FROM_JOB），关窗口它照样跑
        #[cfg(windows)]
        if let Some(job) = self.job.take() {
            unsafe {
                let _ = CloseHandle(job);
            }
        }
        if let Some(mut child) = self.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

impl Drop for Backend {
    fn drop(&mut self) {
        self.shutdown();
    }
}

/// /api/status 能正常返回才算配置服务可用（端口被别的程序占了不算）
pub fn healthy() -> bool {
    let addr: SocketAddr = ([127, 0, 0, 1], PORT).into();
    let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(500)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(3)));
    let request = format!("GET /api/status HTTP/1.0\r\nHost: 127.0.0.1:{PORT}\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut response = Vec::new();
    let _ = stream.read_to_end(&mut response);
    let text = String::from_utf8_lossy(&response);
    (text.starts_with("HTTP/1.0 200") || text.starts_with("HTTP/1.1 200")) && text.contains("\"runtime\"")
}

/// 依次找：项目的 .venv、打包时放进来的 toolkit、系统 PATH 里的 python.exe
fn find_python(root: &Path) -> Option<PathBuf> {
    let local = [root.join(".venv/Scripts/python.exe"), root.join("toolkit/python.exe")];
    if let Some(python) = local.into_iter().find(|path| path.is_file()) {
        return Some(python);
    }
    let path = env::var_os("PATH")?;
    env::split_paths(&path)
        // WindowsApps 里的 python.exe 是应用商店的占位程序，运行会弹商店
        .filter(|dir| !dir.to_string_lossy().contains("WindowsApps"))
        .map(|dir| dir.join("python.exe"))
        .find(|python| python.is_file())
}

const SETUP_HINT: &str = "准备环境：在项目目录打开终端，依次运行\n  python -m venv .venv\n  .venv\\Scripts\\python.exe -m pip install -r requirements.txt\n然后关掉这个窗口，重新打开 zjcs.exe。";

pub fn start_and_wait(root: &Path, stage: impl Fn(&str)) -> Result<Backend, StartError> {
    stage("正在连接配置服务…");
    if healthy() {
        return Ok(Backend::external());
    }
    let python = find_python(root).ok_or_else(|| {
        StartError::new(
            "这台电脑上没找到 Python 环境",
            format!("项目目录 {} 里没有 .venv 或 toolkit，系统 PATH 里也没有 python.exe。\n\n{SETUP_HINT}", root.display()),
        )
    })?;

    stage("正在启动配置服务…");
    let mut command = Command::new(&python);
    command
        .current_dir(root)
        .args(["gui.py", "--port", &PORT.to_string(), "--no-browser"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8:replace")
        .env("PYTHONUNBUFFERED", "1");
    #[cfg(windows)]
    command.creation_flags(0x08000000); // CREATE_NO_WINDOW
    let mut child = command.spawn().map_err(|error| {
        StartError::new("Python 启动不了", format!("{}\n{error}\n\n{SETUP_HINT}", python.display()))
    })?;

    // 输出要一直读走，不然管道写满会把 gui.py 卡住；最后一段留着，启动失败时显示
    let output = Arc::new(Mutex::new(String::new()));
    for pipe in [child.stdout.take().map(|p| Box::new(p) as Box<dyn Read + Send>), child.stderr.take().map(|p| Box::new(p) as Box<dyn Read + Send>)]
        .into_iter()
        .flatten()
    {
        let output = output.clone();
        thread::spawn(move || {
            let mut pipe = pipe;
            let mut buffer = [0u8; 4096];
            while let Ok(n) = pipe.read(&mut buffer) {
                if n == 0 {
                    break;
                }
                if let Ok(mut text) = output.lock() {
                    text.push_str(&String::from_utf8_lossy(&buffer[..n]));
                    if text.len() > 8000 {
                        let cut = text.len() - 6000;
                        let cut = (cut..text.len()).find(|&i| text.is_char_boundary(i)).unwrap_or(0);
                        text.drain(..cut);
                    }
                }
            }
        });
    }

    let mut backend = Backend {
        child: Some(child),
        #[cfg(windows)]
        job: None,
    };
    #[cfg(windows)]
    {
        // 桌面壳被强制结束时，系统也会顺带结束 gui.py
        backend.job = assign_kill_job(backend.child.as_ref().map(|c| c.id()).unwrap_or(0));
    }

    let started = Instant::now();
    while started.elapsed() < STARTUP_TIMEOUT {
        if healthy() {
            return Ok(backend);
        }
        if let Some(status) = backend.child.as_mut().and_then(|c| c.try_wait().ok()).flatten() {
            thread::sleep(Duration::from_millis(200));
            let text = output.lock().map(|t| t.trim().to_string()).unwrap_or_default();
            return Err(explain_exit(&python, &status.to_string(), &text));
        }
        thread::sleep(Duration::from_millis(200));
    }
    let text = output.lock().map(|t| t.trim().to_string()).unwrap_or_default();
    Err(StartError::new(
        "配置服务启动超时",
        format!("等了 {} 秒，{} 还没有响应。\n\n{}", STARTUP_TIMEOUT.as_secs(), url("/"), text),
    ))
}

fn explain_exit(python: &Path, status: &str, output: &str) -> StartError {
    let tail = format!("{}（{status}）\n\n{output}", python.display());
    if output.contains("ModuleNotFoundError") || output.contains("ImportError") {
        return StartError::new("Python 环境缺少依赖", format!("{SETUP_HINT}\n\n原始输出：\n{tail}"));
    }
    if output.contains("10048") || output.contains("Address already in use") || output.contains("只允许使用一次") {
        return StartError::new(
            format!("端口 {PORT} 被别的程序占用了"),
            format!("关掉占用 {PORT} 端口的程序后，重新打开 zjcs.exe。\n\n原始输出：\n{tail}"),
        );
    }
    StartError::new("配置服务启动失败", tail)
}

#[cfg(windows)]
fn assign_kill_job(process_id: u32) -> Option<HANDLE> {
    unsafe {
        let job = CreateJobObjectW(None, PCWSTR::null()).ok()?;
        let mut info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION::default();
        // KILL_ON_JOB_CLOSE：桌面壳退出就结束 gui.py
        // BREAKAWAY_OK：允许 gui.py 启动的调度脚本脱离作业，关窗口不影响正在跑的任务
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK;
        let configured = SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            &info as *const _ as *const _,
            std::mem::size_of_val(&info) as u32,
        );
        let process = OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, false, process_id);
        let assigned = match (configured, process) {
            (Ok(()), Ok(process)) => {
                let result = AssignProcessToJobObject(job, process);
                let _ = CloseHandle(process);
                result.is_ok()
            }
            _ => false,
        };
        if !assigned {
            let _ = CloseHandle(job);
            return None;
        }
        Some(job)
    }
}

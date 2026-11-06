fn main() {
    // 配置界面是 gui.py 的本机网页（远程地址），Tauri 只让远程页面调用在 ACL 里声明过、
    // 又在 capabilities/ 里对这个地址放行的命令。这里给两个窗口命令生成 allow-* 权限
    let manifest = tauri_build::AppManifest::new().commands(&["desktop_info", "window_action"]);
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(manifest)).expect("tauri-build 失败");
}

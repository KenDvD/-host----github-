# -*- coding: utf-8 -*-
"""
SmartHostsTool - 主程序（完美版）
- 内核：高性能优化（并发测速、自动提权、不卡顿背景）
"""

from __future__ import annotations

import concurrent.futures
import ctypes
import json
import os
import re
import ipaddress
import socket
import subprocess
import sys
import threading
from datetime import datetime
from typing import List, Tuple, Optional

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import requests
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, simpledialog, StringVar, Menu

# 导入关于界面
try:
    from about_gui_modern import AboutWindow
except ImportError:
    AboutWindow = None

# Pillow 可选（用于背景绘制）
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFilter
except Exception:
    Image = None; ImageTk = None; ImageDraw = None; ImageFilter = None

# ---------------------------------------------------------------------
# 资源路径
# ---------------------------------------------------------------------
BASE_PATH = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

def resource_path(*parts: str) -> str:
    return os.path.join(BASE_PATH, *parts)

# ---------------------------------------------------------------------
# 常量配置
# ---------------------------------------------------------------------
APP_THEME = "vapor"
GITHUB_TARGET_DOMAIN = "github.com"
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
HOSTS_START_MARK = "# === SmartHostsTool Start ==="
HOSTS_END_MARK = "# === SmartHostsTool End ==="
REMOTE_FETCH_TIMEOUT = (5, 15)

REMOTE_HOSTS_URLS = [
    "https://github-hosts.tinsfox.com/hosts",
    "https://raw.hellogithub.com/hosts",
    "https://raw.githubusercontent.com/521xueweihan/GitHub520/main/hosts",
    "https://fastly.jsdelivr.net/gh/521xueweihan/GitHub520@main/hosts",
    "https://cdn.jsdelivr.net/gh/521xueweihan/GitHub520@main/hosts",
    "https://ghproxy.com/https://raw.githubusercontent.com/521xueweihan/GitHub520/main/hosts",
    "https://gitlab.com/ineo6/hosts/-/raw/master/hosts",
]

# 保留原版详细文字
REMOTE_HOSTS_SOURCE_CHOICES = [
    ("自动（按优先级）", None),
    ("tinsfox（github-hosts.tinsfox.com）", REMOTE_HOSTS_URLS[0]),
    ("GitHub520（raw.hellogithub.com）", REMOTE_HOSTS_URLS[1]),
    ("GitHub520（raw.githubusercontent.com）", REMOTE_HOSTS_URLS[2]),
    ("GitHub520 CDN（fastly.jsdelivr.net）", REMOTE_HOSTS_URLS[3]),
    ("GitHub520 CDN（cdn.jsdelivr.net）", REMOTE_HOSTS_URLS[4]),
    ("GitHub Raw 代理（ghproxy.com）", REMOTE_HOSTS_URLS[5]),
    ("ineo6 镜像（gitlab.com）", REMOTE_HOSTS_URLS[6]),
]

# ---------------------------------------------------------------------
# 权限检查与自动提权
# ---------------------------------------------------------------------
def is_admin() -> bool:
    if sys.platform != "win32": return True
    try: return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except: return False

def check_and_elevate():
    """启动时检查并请求管理员权限"""
    if is_admin(): return True
    if sys.platform == "win32":
        try:
            # 使用5参数（SW_SHOW）代替1，确保不显示额外的控制台窗口
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 5)
            sys.exit(0)
        except Exception:
            ctypes.windll.user32.MessageBoxW(0, "需要管理员权限才能写入Hosts文件。\n请右键选择「以管理员身份运行」。", "权限不足", 0x10)
            sys.exit(1)
    return False

# ---------------------------------------------------------------------
# 玻璃背景（高性能优化 + 层级修复）
# ---------------------------------------------------------------------
class _GlassBackground:
    def __init__(self, master: ttk.Window):
        self.master = master
        self.canvas = ttk.Canvas(master, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvas.lower() # 初始沉底

        self._img = None
        self._img_id = None
        self._after_id = None
        master.bind("<Configure>", self._schedule_redraw)

    def lower(self):
        self.canvas.lower()

    def _schedule_redraw(self, _evt=None):
        if self._after_id:
            try: self.master.after_cancel(self._after_id)
            except: pass
        self._after_id = self.master.after(60, self._redraw)

    def _redraw(self):
        self._after_id = None
        w = max(640, int(self.master.winfo_width()))
        h = max(420, int(self.master.winfo_height()))

        if not (Image and ImageTk):
            self.canvas.configure(background="#0b1020")
            self.canvas.lower()
            return

        # 优化算法：生成 1xH 的渐变条，然后拉伸
        grad = Image.new("RGB", (1, h), "#0b1020")
        gpx = grad.load()
        top, mid, bot = (16, 24, 40), (17, 22, 54), (10, 14, 28)

        for y in range(h):
            t = y / max(1, h - 1)
            if t < 0.55:
                tt = t / 0.55
                r = int(top[0] + (mid[0] - top[0]) * tt)
                g = int(top[1] + (mid[1] - top[1]) * tt)
                b = int(top[2] + (mid[2] - top[2]) * tt)
            else:
                tt = (t - 0.55) / 0.45
                r = int(mid[0] + (bot[0] - mid[0]) * tt)
                g = int(mid[1] + (bot[1] - mid[1]) * tt)
                b = int(mid[2] + (bot[2] - mid[2]) * tt)
            gpx[0, y] = (r, g, b)

        img = grad.resize((w, h), resample=Image.BILINEAR)

        # 光晕
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow)
        draw.ellipse((-w * 0.3, -h * 0.4, w * 0.8, h * 0.7), fill=(56, 189, 248, 45))
        draw.ellipse((w * 0.2, h * 0.1, w * 1.2, h * 1.1), fill=(167, 139, 250, 30))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=50))
        img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
        
        # 噪点
        noise = Image.effect_noise((w, h), 20).convert("L")
        noise = noise.point(lambda v: 15 if v > 120 else 0)
        noise_rgba = Image.merge("RGBA", (noise, noise, noise, noise))
        img = Image.alpha_composite(img.convert("RGBA"), noise_rgba).convert("RGB")

        self._img = ImageTk.PhotoImage(img)
        if self._img_id is None:
            self._img_id = self.canvas.create_image(0, 0, anchor="nw", image=self._img)
        else:
            self.canvas.itemconfig(self._img_id, image=self._img)
        
        # 绘制完成后再次强制沉底
        self.canvas.lower()

# ---------------------------------------------------------------------
# 主界面
# ---------------------------------------------------------------------
class HostsOptimizer(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master, padding=0)
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

        # HTTP Session
        self._http = self._build_http_session()
        self.remote_hosts_source_url = None
        self.remote_source_url_override = None

        # 窗口属性
        self.master.title("智能 Hosts 测速工具")
        self.master.geometry("1080x680")
        self.master.minsize(980, 620)

        # 背景
        try: self._bg = _GlassBackground(self.master)
        except: pass

        # 数据初始化
        self.remote_hosts_data = []
        self.smart_resolved_ips = []
        self.custom_presets = []
        self.test_results = []
        self.presets_file = resource_path("presets.json")
        self.current_selected_presets = []
        self.is_github_selected = False
        
        # 测速相关
        self.stop_test = False
        self.executor = None
        self._stop_event = threading.Event()
        self._futures = []
        self._sort_after_id = None
        self._about = None

        self._setup_style()
        self.create_widgets()
        self.load_presets()

        # 【布局关键修复】：留出 padding 让背景透出来，lift 提升控件层级
        self.pack(fill=BOTH, expand=True, padx=15, pady=15)
        self.lift()
        if hasattr(self, "_bg"): self._bg.lower()

    def on_close(self):
        """退出清理"""
        self.stop_test = True
        self._stop_event.set()
        if self.executor:
            try: self.executor.shutdown(wait=False)
            except: pass
        self.master.destroy()
        sys.exit(0)

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
            style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
            # 透明化 Frame 背景以适配玻璃效果
            style.configure("Card.TLabelframe", background=style.colors.bg, bordercolor=style.colors.border)
            style.configure("Card.TLabelframe.Label", background=style.colors.bg, foreground=style.colors.fg)
            style.configure("Card.TFrame", background=style.colors.bg)
        except: pass

    def create_widgets(self):
        # --- App Bar ---
        appbar = ttk.Frame(self, padding=(10, 8))
        appbar.pack(fill=X)

        left = ttk.Frame(appbar)
        left.pack(side=LEFT, fill=X, expand=True)
        title = ttk.Label(left, text="智能 Hosts 测速工具", font=("Segoe UI", 18, "bold"), bootstyle="inverse-primary", padding=(14, 10))
        title.pack(side=LEFT, fill=X, expand=True)

        actions = ttk.Frame(appbar)
        actions.pack(side=RIGHT)

        self.about_btn = ttk.Button(actions, text="关于", command=self.show_about, bootstyle=INFO, width=8)
        self.about_btn.pack(side=LEFT, padx=5)

        # 源选择 - 下拉按钮
        self.remote_source_var = StringVar(value=REMOTE_HOSTS_SOURCE_CHOICES[0][0])
        self.remote_source_btn_text = StringVar()
        self.remote_source_btn_text.set(self._format_remote_source_button_text(self.remote_source_var.get()))

        self.remote_source_btn = ttk.Menubutton(actions, textvariable=self.remote_source_btn_text, bootstyle="secondary", width=15)
        self.remote_source_btn.pack(side=LEFT, padx=(12, 8))
        
        menu = Menu(self.remote_source_btn, tearoff=0)
        for label, _ in REMOTE_HOSTS_SOURCE_CHOICES:
            menu.add_radiobutton(label=label, variable=self.remote_source_var, value=label, command=self.on_source_change)
        self.remote_source_btn["menu"] = menu

        # 顶部按钮 - 保留原版文字
        self.refresh_remote_btn = ttk.Button(actions, text="刷新远程 Hosts", command=self.refresh_remote_hosts, bootstyle=SUCCESS, width=15, state=DISABLED)
        self.refresh_remote_btn.pack(side=LEFT, padx=5)
        
        self.flush_dns_btn = ttk.Button(actions, text="刷新 DNS", command=self.flush_dns, bootstyle=INFO, width=10)
        self.flush_dns_btn.pack(side=LEFT, padx=5)
        
        self.view_hosts_btn = ttk.Button(actions, text="查看 Hosts 文件", command=self.view_hosts_file, bootstyle=SECONDARY, width=12)
        self.view_hosts_btn.pack(side=LEFT, padx=5)
        
        self.start_test_btn = ttk.Button(actions, text="开始测速", command=self.start_test, bootstyle=PRIMARY, width=10, state=DISABLED)
        self.start_test_btn.pack(side=LEFT, padx=5)
        
        self.pause_test_btn = ttk.Button(actions, text="暂停测速", command=self.pause_test, bootstyle=WARNING, width=10, state=DISABLED)
        self.pause_test_btn.pack(side=LEFT, padx=5)

        # --- Body ---
        body = ttk.Frame(self)
        body.pack(fill=BOTH, expand=True, pady=(12, 0))

        paned = ttk.PanedWindow(body, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True)

        # 左侧面板
        left_panel = ttk.Frame(paned, padding=10)
        paned.add(left_panel, weight=1)
        left_card = ttk.Labelframe(left_panel, text="配置", padding=10, style="Card.TLabelframe")
        left_card.pack(fill=BOTH, expand=True)

        notebook = ttk.Notebook(left_card)
        notebook.pack(fill=BOTH, expand=True)

        # 远程Hosts页 - 保留原版文字
        self.remote_frame = ttk.Frame(notebook, padding=8)
        notebook.add(self.remote_frame, text="远程 Hosts（仅 GitHub）")
        self.remote_tree = self._create_treeview(self.remote_frame, ["ip", "domain"], ["IP 地址", "域名"], [140, 240])

        # 自定义预设页 - 保留原版文字
        self.custom_frame = ttk.Frame(notebook, padding=8)
        notebook.add(self.custom_frame, text="自定义预设")
        
        self.all_resolved_frame = ttk.Frame(notebook, padding=8)
        notebook.add(self.all_resolved_frame, text="🔍 所有解析结果")
        self.all_resolved_tree = self._create_treeview(self.all_resolved_frame, ["ip", "domain"], ["IP 地址", "域名"], [140, 240])
        
        # 自定义工具栏
        custom_toolbar = ttk.Frame(self.custom_frame)
        custom_toolbar.pack(fill=X, pady=(0, 10))
        self.add_preset_btn = ttk.Button(custom_toolbar, text="添加", command=self.add_preset, bootstyle=SUCCESS, width=8)
        self.add_preset_btn.pack(side=LEFT, padx=(0, 6))
        self.delete_preset_btn = ttk.Button(custom_toolbar, text="删除", command=self.delete_preset, bootstyle=DANGER, width=8)
        self.delete_preset_btn.pack(side=LEFT, padx=6)
        self.resolve_preset_btn = ttk.Button(custom_toolbar, text="批量解析", command=self.resolve_selected_presets, bootstyle=INFO, width=12)
        self.resolve_preset_btn.pack(side=LEFT, padx=6)

        tip = ttk.Label(self.custom_frame, text="提示：按住 Ctrl/Shift 可多选域名；选中 github.com 后可启用「刷新远程 Hosts」。", bootstyle="secondary", wraplength=320, justify=LEFT)
        tip.pack(fill=X, pady=(0, 10))

        self.preset_tree = ttk.Treeview(self.custom_frame, columns=["domain"], show="headings", height=14)
        self.preset_tree.heading("domain", text="域名")
        self.preset_tree.column("domain", width=310)
        self.preset_tree.configure(selectmode="extended")
        self.preset_tree.pack(fill=BOTH, expand=True)
        self.preset_tree.bind("<<TreeviewSelect>>", self.on_preset_select)

        # 右侧面板
        right_panel = ttk.Frame(paned, padding=10)
        paned.add(right_panel, weight=2)
        right_card = ttk.Labelframe(right_panel, text="测速结果", padding=10, style="Card.TLabelframe")
        right_card.pack(fill=BOTH, expand=True)

        # 结果列表 - 保留原版文字
        self.result_tree = ttk.Treeview(right_card, columns=["select", "ip", "domain", "delay", "status"], show="headings")
        cols = [("select", "选择", 64), ("ip", "IP 地址", 150), ("domain", "域名", 240), ("delay", "延迟 (ms)", 100), ("status", "状态", 100)]
        for c, t, w in cols:
            self.result_tree.heading(c, text=t)
            self.result_tree.column(c, width=w, anchor="center" if c=="select" else "w")
        self.result_tree.pack(fill=BOTH, expand=True, pady=(0, 10))
        self.result_tree.bind("<Button-1>", self.on_tree_click)

        action_bar = ttk.Frame(right_card)
        action_bar.pack(fill=X)
        # 底部按钮 - 保留原版文字
        self.write_best_btn = ttk.Button(action_bar, text="一键写入最优 IP", command=self.write_best_ip_to_hosts, bootstyle=SUCCESS, width=18)
        self.write_best_btn.pack(side=RIGHT, padx=(8, 0))
        self.write_selected_btn = ttk.Button(action_bar, text="写入选中到 Hosts", command=self.write_selected_to_hosts, bootstyle=PRIMARY, width=18)
        self.write_selected_btn.pack(side=RIGHT)

        # 状态栏
        statusbar = ttk.Frame(self, padding=(10, 8))
        statusbar.pack(fill=X, pady=(12, 0))
        self.progress = ttk.Progressbar(statusbar, orient=HORIZONTAL, mode="determinate")
        self.progress.pack(side=LEFT, fill=X, expand=True)
        self.status_label = ttk.Label(statusbar, text="就绪", bootstyle=INFO)
        self.status_label.pack(side=RIGHT, padx=(10, 0))

    def _create_treeview(self, parent, cols, headers, widths):
        tv = ttk.Treeview(parent, columns=cols, show="headings")
        for c, h, w in zip(cols, headers, widths):
            tv.heading(c, text=h)
            tv.column(c, width=w)
        tv.pack(fill=BOTH, expand=True)
        return tv

    # -------------------------
    # 逻辑部分
    # -------------------------
    
    # 恢复原版 Toast 弹窗方法
    def _toast(self, title: str, message: str, *, bootstyle: str = "info", duration: int = 1800):
        try:
            from ttkbootstrap.toast import ToastNotification
            ToastNotification(
                title=title,
                message=message,
                duration=duration,
                bootstyle=bootstyle,
            ).show_toast()
        except Exception:
            pass

    def _format_remote_source_button_text(self, choice_label: str) -> str:
        # 这里是唯一简化的地方：按钮上文字过长时截断
        label = (choice_label or "").strip()
        if len(label) > 16: label = label[:15] + "…"
        return f"远程源：{label} ▾"
    
    def on_source_change(self):
        c = self.remote_source_var.get()
        self.remote_source_btn_text.set(self._format_remote_source_button_text(c))
        mp = {l: u for l, u in REMOTE_HOSTS_SOURCE_CHOICES}
        self.remote_source_url_override = mp.get(c)
        if self.remote_source_url_override:
            self.status_label.config(text=f"已选择远程源：{c}", bootstyle=INFO)
        else:
            self.status_label.config(text="已选择远程源：自动（按优先级）", bootstyle=INFO)

    def show_about(self):
        if AboutWindow: 
            if self._about and self._about.window.winfo_exists(): self._about.window.lift()
            else: self._about = AboutWindow(self.master)
        else: messagebox.showinfo("关于", "SmartHostsTool\nModern Glass UI")

    def load_presets(self):
        d = ["github.com", "bitbucket.org", "bilibili.com", "baidu.com"]
        try:
            with open(self.presets_file, "r", encoding="utf-8") as f: self.custom_presets = json.load(f)
        except: self.custom_presets = d
        self.preset_tree.delete(*self.preset_tree.get_children())
        for x in self.custom_presets: self.preset_tree.insert("", "end", values=[x])

    def save_presets(self):
        try:
            with open(self.presets_file, "w", encoding="utf-8") as f: json.dump(self.custom_presets, f)
        except: pass

    def add_preset(self):
        s = simpledialog.askstring("添加预设", "请输入域名（例如：example.com）:")
        if s:
            s = s.strip().lower()
            if s not in self.custom_presets:
                self.custom_presets.append(s)
                self.preset_tree.insert("", "end", values=[s])
                self.save_presets()

    def delete_preset(self):
        sel = self.preset_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要删除的预设")
            return
        if messagebox.askyesno("确认", f"确定要删除选中的 {len(sel)} 个预设吗？"):
            for i in sel:
                v = self.preset_tree.item(i, "values")[0]
                if v in self.custom_presets: self.custom_presets.remove(v)
                self.preset_tree.delete(i)
            self.save_presets()

    def on_preset_select(self, _):
        sel = [self.preset_tree.item(i, "values")[0] for i in self.preset_tree.selection()]
        self.current_selected_presets = sel
        self.is_github_selected = GITHUB_TARGET_DOMAIN in sel
        ok = bool(sel)
        self.resolve_preset_btn.config(state=NORMAL if ok else DISABLED)
        self.refresh_remote_btn.config(state=NORMAL if self.is_github_selected else DISABLED)
        self.check_start_btn()

    def check_start_btn(self):
        ok = bool(self.remote_hosts_data or self.smart_resolved_ips)
        self.start_test_btn.config(state=NORMAL if ok else DISABLED)

    def _build_http_session(self):
        s = requests.Session()
        s.mount("https://", HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5)))
        return s

    def refresh_remote_hosts(self):
        if not self.is_github_selected: return
        self.refresh_remote_btn.config(state=DISABLED)
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        
        choice = self.remote_source_var.get()
        self.status_label.config(text=f"正在刷新远程Hosts…（源：{choice}）", bootstyle=INFO)
        threading.Thread(target=self._fetch_remote_hosts, daemon=True).start()

    def _fetch_remote_hosts(self):
        try:
            urls = [self.remote_source_url_override] if self.remote_source_url_override else REMOTE_HOSTS_URLS
            txt, u = None, None
            for url in urls:
                try:
                    r = self._http.get(url, timeout=REMOTE_FETCH_TIMEOUT)
                    # 简单校验
                    if "#" in r.text[:200] or "github" in r.text[:200].lower():
                        txt, u = r.text, url; break
                except: continue
            if not txt: raise Exception("所有远程 hosts 源均获取失败")
            
            p = re.findall(r'([\d\.]+)\s+([A-Za-z0-9.-]+)', txt)
            self.remote_hosts_data = [(ip, d) for ip, d in p if "github" in d.lower()]
            self.master.after(0, self._update_remote_hosts_ui)
        except Exception as e: 
            self.master.after(0, self.progress.stop)
            self.master.after(0, lambda: self.refresh_remote_btn.config(state=NORMAL))
            self.master.after(0, lambda: messagebox.showerror("获取失败", f"无法获取远程Hosts:\n{e}"))

    def _update_remote_hosts_ui(self):
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        self.remote_tree.delete(*self.remote_tree.get_children())
        for x in self.remote_hosts_data: self.remote_tree.insert("", "end", values=x)
        self.status_label.config(text=f"远程Hosts刷新完成，共找到 {len(self.remote_hosts_data)} 条记录", bootstyle=SUCCESS)
        self.refresh_remote_btn.config(state=NORMAL)
        self.check_start_btn()
        
        self._toast("远程 Hosts", f"刷新完成：{len(self.remote_hosts_data)} 条（{self.remote_source_var.get()}）", bootstyle="success", duration=2200)

    def resolve_selected_presets(self):
        self.resolve_preset_btn.config(state=DISABLED)
        self.status_label.config(text="正在解析IP地址...", bootstyle=INFO)
        threading.Thread(target=self._resolve_ips_thread, daemon=True).start()

    def _resolve_ips_thread(self):
        res = []
        # 优化：并发DNS解析
        with concurrent.futures.ThreadPoolExecutor(20) as ex:
            fmap = {ex.submit(socket.gethostbyname_ex, d): d for d in self.current_selected_presets}
            for f in concurrent.futures.as_completed(fmap):
                try:
                    for ip in f.result()[2]: res.append((ip, fmap[f]))
                except: pass
        self.smart_resolved_ips = res
        self.master.after(0, self._update_resolve_ui)

    def _update_resolve_ui(self):
        self.all_resolved_tree.delete(*self.all_resolved_tree.get_children())
        for x in self.smart_resolved_ips: self.all_resolved_tree.insert("", "end", values=x)
        self.status_label.config(text=f"解析完成，共找到 {len(self.smart_resolved_ips)} 个IP", bootstyle=SUCCESS)
        self.resolve_preset_btn.config(state=NORMAL)
        self.check_start_btn()

    def start_test(self):
        self.result_tree.delete(*self.result_tree.get_children())
        self.test_results = []
        data = list(set(self.remote_hosts_data + self.smart_resolved_ips))
        if not data:
             messagebox.showinfo("提示", "没有可测试的IP地址，请先解析IP或刷新远程Hosts")
             return
        
        self.start_test_btn.config(state=DISABLED)
        self.pause_test_btn.config(state=NORMAL)
        self.stop_test = False
        self._stop_event.clear()
        
        self.total_tests = len(data)
        self.completed_tests = 0
        self.progress["value"] = 0
        self.status_label.config(text=f"正在测速… 0/{self.total_tests}", bootstyle=INFO)
        
        if self.executor: self.executor.shutdown(wait=False)
        # 优化：60线程并发
        self.executor = concurrent.futures.ThreadPoolExecutor(60)
        for ip, d in data: self.executor.submit(self._test_ip_delay, ip, d)
        threading.Thread(target=self._monitor_test_completion, daemon=True).start()

    def _test_ip_delay(self, ip, domain):
        if self.stop_test: return
        ms, st = 9999, "超时"
        try:
            t = datetime.now()
            s = socket.socket()
            s.settimeout(2)
            if s.connect_ex((ip, 80)) == 0:
                ms = int((datetime.now()-t).total_seconds()*1000)
                st = "可用"
            s.close()
        except: pass
        if not self.stop_test: self.master.after(0, lambda: self._add_test_result(ip, domain, ms, st))

    def _add_test_result(self, ip, domain, delay, status):
        self.test_results.append((ip, domain, delay, status, False))
        self.completed_tests += 1
        self.progress["value"] = (self.completed_tests/self.total_tests)*100
        self.status_label.config(text=f"测速中… {self.completed_tests}/{self.total_tests}", bootstyle=INFO)
        # 节流排序，避免界面卡顿
        if not self._sort_after_id: self._sort_after_id = self.master.after(300, self._flush_sort_results)

    def _flush_sort_results(self):
        self._sort_after_id = None
        if not self.result_tree.winfo_exists(): return
        self.result_tree.delete(*self.result_tree.get_children())
        # 排序
        for ip, d, ms, st, sel in sorted(self.test_results, key=lambda x: x[2]):
            self.result_tree.insert("", "end", values=["✓" if sel else "□", ip, d, ms, st])

    def _monitor_test_completion(self):
        self.executor.shutdown(wait=True)
        self.master.after(0, lambda: self.status_label.config(text=f"测速完成，共测试 {self.total_tests} 个IP", bootstyle=SUCCESS))
        self.master.after(0, lambda: self.start_test_btn.config(state=NORMAL))
        self.master.after(0, lambda: self.pause_test_btn.config(state=DISABLED))

    def pause_test(self):
        self.stop_test = True
        self._stop_event.set()
        self.status_label.config(text="正在停止测速...", bootstyle=WARNING)

    def on_tree_click(self, event):
        if self.result_tree.identify_column(event.x) != "#1": return
        item = self.result_tree.identify_row(event.y)
        if not item: return
        v = self.result_tree.item(item, "values")
        t_ip, t_dom = v[1], v[2]
        for i, (ip, d, ms, st, s) in enumerate(self.test_results):
            if ip == t_ip and d == t_dom:
                self.test_results[i] = (ip, d, ms, st, not s)
                self.result_tree.item(item, values=["✓" if not s else "□", ip, d, ms, st])
                break

    def write_best_ip_to_hosts(self):
        best = {}
        for ip, d, ms, st, _ in self.test_results:
            if st=="可用" and (d not in best or ms < best[d][1]): best[d] = (ip, ms)
        if not best:
            messagebox.showinfo("提示", "没有可用的IP地址")
            return
        self._do_write([(ip, d) for d, (ip, _) in best.items()])

    def write_selected_to_hosts(self):
        sel = [(ip, d) for ip, d, _, _, s in self.test_results if s]
        if not sel:
            messagebox.showinfo("提示", "请先选择要写入的IP地址")
            return
        self._do_write(sel)

    def _do_write(self, lst):
        try:
            with open(HOSTS_PATH, "r", encoding="utf-8") as f: c = f.read()
            s, e = c.find(HOSTS_START_MARK), c.find(HOSTS_END_MARK)
            new_c = (c[:s] + (c[e+len(HOSTS_END_MARK):] if e!=-1 else "")) if s!=-1 else c
            blk = f"\n{HOSTS_START_MARK}\n" + "\n".join([f"{i} {d}" for i,d in lst]) + f"\n{HOSTS_END_MARK}\n"
            with open(HOSTS_PATH, "w", encoding="utf-8") as f: f.write(new_c.strip() + blk)
            self.flush_dns(silent=True)
            messagebox.showinfo("成功", f"已成功将 {len(lst)} 条记录写入Hosts文件\n建议刷新DNS使修改生效")
            self.status_label.config(text="Hosts文件已更新", bootstyle=SUCCESS)
        except Exception as e: messagebox.showerror("错误", f"写入Hosts文件失败: {e}")

    def flush_dns(self, silent=False):
        """刷新DNS缓存"""
        try: 
            # 设置subprocess参数以隐藏控制台窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run("ipconfig /flushdns", shell=True, startupinfo=startupinfo)
            if not silent: 
                messagebox.showinfo("成功", "DNS缓存已成功刷新")
                self.status_label.config(text="DNS缓存已刷新", bootstyle=SUCCESS)
        except: pass

    def view_hosts_file(self):
        try: os.startfile(HOSTS_PATH)
        except: 
            # 设置subprocess参数以隐藏控制台窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(["notepad", HOSTS_PATH], startupinfo=startupinfo)

def main():
    check_and_elevate()
    app = ttk.Window(themename=APP_THEME)
    if os.path.exists(resource_path("icon.ico")):
        try: app.iconbitmap(resource_path("icon.ico"))
        except: pass
    HostsOptimizer(app)
    app.mainloop()

if __name__ == "__main__":
    main()

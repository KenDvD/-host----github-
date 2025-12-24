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
import shutil
import re
import socket
import time
import subprocess
import sys
import threading
import statistics
from datetime import datetime
from typing import List, Tuple, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import requests
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip

# 导入自定义模块
from utils import resource_path, is_admin
from ui_components import GlassBackground
from tkinter import BooleanVar, Menu, StringVar, filedialog, messagebox, simpledialog

# 导入关于界面
try:
    from about_gui_modern import AboutWindow
except ImportError:
    AboutWindow = None

# Pillow 可选（用于背景绘制）
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFilter
except ImportError:
    Image = None; ImageTk = None; ImageDraw = None; ImageFilter = None

# Toast通知 可选
try:
    from ttkbootstrap.toast import ToastNotification
except ImportError:
    ToastNotification = None

# ---------------------------------------------------------------------
# 资源路径
# ---------------------------------------------------------------------


# ---------------------------------------------------------------------
# 常量配置
# ---------------------------------------------------------------------
APP_NAME = "SmartHostsTool"
APP_THEME = "vapor"
GITHUB_TARGET_DOMAIN = "github.com"
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
BACKUP_DIR = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'), APP_NAME, 'hosts_backups')
BACKUP_FILE_FMT = 'hosts_%Y%m%d_%H%M%S.bak'
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
    try:
        # 优先使用IsUserAnAdmin()检查，这是最可靠的方法
        if hasattr(ctypes, 'windll') and hasattr(ctypes.windll, 'shell32'):
            if ctypes.windll.shell32.IsUserAnAdmin():
                return True
    except (AttributeError, OSError, TypeError):
        pass
    
    # 如果IsUserAnAdmin()检查失败或返回False，再尝试简单的写入测试
    try:
        # 简单的写入测试，只追加一个空字符然后回退
        with open(HOSTS_PATH, 'r+b') as f:
            f.seek(0, 2)  # 移动到文件末尾
            f.write(b'\0')  # 写入一个空字符
            f.seek(-1, 2)  # 回退一个字符
            f.truncate()  # 删除刚写入的字符
        return True
    except (IOError, OSError, PermissionError):
        return False

def check_and_elevate():
    """启动时检查并请求管理员权限"""
    if is_admin():
        return True
    if sys.platform == "win32":
        try:
            # 确保使用正确的文件路径
            if getattr(sys, 'frozen', False):
                # 当程序被打包为可执行文件时
                script_path = sys.executable
                params = []
            else:
                # 当程序以脚本形式运行时
                script_path = sys.executable
                params = [__file__]
            
            # 使用ShellExecuteW请求管理员权限
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", script_path, " ".join(params), None, 5
            )
            sys.exit(0)
        except Exception as e:
            ctypes.windll.user32.MessageBoxW(
                0, "需要管理员权限才能写入Hosts文件。\n请右键选择「以管理员身份运行」。", 
                "权限不足", 0x10
            )
            sys.exit(1)
    return False

def restart_as_admin(args):
    """以管理员权限重新启动程序，并传递参数"""
    if sys.platform == "win32":
        try:
            # 确保使用正确的文件路径
            if getattr(sys, 'frozen', False):
                # 当程序被打包为可执行文件时
                script_path = sys.executable
                params = args[1:]  # 跳过第一个参数（程序名）
            else:
                # 当程序以脚本形式运行时
                script_path = sys.executable
                # 参数应该是 [脚本路径] + [其他参数]
                params = [args[0]] + args[1:]  # 保留脚本路径和所有参数
            
            # 使用ShellExecuteW请求管理员权限
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", script_path, " ".join(params), None, 5
            )
            sys.exit(0)
        except Exception as e:
            ctypes.windll.user32.MessageBoxW(
                0, "需要管理员权限才能写入Hosts文件。\n请右键选择「以管理员身份运行」。", 
                "权限不足", 0x10
            )
            sys.exit(1)
    return False

# ---------------------------------------------------------------------
# 玻璃背景（高性能优化 + 层级修复）
# ---------------------------------------------------------------------


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
        try: self._bg = GlassBackground(self.master)
        except: pass

        # 数据初始化
        self.remote_hosts_data = []
        self.smart_resolved_ips = []
        self.custom_presets = []
        self.test_results = []
        self.presets_file = resource_path("presets.json")
        self.current_selected_presets = []
        self.is_github_selected = False
        
                # Hosts 备份/回滚
        self.backup_dir = BACKUP_DIR
        self.last_backup_path = None
# 测速相关
        self.stop_test = False
        self.executor = None
        self._stop_event = threading.Event()
        self._futures = []
        self._sort_after_id = None
        self._about = None
        self.total_ip_tests = 0
        self.completed_ip_tests = 0
        self._ip_to_domains = {}
        self.icmp_fallback_var = BooleanVar(value=True)  # TCP失败时用 ICMP 补充
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


    # -------------------------
    # Treeview 美化：斑马纹 / 状态着色（不影响功能）
    # -------------------------
    def _hex_to_rgb(self, hx: str):
        hx = (hx or "").lstrip("#")
        return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return "#%02x%02x%02x" % rgb

    def _mix(self, c1: str, c2: str, t: float) -> str:
        """在 c1 和 c2 之间按比例 t（0~1）混合颜色。失败则返回 c1。"""
        try:
            if not (isinstance(c1, str) and isinstance(c2, str)):
                return c1
            if not (c1.startswith("#") and c2.startswith("#") and len(c1) == 7 and len(c2) == 7):
                return c1
            r1, g1, b1 = self._hex_to_rgb(c1)
            r2, g2, b2 = self._hex_to_rgb(c2)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            return self._rgb_to_hex((r, g, b))
        except (ValueError, TypeError):
            return c1

    def _setup_treeview_tags(self, tv: ttk.Treeview):
        """给 Treeview 加：斑马纹 + 状态色（可用/超时）。"""
        try:
            style = ttk.Style()
            bg = style.colors.bg
            fg = style.colors.fg

            # 轻微底色差（克制一些）
            row_a = self._mix(bg, fg, 0.04)
            row_b = self._mix(bg, fg, 0.07)

            tv.tag_configure("row_a", background=row_a)
            tv.tag_configure("row_b", background=row_b)

            tv.tag_configure("ok", foreground=style.colors.success)
            tv.tag_configure("bad", foreground=style.colors.danger)
        except Exception:
            # 失败不影响功能
            pass
    def _tv_insert(self, tv: ttk.Treeview, values, index: int, status: Optional[str] = None):
        tags = ["row_a" if index % 2 == 0 else "row_b"]
        if status:
            st = str(status)
            if st.startswith("可用") or "可用(ICMP)" in st:
                # 检查延迟值，超过200ms显示红色，否则绿色
                try:
                    # 延迟时间在values列表的第4个位置（索引3）
                    delay = int(values[3])
                    if delay > 200:
                        tags.append("bad")
                    else:
                        tags.append("ok")
                except (IndexError, ValueError):
                    # 如果无法获取延迟值，默认使用绿色
                    tags.append("ok")
            elif ("超时" in st) or ("不可达" in st) or ("失败" in st) or ("拒绝" in st):
                tags.append("bad")
        tv.insert("", "end", values=values, tags=tags)


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
        # 源选择 - 下拉按钮
        self.remote_source_var = StringVar(value=REMOTE_HOSTS_SOURCE_CHOICES[0][0])
        self.remote_source_btn_text = StringVar()
        self.remote_source_btn_text.set(self._format_remote_source_button_text(self.remote_source_var.get()))

        self.remote_source_btn = ttk.Menubutton(
            actions, textvariable=self.remote_source_btn_text, bootstyle="secondary", width=15
        )
        self.remote_source_btn.pack(side=LEFT, padx=(12, 8))

        menu = Menu(self.remote_source_btn, tearoff=0)
        for label, _ in REMOTE_HOSTS_SOURCE_CHOICES:
            menu.add_radiobutton(
                label=label, variable=self.remote_source_var, value=label, command=self.on_source_change
            )
        self.remote_source_btn["menu"] = menu

        # 顶部按钮（左侧：数据源 / 刷新）
        self.refresh_remote_btn = ttk.Button(
            actions, text="🔄 刷新远程 Hosts", command=self.refresh_remote_hosts,
            bootstyle=SUCCESS, width=15, state=DISABLED
        )
        self.refresh_remote_btn.pack(side=LEFT, padx=5)

        # 顶部按钮（右侧：主操作）
        self.pause_test_btn = ttk.Button(
            actions, text="⏸ 暂停测速", command=self.pause_test,
            bootstyle=WARNING, width=10, state=DISABLED
        )
        self.pause_test_btn.pack(side=RIGHT, padx=(8, 0))

        self.start_test_btn = ttk.Button(
            actions, text="▶ 开始测速", command=self.start_test,
            bootstyle=PRIMARY, width=10, state=DISABLED
        )
        self.start_test_btn.pack(side=RIGHT, padx=5)

        # 更多功能：把次要动作收起来，界面更清爽
        self.more_btn = ttk.Menubutton(actions, text="🧰 更多 ▾", bootstyle="secondary", width=10)
        self.more_btn.pack(side=RIGHT, padx=(0, 8))
        more_menu = Menu(self.more_btn, tearoff=0)
        more_menu.add_command(label="🧹刷新 DNS", command=self.flush_dns)
        more_menu.add_command(label="📄查看 Hosts 文件", command=self.view_hosts_file)
        more_menu.add_checkbutton(label="📡 TCP失败时使用ICMP补充", variable=self.icmp_fallback_var)
        more_menu.add_separator()
        more_menu.add_command(label="ℹ 关于", command=self.show_about)
        self.more_btn["menu"] = more_menu

        # ToolTip：提升成熟度（不影响功能）
        try:
            ToolTip(self.remote_source_btn, text="选择远程 hosts 数据源（默认按优先级自动选择）")
            ToolTip(self.refresh_remote_btn, text="从远程源获取 GitHub 相关 hosts 记录")
            ToolTip(self.start_test_btn, text="对当前 IP 列表进行并发测速并排序")
            ToolTip(self.pause_test_btn, text="停止当前测速任务")
            ToolTip(self.more_btn, text="更多工具：刷新 DNS / 查看 hosts / 关于")
        except Exception:
            pass

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
        notebook.add(self.remote_frame, text="🌐远程Hosts（仅 GitHub）")
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
        self.add_preset_btn = ttk.Button(custom_toolbar, text="➕ 添加", command=self.add_preset, bootstyle=SUCCESS, width=8)
        self.add_preset_btn.pack(side=LEFT, padx=(0, 6))
        self.delete_preset_btn = ttk.Button(custom_toolbar, text="🗑 删除", command=self.delete_preset, bootstyle=DANGER, width=8)
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
        self._setup_treeview_tags(self.result_tree)
        self.result_tree.bind("<Button-1>", self.on_tree_click)

        action_bar = ttk.Frame(right_card)
        action_bar.pack(fill=X)

        # 回滚 Hosts（从自动备份恢复）
        self.rollback_hosts_btn = ttk.Button(
            action_bar, text="↩ 回滚 Hosts", command=self.rollback_hosts,
            bootstyle=WARNING, width=12, state=DISABLED
        )
        self.rollback_hosts_btn.pack(side=LEFT)

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
        self._setup_treeview_tags(tv)
        return tv

    # -------------------------
    # 逻辑部分
    # -------------------------
    
    # Toast 弹窗方法
    def _toast(self, title: str, message: str, *, bootstyle: str = "info", duration: int = 1800):
        try:
            if ToastNotification:
                ToastNotification(
                    title=title,
                    message=message,
                    duration=duration,
                    bootstyle=bootstyle,
                ).show_toast()
        except Exception as e:
            # 可以选择记录错误日志
            print(f"Toast通知显示失败: {e}")

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
            self._toast("数据源切换", f"已切换到：{c}", bootstyle="info", duration=1800)
        else:
            self.status_label.config(text="已选择远程源：自动（按优先级）", bootstyle=INFO)
            self._toast("数据源切换", "已切换到：自动（按优先级）", bootstyle="info", duration=1800)

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
        for idx, x in enumerate(self.custom_presets):
            self._tv_insert(self.preset_tree, [x], idx)

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
                idx = len(self.preset_tree.get_children())
                self._tv_insert(self.preset_tree, [s], idx)
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
        for idx, x in enumerate(self.remote_hosts_data):
            self._tv_insert(self.remote_tree, x, idx)
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
        for idx, x in enumerate(self.smart_resolved_ips):
            self._tv_insert(self.all_resolved_tree, x, idx)
        self.status_label.config(text=f"解析完成，共找到 {len(self.smart_resolved_ips)} 个IP", bootstyle=SUCCESS)
        self.resolve_preset_btn.config(state=NORMAL)
        self.check_start_btn()

    def start_test(self):
        """
        开始测速（修复版）
        修复点：
        1) 进度条实时更新：不再等全部测速完成后才回填结果，而是按 as_completed() 逐个回调 UI。
        2) 结果完整：同一 IP 可能对应多个域名，改为 ip -> [domains] 的映射，避免 domain_map 覆盖导致丢失。
        3) 进度统计口径明确：按“唯一 IP 数”统计进度；结果表仍展示每个 (IP, 域名) 组合。
        """
        # 清空旧结果
        self.result_tree.delete(*self.result_tree.get_children())
        self.test_results = []

        # 合并数据源（保持原顺序），去除“完全重复的 (ip, domain)”
        raw_pairs = list(self.remote_hosts_data) + list(self.smart_resolved_ips)
        if not raw_pairs:
            messagebox.showinfo("提示", "没有可测试的IP地址，请先解析IP或刷新远程Hosts")
            return

        seen_pair = set()
        pairs = []
        for ip, dom in raw_pairs:
            key = (str(ip).strip(), str(dom).strip())
            if key in seen_pair:
                continue
            seen_pair.add(key)
            pairs.append(key)

        # 重要：同一 IP 可能对应多个域名（远程 hosts + 自定义解析会出现这种情况）
        self._ip_to_domains = {}
        for ip, dom in pairs:
            self._ip_to_domains.setdefault(ip, []).append(dom)

        # 保持 IP 的首次出现顺序
        ip_list = list(self._ip_to_domains.keys())

        # UI 状态
        self.start_test_btn.config(state=DISABLED)
        self.pause_test_btn.config(state=NORMAL)
        self.stop_test = False
        self._stop_event.clear()

        self.total_ip_tests = len(ip_list)
        self.completed_ip_tests = 0
        self.progress.configure(mode="determinate", value=0)
        self.status_label.config(text=f"正在测速… 0/{self.total_ip_tests} (IP)", bootstyle=INFO)

        # 线程池并发测速（只测唯一 IP，一次结果复用到同 IP 的多个域名）
        workers = min(60, max(1, self.total_ip_tests))
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
        self._futures = [self.executor.submit(self._speedtest_one_ip_worker, ip) for ip in ip_list]

        threading.Thread(target=self._collect_speedtest_results, daemon=True).start()

    # -----------------------------------------------------------------
    # 高性能测速：TCP 多次取中位数 + 可选 ICMP 回退
    # -----------------------------------------------------------------
    def _tcp_connect_rtt_ms(self, ip: str, port: int = 443, timeout: float = 2.0):
        """阻塞式 TCP connect 测 RTT（毫秒）。成功返回 (rtt_ms, None)，失败返回 (None, err_str)。"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(timeout)
            t0 = time.perf_counter_ns()
            err = s.connect_ex((ip, port))
            t1 = time.perf_counter_ns()
            if err != 0:
                return None, f"connect_ex_err:{err}"
            so_err = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if so_err != 0:
                return None, f"so_error:{so_err}"
            return (t1 - t0) / 1_000_000.0, None
        except socket.timeout:
            return None, "timeout"
        except Exception as e:
            return None, f"err:{e}"
        finally:
            try:
                s.close()
            except Exception:
                pass

    def _tcp_median_rtt_ms(self, ip: str, port: int = 443, attempts: int = 3, timeout: float = 2.0):
        """TCP 多次取中位数（更稳）。返回 (median_ms, ok_bool, last_err)。"""
        lat = []
        last_err = None
        for _ in range(max(1, attempts)):
            if self._stop_event.is_set() or self.stop_test:
                break
            rtt, err = self._tcp_connect_rtt_ms(ip, port=port, timeout=timeout)
            last_err = err
            if rtt is not None:
                lat.append(rtt)
            time.sleep(0.01)  # 轻微退避，降低瞬时风暴
        if lat:
            med = statistics.median(lat)
            return med, True, None
        return None, False, last_err

    def _speedtest_one_ip_worker(self, ip: str):
        """线程池工作函数：对单个 IP 测速并返回 (ip, ms, status)。"""
        if self._stop_event.is_set() or self.stop_test:
            return ip, 9999, "已停止"

        # TCP 多次取中位数
        med, ok, err = self._tcp_median_rtt_ms(
            ip,
            port=443,
            attempts=3,
            timeout=2.0
        )

        if ok and med is not None:
            ms = max(1, int(med))
            return ip, ms, "可用"

        # TCP 失败 -> 可选 ICMP 回退
        if (not ok) and self.icmp_fallback_var.get() and (not self._stop_event.is_set()) and (not self.stop_test):
            try:
                icmp_ms = self._icmp_ping_once(ip, timeout_ms=2000)
                if icmp_ms is not None:
                    return ip, icmp_ms, "可用(ICMP)"
            except Exception:
                pass

        # 失败状态分类
        if err == "timeout":
            return ip, 9999, "超时"
        return ip, 9999, "失败"

    def _collect_speedtest_results(self):
        """后台收集测速结果：按完成顺序逐个更新 UI（保证进度条实时）。"""
        try:
            for fut in concurrent.futures.as_completed(self._futures):
                if self._stop_event.is_set() or self.stop_test:
                    break
                try:
                    ip, ms, st = fut.result()
                except Exception as e:
                    ip, ms, st = "?", 9999, f"失败:{str(e)[:12]}"

                domains = self._ip_to_domains.get(ip, [""])
                # 在主线程批量插入多域名行，并把“完成 IP 数”+1
                self.master.after(
                    0,
                    lambda ip=ip, domains=domains, ms=ms, st=st: self._on_one_ip_finished(ip, domains, ms, st)
                )

            # 全部结束（或被停止）
            self.master.after(0, self._finish_speedtest_ui)
        finally:
            # 线程池清理
            if self.executor:
                try:
                    # cancel_futures 需要 Py3.9+
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    self.executor.shutdown(wait=False)
                except Exception:
                    pass

    def _on_one_ip_finished(self, ip: str, domains: List[str], ms: int, status: str):
        """主线程回调：把一个 IP 的结果展开成多行写入表格，并更新进度。"""
        if self._stop_event.is_set() or self.stop_test:
            return

        rows = [(ip, dom, ms, status) for dom in domains]
        self._add_test_results_batch(rows, ip_completed_increment=1)

    def _finish_speedtest_ui(self):
        """主线程：测速结束后的按钮/状态恢复。"""
        # 如果是手动停止，状态不同
        if self._stop_event.is_set() or self.stop_test:
            self.status_label.config(text=f"测速已停止（完成 {self.completed_ip_tests}/{self.total_ip_tests} 个IP）", bootstyle=WARNING)
        else:
            self.progress.configure(value=100)
            self.status_label.config(text=f"测速完成，共测试 {self.total_ip_tests} 个IP", bootstyle=SUCCESS)

        self.start_test_btn.config(state=NORMAL)
        self.pause_test_btn.config(state=DISABLED)

    def _test_ip_delay(self, ip, domain):
        """原测速方法保留（备用），按“单 IP 计进度”。"""
        if self._stop_event.is_set() or self.stop_test:
            return

        ms, st = 9999, "超时"
        med, ok, err = self._tcp_median_rtt_ms(ip, port=443, attempts=3, timeout=2.0)
        if ok and med is not None:
            ms = max(1, int(med))
            st = "可用"
        else:
            if self.icmp_fallback_var.get():
                try:
                    icmp_ms = self._icmp_ping_once(ip, timeout_ms=2000)
                    if icmp_ms is not None:
                        ms = icmp_ms
                        st = "可用(ICMP)"
                except Exception:
                    pass
            if st != "可用(ICMP)":
                st = "超时" if err == "timeout" else "失败"

        self.master.after(0, lambda: self._add_test_results_batch([(ip, domain, ms, st)], ip_completed_increment=1))

    def _add_test_results_batch(self, rows, ip_completed_increment: int = 0):
        """
        主线程批量写入测速结果。
        rows: [(ip, domain, delay_ms, status), ...]
        ip_completed_increment: 完成的“IP 数”增量（用于进度条）
        """
        for ip, domain, delay, status in rows:
            self.test_results.append((ip, domain, delay, status, False))

        if ip_completed_increment:
            self.completed_ip_tests += int(ip_completed_increment)
            if self.total_ip_tests:
                self.progress["value"] = (self.completed_ip_tests / self.total_ip_tests) * 100.0
            else:
                self.progress["value"] = 0
            self.status_label.config(
                text=f"测速中… {self.completed_ip_tests}/{self.total_ip_tests} (IP)",
                bootstyle=INFO
            )

        # 节流排序，避免界面卡顿
        if not self._sort_after_id:
            self._sort_after_id = self.master.after(200, self._flush_sort_results)

    def _add_test_result(self, ip, domain, delay, status):
        """兼容旧调用：单条写入（按单 IP 计进度）。"""
        self._add_test_results_batch([(ip, domain, delay, status)], ip_completed_increment=1)

    def _flush_sort_results(self):
        self._sort_after_id = None
        if not self.result_tree.winfo_exists(): return
        self.result_tree.delete(*self.result_tree.get_children())
        # 排序
        for idx, (ip, d, ms, st, sel) in enumerate(sorted(self.test_results, key=lambda x: x[2])):
            self._tv_insert(self.result_tree, ["✓" if sel else "□", ip, d, ms, st], idx, status=st)

    def pause_test(self):
        """停止当前测速任务（尽量快速释放线程池与UI状态）。"""
        self.stop_test = True
        self._stop_event.set()

        # 尽量取消未开始的任务
        if self.executor:
            try:
                self.executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                # 兼容旧版本 Python
                self.executor.shutdown(wait=False)
            except Exception:
                pass

        self.status_label.config(text="测速已请求停止…", bootstyle=WARNING)
        self.progress.stop()
        self._toast("测速暂停", "已停止/取消当前测速任务", bootstyle="warning", duration=2000)

        # UI 恢复（不等后台线程完全退出）
        self.start_test_btn.config(state=NORMAL)
        self.pause_test_btn.config(state=DISABLED)

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
            if str(st).startswith("可用") and (d not in best or ms < best[d][1]): best[d] = (ip, ms)
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

        # -----------------------------------------------------------------
    # ICMP / Ping（补充测速）
    # -----------------------------------------------------------------
    def _icmp_ping_once(self, ip: str, timeout_ms: int = 1200) -> Optional[int]:
        """Windows 下调用 ping -n 1 -w <timeout>，解析 time=xxms / 时间=xxms。
        注意：ICMP 可能被防火墙/网络策略禁用，因此仅作为补充参考。
        """
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            p = subprocess.run(
                ["ping", "-n", "1", "-w", str(int(timeout_ms)), ip],
                capture_output=True, text=True, encoding="utf-8", errors="ignore",
                startupinfo=startupinfo
            )
            out = (p.stdout or "") + "\n" + (p.stderr or "")
            m = re.search(r"(?:time|时间)[=<]\s*(\d+)\s*ms", out, re.IGNORECASE)
            if m:
                v = int(m.group(1))
                return max(1, v)
            if re.search(r"(?:time|时间)<\s*1\s*ms", out, re.IGNORECASE):
                return 1
        except Exception:
            pass
        return None

    # -----------------------------------------------------------------
    # Hosts 安全写入：自动备份 + 原子替换 + 回滚
    # -----------------------------------------------------------------
    def _ensure_backup_dir(self) -> str:
        os.makedirs(self.backup_dir, exist_ok=True)
        return self.backup_dir

    def _create_hosts_backup(self) -> str:
        """写入前自动备份 hosts。
        备份目录：%LOCALAPPDATA%\\SmartHostsTool\\hosts_backups\\
        文件名格式：hosts_YYYYMMDD_HHMMSS.bak
        """
        self._ensure_backup_dir()
        ts_name = datetime.now().strftime(BACKUP_FILE_FMT)
        bak_path = os.path.join(self.backup_dir, ts_name)
        shutil.copy2(HOSTS_PATH, bak_path)
        self.last_backup_path = bak_path
        try:
            self.rollback_hosts_btn.config(state=NORMAL)
        except Exception:
            pass
        return bak_path

    def _list_backups(self) -> List[str]:
        if not os.path.isdir(self.backup_dir):
            return []
        items = []
        for fn in os.listdir(self.backup_dir):
            if re.fullmatch(r"hosts_\d{8}_\d{6}\.bak", fn):
                items.append(os.path.join(self.backup_dir, fn))
        items.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return items

    def _latest_backup(self) -> Optional[str]:
        lst = self._list_backups()
        return lst[0] if lst else None

    def _read_hosts_text(self) -> Tuple[str, str]:
        """读取 hosts，返回 (content, encoding_used)。尽量兼容 UTF-8/UTF-8-SIG/GBK。"""
        for enc in ("utf-8-sig", "utf-8", "gbk"):
            try:
                with open(HOSTS_PATH, "r", encoding=enc) as f:
                    return f.read(), enc
            except Exception:
                continue
        with open(HOSTS_PATH, "r", errors="ignore") as f:
            return f.read(), "utf-8"

    def _write_hosts_atomic(self, text: str, encoding: str = "utf-8"):
        """原子写入：多方案备选，确保hosts文件写入成功。"""
        import tempfile
        import shutil
        import logging
        
        tmp_path = None
        hosts_tmp = None
        
        # 方案1：直接写入（最直接的方法，优先尝试）
        try:
            with open(HOSTS_PATH, "w", encoding=encoding, newline="\n") as f:
                f.write(text)
            return  # 成功，直接返回
        except Exception as e:
            logging.warning(f"方案1（直接写入）失败: {e}")
        
        # 方案2：使用系统临时目录 + shutil.copy2（避免权限问题）
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding=encoding, 
                                           newline="\n", suffix='.smarttmp', 
                                           delete=False) as f:
                f.write(text)
                tmp_path = f.name
            
            # 使用shutil.copy2复制内容（保持元数据）
            shutil.copy2(tmp_path, HOSTS_PATH)
            os.remove(tmp_path)
            return  # 成功，直接返回
        except Exception as e:
            # 清理临时文件
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            logging.warning(f"方案2（系统临时目录）失败: {e}")
        
        # 方案3：在hosts文件所在目录创建临时文件 + os.replace（最后尝试）
        try:
            hosts_tmp = HOSTS_PATH + ".smarttmp"
            with open(hosts_tmp, "w", encoding=encoding, newline="\n") as f:
                f.write(text)
            
            # 尝试os.replace（原子操作）
            os.replace(hosts_tmp, HOSTS_PATH)
            return  # 成功，直接返回
        except Exception as e:
            # 清理临时文件
            if hosts_tmp and os.path.exists(hosts_tmp):
                os.remove(hosts_tmp)
            logging.warning(f"方案3（hosts目录临时文件）失败: {e}")
        
        # 所有方法都失败，检查是否是权限问题
        # 如果是权限问题，尝试自动提权重新运行程序
        import traceback
        error_msg = traceback.format_exc()
        if "permission denied" in error_msg.lower() or "拒绝访问" in error_msg:
            self._toast("权限不足", "写入Hosts文件需要管理员权限，将自动尝试提权...", bootstyle="warning", duration=3000)
            # 保存要写入的内容到临时文件，以便重新运行后读取
            with tempfile.NamedTemporaryFile(mode='w', encoding=encoding, newline="\n", 
                                         suffix='.hostscontent', delete=False) as f:
                f.write(text)
                temp_content_path = f.name
            
            # 传递参数重新运行程序
            args = sys.argv.copy()
            args.append(f"--write-content={temp_content_path}")
            args.append(f"--encoding={encoding}")
            restart_as_admin(args)
        
        # 不是权限问题或提权失败，抛出异常
        raise PermissionError("无法写入hosts文件，尝试了多种方法均失败")

    def _remove_existing_smart_block(self, content: str) -> Tuple[str, bool]:
        """移除旧的 SmartHostsTool 标记块（Start..End），返回 (new_content, removed)。
        若仅存在 Start 或 End（标记损坏），不会做激进删除，只返回原内容并标记 removed=False。
        """
        s_idx = content.find(HOSTS_START_MARK)
        e_idx = content.find(HOSTS_END_MARK)
        if s_idx != -1 and e_idx != -1 and s_idx < e_idx:
            pat = re.compile(
                rf"{re.escape(HOSTS_START_MARK)}.*?{re.escape(HOSTS_END_MARK)}\s*",
                re.DOTALL
            )
            new_c, n = pat.subn("", content, count=1)
            return new_c, (n > 0)
        return content, False

    def rollback_hosts(self):
        """回滚按钮：默认回滚到最近一次备份；也可选择备份文件回滚。"""
        if not is_admin():
            self._toast("权限不足", "回滚Hosts文件需要管理员权限，请以管理员身份运行程序", bootstyle="warning", duration=3000)
            messagebox.showerror("权限不足", "回滚Hosts文件需要管理员权限，请以管理员身份运行程序")
            return

        latest = self._latest_backup()
        if not latest:
            messagebox.showwarning("没有备份", f"未找到备份文件\n备份目录：{self.backup_dir}")
            return

        use_latest = messagebox.askyesno("回滚 Hosts", f"是否回滚到最近备份？\n\n{latest}")
        bak_path = latest
        if not use_latest:
            bak_path = filedialog.askopenfilename(
                title="选择要回滚的备份文件",
                initialdir=self.backup_dir,
                filetypes=[("Hosts backup", "*.bak"), ("All files", "*.*")]
            )
            if not bak_path:
                return

        try:
            for enc in ("utf-8-sig", "utf-8", "gbk"):
                try:
                    with open(bak_path, "r", encoding=enc) as f:
                        bak_text = f.read()
                    used_enc = enc
                    break
                except Exception:
                    bak_text = None
                    used_enc = "utf-8"
            if bak_text is None:
                with open(bak_path, "r", errors="ignore") as f:
                    bak_text = f.read()
                used_enc = "utf-8"

            self._write_hosts_atomic(bak_text, encoding=used_enc)
            self.flush_dns(silent=True)
            messagebox.showinfo("回滚成功", f"已从备份恢复 hosts：\n{bak_path}\n\n备份目录：{self.backup_dir}")
            self.status_label.config(text="Hosts 已回滚并刷新DNS", bootstyle=SUCCESS)
        except Exception as e:
            messagebox.showerror("回滚失败", f"回滚 Hosts 失败：{e}")
    def _do_write(self, lst):
        try:
            if not is_admin():
                self._toast("提示", "当前没有管理员权限，将尝试写入Hosts文件...", bootstyle="info", duration=2000)

            # 1) 读取原 hosts + 备份
            content, enc = self._read_hosts_text()
            bak_path = self._create_hosts_backup()

            # 2) 移除旧标记块（仅当 Start/End 都存在且顺序正确时才移除）
            new_c, _removed = self._remove_existing_smart_block(content)
            if (content.find(HOSTS_START_MARK) != -1) ^ (content.find(HOSTS_END_MARK) != -1):
                self._toast(
                    "提示",
                    "检测到 Hosts 标记可能损坏（Start/End 不成对）。已采用安全写入：不删除旧段，仅追加新段。必要时可点击“回滚 Hosts”。",
                    bootstyle="warning", duration=4500
                )

            # 3) 生成新块并追加到文件末尾
            blk = (
                f"\n{HOSTS_START_MARK}\n"
                + "\n".join([f"{i} {d}" for i, d in lst])
                + f"\n{HOSTS_END_MARK}\n"
            )
            final_text = new_c.rstrip() + blk

            # 4) 原子写入（避免写到一半断电/异常导致 hosts 损坏）
            self._write_hosts_atomic(final_text, encoding=enc)

            # 5) 刷新 DNS
            self.flush_dns(silent=True)

            messagebox.showinfo(
                "成功",
                f"已成功将 {len(lst)} 条记录写入 Hosts 文件\n\n"
                f"写入前已自动备份：\n{bak_path}\n\n"
                f"备份目录：{self.backup_dir}\n"
                f"备份文件格式：hosts_YYYYMMDD_HHMMSS.bak\n\n"
                "如需恢复，请点击底部“回滚 Hosts”。"
            )
            self.status_label.config(text="Hosts文件已更新（已备份）", bootstyle=SUCCESS)
        except Exception as e:
            if "permission denied" in str(e).lower() or "拒绝访问" in str(e):
                self._toast("权限不足", "写入Hosts文件失败，请以管理员身份运行程序", bootstyle="warning", duration=3000)
                messagebox.showerror("权限不足", f"写入Hosts文件失败: {e}\n请以管理员身份运行程序")
            else:
                messagebox.showerror("错误", f"写入Hosts文件失败: {e}")

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
            else:
                # 静默模式下显示Toast通知
                self._toast("DNS刷新", "DNS缓存已成功刷新", bootstyle="success", duration=1800)
        except: pass

    def view_hosts_file(self):
        try: os.startfile(HOSTS_PATH)
        except: 
            # 设置subprocess参数以隐藏控制台窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(["notepad", HOSTS_PATH], startupinfo=startupinfo)

def main():
    import argparse
    import tempfile
    import os
    import subprocess
    
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--write-content', type=str, help='临时文件路径，包含要写入的hosts内容')
    parser.add_argument('--encoding', type=str, default='utf-8', help='文件编码')
    args = parser.parse_args()
    
    # 如果有写入内容的参数，直接执行写入操作
    if args.write_content and os.path.exists(args.write_content):
        try:
            # 读取要写入的内容
            with open(args.write_content, 'r', encoding=args.encoding) as f:
                content = f.read()
            
            # 执行原子写入
            import tempfile
            import shutil
            import logging
            import os
            
            HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
            success = False
            
            # 方案1：直接写入
            try:
                with open(HOSTS_PATH, "w", encoding=args.encoding, newline="\n") as f:
                    f.write(content)
                success = True
                print("方案1（直接写入）成功")
            except Exception as e:
                print(f"方案1（直接写入）失败: {e}")
                
                # 方案2：使用系统临时目录 + shutil.copy2
                try:
                    with tempfile.NamedTemporaryFile(mode='w', encoding=args.encoding, 
                                                   newline="\n", suffix='.smarttmp', 
                                                   delete=False) as f:
                        f.write(content)
                        tmp_path = f.name
                    
                    shutil.copy2(tmp_path, HOSTS_PATH)
                    os.remove(tmp_path)
                    success = True
                    print("方案2（系统临时目录）成功")
                except Exception as e:
                    print(f"方案2（系统临时目录）失败: {e}")
                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    
                    # 方案3：在hosts文件所在目录创建临时文件 + os.replace
                    try:
                        hosts_tmp = HOSTS_PATH + ".smarttmp"
                        with open(hosts_tmp, "w", encoding=args.encoding, newline="\n") as f:
                            f.write(content)
                        
                        os.replace(hosts_tmp, HOSTS_PATH)
                        success = True
                        print("方案3（hosts目录临时文件）成功")
                    except Exception as e:
                        print(f"方案3（hosts目录临时文件）失败: {e}")
                        if os.path.exists(hosts_tmp):
                            os.remove(hosts_tmp)
            
            if success:
                # 清理临时文件
                if os.path.exists(args.write_content):
                    os.remove(args.write_content)
                
                # 刷新DNS
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.run("ipconfig /flushdns", shell=True, startupinfo=startupinfo)
                    print("DNS缓存已刷新")
                except Exception as e:
                    print(f"刷新DNS失败: {e}")
                
                print("Hosts文件写入成功")
            else:
                print("所有写入方案都失败")
                raise PermissionError("无法写入hosts文件，尝试了多种方法均失败")
        except Exception as e:
            print(f"写入hosts文件失败: {e}")
            # 清理临时文件
            if args.write_content and os.path.exists(args.write_content):
                os.remove(args.write_content)
        finally:
            # 程序执行完毕后退出
            import sys
            sys.exit(0)
    
    # 正常启动GUI界面
    check_and_elevate()
    app = ttk.Window(themename=APP_THEME)
    if os.path.exists(resource_path("icon.ico")):
        try: app.iconbitmap(resource_path("icon.ico"))
        except: pass
    HostsOptimizer(app)
    app.mainloop()

if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""
关于窗口（Modern Glass UI, ttkbootstrap）

目标：
- 玻璃质感：渐变背景 + 卡片式信息区 + 轻透明窗口（平台支持则启用 alpha）
- 保持原有功能：打开 GitHub、展开/收起使用说明、资源路径兼容 PyInstaller
- 仍使用 Toplevel（避免第二个 Tk/mainloop）

优化内容：
- 修复了展开/收起使用说明的UI显示问题
- 添加了强制UI刷新机制
- 优化了窗口大小调整的流畅度

依赖：
- ttkbootstrap（必需）
- Pillow（可选，用于更漂亮的渐变背景/头像圆形裁剪；无 Pillow 则自动降级）
"""

from __future__ import annotations

import os
import sys
import webbrowser
from typing import Optional, Sequence

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# Pillow 可选
try:
    from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageFilter
except Exception:  # pragma: no cover
    Image = None
    ImageTk = None
    ImageOps = None
    ImageDraw = None
    ImageFilter = None


# 导入自定义模块
from utils import resource_path
from ui_components import GlassBackground


def find_first_existing(paths: Sequence[str]) -> Optional[str]:
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None





class AboutWindow:
    """
    关于窗口：作为 Toplevel 弹窗显示（不启动第二个 mainloop）
    """

    def __init__(
        self,
        master,
        *,
        app_name: str = "智能Hosts测速工具",
        version: str = "V1.6",
        author: str = "毕加索自画像",
        github_profile_url: str = "https://github.com/KenDvD",
        github_repo_url: str = "https://github.com/KenDvD/SmartHostsTool-github",
    ) -> None:
        self.master = master
        self.app_name = app_name
        self.version = version
        self.author = author
        self.github_profile_url = github_profile_url
        self.github_repo_url = github_repo_url

        self.window_width = 820
        self.window_height = 520
        self.expanded_height = 760

        self.usage_expanded = False
        self.usage_frame = None

        self.window = ttk.Toplevel(master=master, title=f"关于 · {app_name}")
        self.window.resizable(False, False)

        # 轻透明（平台支持则启用）
        try:
            self.window.attributes("-alpha", 0.98)
        except Exception:
            pass

        # 居中
        try:
            self.window.geometry(f"{self.window_width}x{self.window_height}")
            self.window.place_window_center()
        except Exception:
            sw = self.window.winfo_screenwidth()
            sh = self.window.winfo_screenheight()
            x = int(sw / 2 - self.window_width / 2)
            y = int(sh / 2 - self.window_height / 2)
            self.window.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")

        # 模态
        try:
            self.window.transient(master)
            self.window.grab_set()
            self.window.focus_set()
        except Exception:
            pass

        self._set_icon()

        # 背景
        self._bg = GlassBackground(self.window)
        self._bg.lower()

        self._build_ui()

    # -------------------------
    # Icon
    # -------------------------
    def _set_icon(self) -> None:
        ico = find_first_existing([resource_path("icon.ico"), resource_path("icon.png")])
        if not ico:
            return
        try:
            if ico.lower().endswith(".ico"):
                self.window.iconbitmap(ico)
            else:
                if ImageTk and Image:
                    img = Image.open(ico)
                    photo = ImageTk.PhotoImage(img)
                    self.window.iconphoto(False, photo)
                    self.window._icon_photo = photo  # type: ignore[attr-defined]
        except Exception:
            pass

    # -------------------------
    # UI
    # -------------------------
    def _build_ui(self) -> None:
        root = self.window

        # Style tweaks (更"卡片")
        style = ttk.Style()
        try:
            style.configure("Card.TFrame", background=style.colors.bg)
            style.configure("Card.TLabelframe", background=style.colors.bg, bordercolor=style.colors.border)
            style.configure("Card.TLabelframe.Label", background=style.colors.bg, foreground=style.colors.fg)
        except Exception:
            pass

        container = ttk.Frame(root, padding=18)
        container.pack(fill=BOTH, expand=True)

        # 顶部"应用栏"
        appbar = ttk.Frame(container)
        appbar.pack(fill=X)

        title = ttk.Label(
            appbar,
            text=self.app_name,
            font=("Segoe UI", 18, "bold"),
            bootstyle="inverse-primary",
            padding=(14, 10),
        )
        title.pack(side=LEFT, fill=X, expand=True)

        version_chip = ttk.Label(
            appbar,
            text=self.version,
            bootstyle="info",
            padding=(10, 6),
            font=("Segoe UI", 10, "bold"),
        )
        version_chip.pack(side=RIGHT, padx=(10, 0), pady=6)

        body = ttk.Frame(container)
        body.pack(fill=BOTH, expand=True, pady=(14, 0))

        # 左：头像卡片
        left = ttk.Frame(body)
        left.pack(side=LEFT, fill=Y, padx=(0, 14))

        avatar_card = ttk.Labelframe(left, text="头像", padding=(14, 12), style="Card.TLabelframe")
        avatar_card.pack(fill=X)
        self._render_avatar(avatar_card)

        # 右：信息卡片 + 提示卡片
        right = ttk.Frame(body)
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        info_card = ttk.Labelframe(right, text="项目信息", padding=(16, 14), style="Card.TLabelframe")
        info_card.pack(fill=X)

        row = ttk.Frame(info_card)
        row.pack(fill=X)
        ttk.Label(row, text="作者", font=("Segoe UI", 10), bootstyle="secondary").pack(side=LEFT)
        ttk.Label(row, text=f"  {self.author}", font=("Segoe UI", 10, "bold")).pack(side=LEFT)

        ttk.Separator(info_card).pack(fill=X, pady=10)

        ttk.Label(
            info_card,
            text="一个智能获取域名 IP 进行测速并写入 hosts 的工具（支持 GitHub 专属远程 Hosts）",
            font=("Segoe UI", 10),
            wraplength=520,
            justify=LEFT,
        ).pack(anchor=W)

        link_row = ttk.Frame(info_card)
        link_row.pack(fill=X, pady=(10, 0))

        ttk.Label(link_row, text="仓库：", font=("Segoe UI", 10), bootstyle="secondary").pack(side=LEFT)
        link = ttk.Label(
            link_row,
            text="KenDvD / SmartHostsTool-github",
            font=("Segoe UI", 10, "underline"),
            cursor="hand2",
            bootstyle="info",
        )
        link.pack(side=LEFT)
        link.bind("<Button-1>", lambda _e: self.open_repo())

        warn = ttk.Label(
            right,
            text="该工具完全开源免费！如果你买到此软件那么你被坑了。",
            font=("Segoe UI", 10, "bold"),
            bootstyle="inverse-danger",
            padding=(14, 10),
            wraplength=540,
            justify=LEFT,
        )
        warn.pack(fill=X, pady=(12, 0))

        # 使用说明容器（展开/收起）
        self.usage_container = ttk.Frame(container)
        self.usage_container.pack(fill=BOTH, expand=True, pady=(14, 0))

        # 底部按钮栏（更现代的"动作区"）
        btnbar = ttk.Frame(container)
        btnbar.pack(fill=X, pady=(12, 0))

        self.usage_btn = ttk.Button(
            btnbar,
            text="展开使用说明",
            command=self.toggle_usage,
            bootstyle="success",
            width=14,
        )
        self.usage_btn.pack(side=LEFT)

        ttk.Button(
            btnbar,
            text="打开 GitHub",
            command=self.open_repo,
            bootstyle="info-outline",
            width=12,
        ).pack(side=LEFT, padx=(10, 0))

        ttk.Button(
            btnbar,
            text="确定",
            command=self.close,
            bootstyle="primary",
            width=10,
        ).pack(side=RIGHT)

        root.bind("<Escape>", lambda _e: self.close())

    # -------------------------
    # Avatar
    # -------------------------
    def _render_avatar(self, parent) -> None:
        avatar_path = resource_path("头像.jpg")

        if not (avatar_path and Image and ImageTk and ImageOps and ImageDraw):
            ttk.Label(parent, text="🤖", font=("Segoe UI", 84), padding=(10, 2)).pack()
            ttk.Label(parent, text="(未找到头像资源)", font=("Segoe UI", 9), bootstyle="secondary").pack(pady=(6, 0))
            return

        try:
            size = 170
            img = Image.open(avatar_path).convert("RGBA")
            img = ImageOps.fit(img, (size, size), method=Image.LANCZOS)

            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)

            out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            out.paste(img, (0, 0), mask=mask)

            photo = ImageTk.PhotoImage(out)
            lbl = ttk.Label(parent, image=photo)
            lbl.pack()

            self.window._avatar_photo = photo  # type: ignore[attr-defined]
            self.window._avatar_label = lbl  # type: ignore[attr-defined]
        except Exception:
            ttk.Label(parent, text="🤖", font=("Segoe UI", 84), padding=(10, 2)).pack()
            ttk.Label(parent, text="(头像加载失败)", font=("Segoe UI", 9), bootstyle="secondary").pack(pady=(6, 0))

    # -------------------------
    # Actions
    # -------------------------
    def open_repo(self) -> None:
        webbrowser.open(self.github_repo_url)

    def open_profile(self) -> None:
        webbrowser.open(self.github_profile_url)

    def close(self) -> None:
        try:
            self.window.grab_release()
        except Exception:
            pass
        self.window.destroy()

    def toggle_usage(self) -> None:
        """
        展开/收起使用说明
        优化版本：添加了UI强制刷新机制，确保界面正确更新
        """
        if not self.usage_expanded:
            # === 展开使用说明 ===
            if self.usage_frame is None:
                self.usage_frame = ttk.Labelframe(
                    self.usage_container, text="软件详细使用说明", padding=14
                )
                usage_content = """
软件详细使用说明：

1. 首先以管理员身份打开软件，点击「自定义网站预设」选择你需要测速的域名（可以自己添加想要的域名）

2. 例如 github.com：选择后点击「智能解析IP」，也可以再点击「刷新远程 Hosts」获取更多 IP
   （刷新远程 Hosts 仅 GitHub 专属，其他域名均为智能解析后测速。）

3. 点击「开始测速」——选择延迟低的 IP 写入 hosts；也可以点「一键写入最优IP」

--- 其他功能 ---

1. 刷新 DNS：清除 DNS 缓存，使 hosts 修改立即生效
2. 查看 hosts 文件：用系统默认编辑器打开系统 hosts 文件
3. 添加/删除预设：管理自定义域名列表，方便下次使用
4. 手动选择IP：按实际需求选择特定 IP 写入 hosts
5. 自动排序：测速完成后结果按延迟自动排序，方便选择最优 IP
                """.strip()

                text_frame = ttk.Frame(self.usage_frame)
                text_frame.pack(fill=BOTH, expand=True)

                scrollbar = ttk.Scrollbar(text_frame)
                scrollbar.pack(side=RIGHT, fill=Y)

                text = ttk.Text(
                    text_frame,
                    wrap=WORD,
                    font=("Segoe UI", 10),
                    height=10,
                    yscrollcommand=scrollbar.set,
                    relief="flat",
                )
                text.insert("1.0", usage_content)
                text.configure(state="disabled")
                text.pack(side=LEFT, fill=BOTH, expand=True, padx=2, pady=2)
                scrollbar.configure(command=text.yview)

            # 显示使用说明框架
            self.usage_frame.pack(fill=BOTH, expand=True)
            
            # 更新状态
            self.usage_expanded = True
            self.usage_btn.configure(text="收起使用说明")
            
            # 调整窗口大小
            self.window.geometry(f"{self.window_width}x{self.expanded_height}")
            
            # 强制刷新UI - 关键修复！
            self.window.update_idletasks()
            
            # 重新居中窗口
            try:
                self.window.place_window_center()
            except Exception:
                # 如果place_window_center不可用，手动居中
                sw = self.window.winfo_screenwidth()
                sh = self.window.winfo_screenheight()
                x = int(sw / 2 - self.window_width / 2)
                y = int(sh / 2 - self.expanded_height / 2)
                self.window.geometry(f"{self.window_width}x{self.expanded_height}+{x}+{y}")
        else:
            # === 收起使用说明 ===
            if self.usage_frame:
                # 隐藏使用说明框架
                self.usage_frame.pack_forget()
            
            # 更新状态
            self.usage_expanded = False
            self.usage_btn.configure(text="展开使用说明")
            
            # 调整窗口大小回到原始尺寸
            self.window.geometry(f"{self.window_width}x{self.window_height}")
            
            # 强制刷新UI - 关键修复！
            self.window.update_idletasks()
            
            # 重新居中窗口
            try:
                self.window.place_window_center()
            except Exception:
                # 如果place_window_center不可用，手动居中
                sw = self.window.winfo_screenwidth()
                sh = self.window.winfo_screenheight()
                x = int(sw / 2 - self.window_width / 2)
                y = int(sh / 2 - self.window_height / 2)
                self.window.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")


if __name__ == "__main__":
    app = ttk.Window(themename="vapor")
    app.withdraw()
    AboutWindow(app)
    app.mainloop()
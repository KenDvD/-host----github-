# 🚀 SmartHostsTool

**SmartHostsTool** 是一款用于 **域名 IP 智能测速与 Hosts 优化写入** 的工具，通过自动测速算法筛选最优 IP 并写入系统 Hosts 文件，帮助用户解决访问速度慢、解析不稳定等问题 🛠️。

> ℹ️ 本程序的 **远程 Hosts 文件来自 `https://github.com/521xueweihan/GitHub520` 仓库**（用于获取最新 GitHub 相关域名的 IP 列表）。该仓库通过定期更新的 hosts 解析数据帮助提升访问速度和稳定性。:contentReference[oaicite:0]{index=0}

---

## 🖼️ 软件界面架构
### 1. 关于界面
软件启动后，点击顶部菜单栏「关于」按钮可访问此界面，包含项目基础信息与使用指引：
![关于界面](docs/screenshots/about_interface.png)

**功能模块：**
- **项目信息区**：展示软件版本、简介、作者信息及仓库链接
- **使用说明区**：提供详细的操作指南，支持展开/收起
- **交互按钮区**：包含「打开GitHub」和「确定」按钮，支持快速访问项目仓库

### 2. 主操作界面
软件核心功能的集中操作区域，采用分区设计，提升用户体验：
![主操作界面](docs/screenshots/main_interface.png)

## 📦 功能亮点

### ⚡ 自动拉取远程 Hosts 数据
从 GitHub520 等可靠来源自动获取最新域名‑IP 映射内容，无需手动查找或维护。:contentReference[oaicite:1]{index=1}

### 🚀 多节点延迟智能测速
对多个候选 IP 进行延迟测试，自动按响应速度排序，优先选择最优 IP。

### 🗂 一键写入 Hosts
支持将测得的最优 IP 写入系统 Hosts，同时可以备份原 Hosts 配置以便回退。

### ✍️ 自定义域名管理
支持用户手动添加、编辑、删除域名配置，方便处理特殊域名加速需求。

### 🔄 刷新 DNS 缓存
Hosts 写入后自动刷新本机 DNS 缓存，使配置立即生效。

### 🖼 全新 UI 界面
新版界面布局更加清晰直观，操作更简洁，让测速、写入 Hosts 更容易上手。

---

## 📋 专业使用指南
### 1. 前置准备
由于工具需要修改系统Hosts文件，必须以**管理员权限**运行：
- **Windows系统**：右键点击可执行文件 → 选择「以管理员身份运行」
- **macOS/Linux系统**：通过终端执行 `sudo python main.py`

### 2. 测速目标配置

#### 2.1 使用默认GitHub域名
工具默认集成GitHub生态相关域名（如`github.com`、`assets-cdn.github.com`、`githubusercontent.com`等），无需额外配置即可直接使用。

#### 2.2 添加自定义域名
1. 切换至「自定义预设网址」标签页
2. 点击标签页内的「添加预设」按钮
3. 在弹出的对话框中输入目标域名（如`google.com`、`twitter.com`等）
4. 点击「确定」完成添加
5. 重复上述步骤可添加多个自定义域名

### 3. IP测速流程
1. 确保已选择目标域名列表（远程Hosts或自定义预设）
2. 点击顶部操作栏的「开始测速」按钮启动测速任务
3. 监控右侧结果区域的实时测速数据
4. 如需中断测速，点击「暂停测速」按钮

**测速原理**：工具采用TCP协议进行延迟测试，每个IP地址测试3次并取平均值，确保结果的准确性和稳定性。

### 4. Hosts配置管理

#### 4.1 一键写入最优IP（推荐）
测速完成后，点击底部「一键写入最优IP」按钮，工具将自动执行以下操作：
1. 为每个域名选择延迟最低的可用IP
2. 备份当前系统Hosts文件
3. 将选定的IP-域名映射写入系统Hosts文件
4. 提示写入成功

#### 4.2 手动选择IP写入
1. 在右侧测速结果区域，勾选需要写入的IP地址（可多选）
2. 点击底部「写入选中到Hosts」按钮
3. 工具将仅写入勾选的IP-域名映射

### 5. 配置生效
写入Hosts文件后，点击顶部操作栏的「刷新DNS」按钮，工具将执行以下命令清除DNS缓存：
- **Windows**：`ipconfig /flushdns`
- **macOS**：`sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder`
- **Linux**：`sudo systemctl restart nscd` 或 `sudo /etc/init.d/nscd restart`

---

## ⚠️ 安全与使用注意事项

### 权限管理
- **必须管理员权限**：Hosts文件属于系统关键文件，修改需要管理员/root权限
- **权限不足提示**：若未以管理员身份运行，写入操作将失败并提示权限不足

### 网络环境影响
- **测速结果波动**：网络延迟受当前网络环境影响，建议在网络稳定时进行测速
- **多次测速验证**：若对测速结果有疑问，可多次测试取平均值

### 数据安全
- **自动备份**：工具在修改Hosts文件前会自动创建备份，确保数据可恢复
- **手动备份建议**：重要场景下，建议用户手动备份Hosts文件（路径：`C:\Windows\System32\drivers\etc\hosts`）

### 开源合规
- **免费使用**：本工具完全开源免费，任何付费获取渠道均为诈骗
- **合规使用**：请遵守相关法律法规，合理使用本工具

---

## ❓ 技术常见问题

### Q1：为什么测速后没有结果？
**A1**：可能的原因包括：
- 网络连接异常，无法访问目标IP
- 目标域名无可用IP地址
- 防火墙或安全软件阻止了测速请求

**解决方案**：
- 检查网络连接状态
- 点击「刷新远程Hosts」获取最新IP列表
- 临时关闭防火墙或安全软件后重试

### Q2：写入Hosts后仍然无法访问目标网站？
**A2**：可能的原因包括：
- DNS缓存未刷新，配置未生效
- 选择的IP地址不可用
- 浏览器缓存导致

**解决方案**：
- 点击「刷新DNS」按钮清除DNS缓存
- 选择其他延迟较低的IP地址重新写入
- 清除浏览器缓存或重启浏览器

### Q3：如何删除自定义添加的域名？
**A3**：
1. 切换至「自定义预设网址」标签页
2. 在域名列表中选中需要删除的域名
3. 点击标签页内的「删除预设」按钮
4. 确认删除操作

### Q4：为什么远程Hosts数据更新后IP数量变化？
**A4**：
- 远程Hosts文件内容会定期更新
- 工具采用智能过滤机制，仅保留GitHub相关域名的IP地址
- 网络环境变化可能导致部分IP不可用

**解决方案**：定期点击「刷新远程Hosts」获取最新数据

---

## 🛠️ 技术实现细节

### 1. 远程Hosts同步机制
- 采用HTTP协议从GitHub520仓库拉取最新Hosts文件
- 使用正则表达式解析IP-域名映射
- 智能过滤GitHub相关域名，确保数据相关性

### 2. IP测速算法
- 基于TCP协议的延迟测试
- 每个IP地址测试3次，取平均值作为最终延迟
- 超时时间设置为5秒，避免长时间等待

### 3. Hosts文件管理
- 自动备份原Hosts文件
- 采用原子操作写入新配置，避免文件损坏
- 支持多IP批量写入

### 4. 跨平台兼容性
- 支持Windows、macOS、Linux系统
- 使用ttkbootstrap实现跨平台GUI
- 采用resource_path函数处理资源路径，确保PyInstaller打包后正常运行

---

## 📦 安装与部署

### 1. 源码运行
```bash
# 克隆仓库
git clone https://github.com/KenDvD/SmartHostsTool-github.git
cd SmartHostsTool-github

# 安装依赖
pip install -r requirements.txt

# 运行程序（需管理员权限）
python main.py
```

### 2. 可执行文件
从项目Releases页面下载对应系统的可执行文件，直接运行即可（Windows系统需以管理员身份运行）。

### 3. 自定义打包
```bash
# 使用PyInstaller打包为单文件可执行程序
pyinstaller --onefile --windowed --icon=icon.ico --add-data "presets.json;." --add-data "头像.jpg;." --name "智能host测速工具" main.py
```

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request，共同改进项目！

### 贡献流程
1. Fork本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交Pull Request

---

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

---

## 🙏 致谢

- 感谢[GitHub520](https://github.com/521xueweihan/GitHub520)项目提供的远程Hosts数据源
- 感谢ttkbootstrap团队提供的优秀GUI框架
- 感谢所有为项目做出贡献的开发者们
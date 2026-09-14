# 浏览器立体声修复

桌面软件。给指定的 Chrome / Edge / Brave / Vivaldi 等 Chromium **用户**关掉 Wide Echo Cancellation，这个用户下所有窗口的声音才能进 VoiceMeeter / VoiceMeeter AUX / CABLE / Line 1。

只重启你勾选的那一套浏览器。其它浏览器不会关。不改这些虚拟设备的系统默认设置。

## 启动

下载 Release 里的 `TabStereoFix-v版本号.zip`，解压后打开 `TabStereoFix` 文件夹，双击 `TabStereoFix.exe`。不需要安装 Python。

开发时也可以双击 `启动立体声修复.bat`。

## 使用说明

**必须从本软件打开浏览器。** 关掉后再从任务栏、开始菜单或桌面图标打开，声音进不了 VoiceMeeter / VoiceMeeter AUX / CABLE / Line 1。

1. 双击 `TabStereoFix.exe`
2. 选一个用户
3. 点 **打开（关掉 Wide AEC）**
4. 只用软件拉起来的这套浏览器听立体声混音
5. 这套浏览器关掉后，再打开本软件，选同一用户，再点 **打开**

不要从任务栏、开始菜单、桌面图标自己开。那样 Wide AEC 会回来，声音就不进立体声混音。

要恢复原来的回声消除：选同一套，点 **关闭（恢复）**。软件只开一个窗口。其它浏览器不关。不改 VoiceMeeter / AUX / CABLE / Line 1。

点 **开机启动** 可让软件开机后自己出现。只打开本软件窗口，不会自动打开浏览器，开机后仍要点 **打开**。

## 如何发布新版本

打 tag 后，GitHub Actions 会在 Windows 上打出 `TabStereoFix-v版本号.zip`，并放到 Release 里供下载。

### 发布步骤

#### 1. 确保代码已提交并推送

在发布之前，确保你的所有代码改动已经提交并推送到 GitHub：

```bash
# 查看当前状态
git status

# 添加所有改动
git add .

# 提交改动（把“你的改动说明”替换成实际的描述）
git commit -m "你的改动说明"

# 推送到 GitHub
git push origin main
```

#### 2. 创建版本 Tag

Git Tag 是一个版本标记，用于标识发布的版本号。版本号格式为 `v主版本.次版本.修订版本`，例如 `v1.0.0`、`v1.1.0`、`v2.0.0`。

```bash
# 创建一个新的版本 tag（将 v1.0.1 替换为你想要的版本号）
git tag -a v1.0.1 -m "Release version 1.0.1"
```

#### 3. 推送 Tag 触发自动构建

```bash
# 推送 tag 到 GitHub（这会自动触发 CI 构建）
git push origin v1.0.1
```

推送后，GitHub Actions 会自动执行以下操作：
1. 构建项目
2. 生成安全签名（Attestation）
3. 创建 Release 并上传构建产物

#### 4. 查看构建结果

- 构建进度：访问项目的 **Actions** 页面查看
- 发布结果：访问项目的 **Releases** 页面查看已发布的文件

### 版本号说明

| 版本号格式 | 什么时候用 | 示例 |
|-----------|-----------|------|
| `vX.0.0` | 重大更新、不兼容改动 | `v2.0.0` |
| `vX.Y.0` | 新增功能 | `v1.1.0` |
| `vX.Y.Z` | 修复 bug | `v1.0.1` |

### 如果构建失败怎么办

1. 访问项目的 **Actions** 页面查看错误日志
2. 修复代码问题
3. 删除失败的 tag 并重新创建：

```bash
# 删除本地 tag
git tag -d v1.0.1

# 删除远程 tag
git push origin :refs/tags/v1.0.1

# 修复问题后，重新创建并推送
git tag -a v1.0.1 -m "Release version 1.0.1"
git push origin v1.0.1
```

/**
 * 彻底关闭 Chrome / Edge 的 Chrome Wide Echo Cancellation。
 * 1) 给常用快捷方式加上 --disable-features=ChromeWideEchoCancellation
 * 2) 在浏览器已完全退出时，把 Local State 里的实验项写成 Disabled
 */
const fs = require("fs");
const path = require("path");
const { execFileSync, spawnSync } = require("child_process");

const FLAG_ID = "chrome-wide-echo-cancellation";
const FLAG_DISABLED = `${FLAG_ID}@2`;
const FEATURE_ARG = "--disable-features=ChromeWideEchoCancellation";
const force = process.argv.includes("--force");

function localAppData() {
  return process.env.LOCALAPPDATA || "";
}

function localStateCandidates() {
  const root = localAppData();
  return [
    ["Chrome", path.join(root, "Google", "Chrome", "User Data", "Local State")],
    ["Chrome Beta", path.join(root, "Google", "Chrome Beta", "User Data", "Local State")],
    ["Edge", path.join(root, "Microsoft", "Edge", "User Data", "Local State")],
    ["Edge Beta", path.join(root, "Microsoft", "Edge Beta", "User Data", "Local State")],
  ];
}

function runningBrowsers() {
  let out = "";
  try {
    out = execFileSync("tasklist", ["/FO", "CSV", "/NH"], { encoding: "utf8" });
  } catch {
    return [];
  }
  const found = [];
  if (/\bchrome\.exe\b/i.test(out)) found.push("chrome.exe");
  if (/\bmsedge\.exe\b/i.test(out)) found.push("msedge.exe");
  return found;
}

function patchLocalState(filePath) {
  const raw = fs.readFileSync(filePath, "utf8");
  const data = JSON.parse(raw);
  data.browser = data.browser || {};
  const list = Array.isArray(data.browser.enabled_labs_experiments)
    ? data.browser.enabled_labs_experiments.filter(
        (item) => typeof item === "string" && !item.startsWith(`${FLAG_ID}@`) && item !== FLAG_ID,
      )
    : [];
  if (!list.includes(FLAG_DISABLED)) list.push(FLAG_DISABLED);
  data.browser.enabled_labs_experiments = list;

  const backup = `${filePath}.tab-stereo-fix.bak`;
  if (!fs.existsSync(backup)) fs.writeFileSync(backup, raw);
  fs.writeFileSync(filePath, JSON.stringify(data));
}

function patchShortcuts() {
  const ps = `
$ErrorActionPreference = 'SilentlyContinue'
$flag = '${FEATURE_ARG}'
$shell = New-Object -ComObject WScript.Shell
$roots = @(
  [Environment]::GetFolderPath('Desktop'),
  [Environment]::GetFolderPath('CommonDesktopDirectory'),
  [Environment]::GetFolderPath('StartMenu'),
  [Environment]::GetFolderPath('CommonStartMenu'),
  Join-Path $env:APPDATA 'Microsoft\\Internet Explorer\\Quick Launch\\User Pinned\\TaskBar'
)
$changed = 0
Get-ChildItem -Path $roots -Filter *.lnk -Recurse | Where-Object {
  $_.Name -match 'Chrome|Edge|铬'
} | ForEach-Object {
  $lnk = $shell.CreateShortcut($_.FullName)
  if ($lnk.TargetPath -notmatch 'chrome|msedge') { return }
  if ($lnk.Arguments -match 'ChromeWideEchoCancellation') { return }
  $lnk.Arguments = (($lnk.Arguments + ' ' + $flag).Trim())
  $lnk.Save()
  $changed++
  Write-Output $_.FullName
}
Write-Output "CHANGED:$changed"
`;
  const result = spawnSync(
    "powershell",
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
    { encoding: "utf8" },
  );
  return (result.stdout || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function main() {
  console.log("标签页立体声修复 · 关闭 Chrome Wide Echo Cancellation");
  console.log("");

  const running = runningBrowsers();
  const shortcutLines = patchShortcuts();
  const changedShortcuts = shortcutLines.filter((line) => !line.startsWith("CHANGED:"));
  console.log(changedShortcuts.length
    ? `已给 ${changedShortcuts.length} 个快捷方式加上启动参数：`
    : "没有找到还能改的 Chrome / Edge 快捷方式（可能已经加过）。");
  for (const line of changedShortcuts) console.log("  " + line);

  if (running.length && !force) {
    console.log("");
    console.log("浏览器还在运行：" + running.join(", "));
    console.log("快捷方式已经改好。要写入实验项，请先完全退出 Chrome / Edge，再重新运行本脚本。");
    console.log("也可以自己打开 chrome://flags/#chrome-wide-echo-cancellation 设为 Disabled。");
    process.exit(0);
  }

  console.log("");
  let patched = 0;
  for (const [name, filePath] of localStateCandidates()) {
    if (!fs.existsSync(filePath)) continue;
    try {
      patchLocalState(filePath);
      patched += 1;
      console.log(`已写入 ${name} 实验项：${filePath}`);
    } catch (error) {
      console.log(`写入 ${name} 失败：${error.message}`);
    }
  }
  if (!patched) console.log("没有找到可写的 Local State。请改用浏览器实验项页面。");

  console.log("");
  console.log("下一步：完全退出浏览器后重新打开，再用立体声混音听一次标签页声音。");
}

main();

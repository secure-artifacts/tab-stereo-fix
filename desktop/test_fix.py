import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from autostart import START_BAT, autostart_command, write_autostart_vbs
from paths import app_root, asset_file, config_dir

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from build_exe import release_version, write_version_file
from browser_audio_fix import (
    BrowserProfile,
    INSTALLS,
    collect_boost_pids,
    collect_install_pids,
    disable_flags,
    filter_profiles_by_name,
    is_fix_on,
    group_installs,
    mark_running_profiles,
    merge_disable_features,
    merge_open_command,
    _is_our_shortcut,
    _product_key,
    one_install_only,
    parse_chrome_arg,
    patch_local_state,
    strip_gain_extension,
    write_fix_status,
    write_gain_config,
    pids_for_install,
    profile_display,
    profiles_from_local_state,
    restore_flags,
)


class DisableFlagsTests(unittest.TestCase):
    def test_adds_disabled_flags_and_keeps_others(self):
        data = {
            "browser": {
                "enabled_labs_experiments": [
                    "enable-force-dark@1",
                    "chrome-wide-echo-cancellation@1",
                ]
            }
        }
        next_data = disable_flags(data)
        flags = next_data["browser"]["enabled_labs_experiments"]
        self.assertIn("enable-force-dark@1", flags)
        self.assertIn("chrome-wide-echo-cancellation@2", flags)
        self.assertIn("edge-wide-echo-cancellation@2", flags)
        self.assertIn("msedge-wide-echo-cancellation@2", flags)
        self.assertNotIn("chrome-wide-echo-cancellation@1", flags)
        self.assertFalse(next_data["startup_boost"]["enabled"])
        self.assertFalse(next_data["background_mode"]["enabled"])

    def test_restore_removes_our_flags(self):
        data = disable_flags({"browser": {"enabled_labs_experiments": ["enable-force-dark@1"]}})
        restored = restore_flags(data)
        flags = restored["browser"]["enabled_labs_experiments"]
        self.assertIn("enable-force-dark@1", flags)
        self.assertFalse(any(item.startswith("chrome-wide-echo-cancellation") for item in flags))
        self.assertTrue(restored["startup_boost"]["enabled"])


class LocalStateTests(unittest.TestCase):
    def test_reads_all_profiles(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "Default").mkdir()
            (root / "Profile 1").mkdir()
            payload = {
                "profile": {
                    "last_used": "Profile 1",
                    "info_cache": {
                        "Default": {"name": "个人", "user_name": "a@example.com"},
                        "Profile 1": {"name": "工作"},
                    },
                }
            }
            (root / "Local State").write_text(json.dumps(payload), encoding="utf-8")
            profiles = profiles_from_local_state("Chrome", Path("chrome.exe"), root)
            self.assertEqual([item.directory for item in profiles], ["Default", "Profile 1"])
            self.assertEqual(profiles[0].display_name, "个人")
            self.assertTrue(profiles[1].selected)

    def test_patch_writes_backup(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "Default").mkdir()
            (root / "Local State").write_text(json.dumps({"browser": {}}), encoding="utf-8")
            patched = patch_local_state(root)
            self.assertTrue(patched.exists())
            data = json.loads(patched.read_text(encoding="utf-8"))
            self.assertIn("chrome-wide-echo-cancellation@2", data["browser"]["enabled_labs_experiments"])
            self.assertTrue((root / "Local State.tab-stereo-fix.bak").exists())

    def test_status_file_counts_as_fixed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.assertFalse(is_fix_on(root))
            write_fix_status(root, True)
            self.assertTrue(is_fix_on(root))
            write_fix_status(root, False)
            self.assertFalse(is_fix_on(root))


class PidScopeTests(unittest.TestCase):
    def test_does_not_match_other_browsers(self):
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        chrome_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome\User Data")
        edge_data = Path(r"C:\Users\me\AppData\Local\Microsoft\Edge\User Data")
        rows = [
            {
                "pid": 11,
                "ppid": 1,
                "name": "chrome.exe",
                "exe": str(chrome),
                "cmdline": f'"{chrome}" --user-data-dir="{chrome_data}"',
                "user_data": str(chrome_data),
                "directory": "Default",
            },
            {
                "pid": 12,
                "ppid": 11,
                "name": "chrome.exe",
                "exe": str(chrome),
                "cmdline": f'"{chrome}" --type=gpu --user-data-dir="{chrome_data}"',
                "user_data": str(chrome_data),
                "directory": "Default",
            },
            {
                "pid": 21,
                "ppid": 2,
                "name": "msedge.exe",
                "exe": str(edge),
                "cmdline": f'"{edge}" --user-data-dir="{edge_data}"',
                "user_data": str(edge_data),
                "directory": "Default",
            },
            {
                "pid": 31,
                "ppid": 3,
                "name": "brave.exe",
                "exe": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                "cmdline": "--user-data-dir=C:\\Users\\me\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data",
                "user_data": r"C:\Users\me\AppData\Local\BraveSoftware\Brave-Browser\User Data",
                "directory": "Default",
            },
        ]
        self.assertEqual(set(pids_for_install(chrome, chrome_data, rows=rows)), {11, 12})
        profiles = [
            BrowserProfile("Chrome", chrome, chrome_data, "Default", "个人", selected=True)
        ]
        pids, warnings = collect_install_pids(profiles, rows=rows)
        self.assertEqual(set(pids), {11, 12})
        self.assertFalse(warnings)

    def test_boost_pid_stays_on_same_install(self):
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        beta = Path(r"C:\Program Files (x86)\Microsoft\Edge Beta\Application\msedge.exe")
        edge_data = Path(r"C:\Users\me\AppData\Local\Microsoft\Edge\User Data")
        beta_data = Path(r"C:\Users\me\AppData\Local\Microsoft\Edge Beta\User Data")
        rows = [
            {
                "pid": 88,
                "ppid": 1,
                "name": "msedge.exe",
                "exe": str(edge),
                "cmdline": f'"{edge}" --no-startup-window',
                "user_data": "",
                "directory": "Default",
            },
            {
                "pid": 89,
                "ppid": 1,
                "name": "msedge.exe",
                "exe": str(beta),
                "cmdline": f'"{beta}" --no-startup-window',
                "user_data": "",
                "directory": "Default",
            },
        ]
        self.assertEqual(collect_boost_pids(beta, beta_data, rows=rows), [89])
        self.assertEqual(collect_boost_pids(edge, edge_data, rows=rows), [88])

    def test_does_not_match_chrome_beta(self):
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        beta = Path(r"C:\Program Files\Google\Chrome Beta\Application\chrome.exe")
        chrome_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome\User Data")
        beta_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome Beta\User Data")
        rows = [
            {
                "pid": 41,
                "ppid": 1,
                "name": "chrome.exe",
                "exe": str(chrome),
                "cmdline": str(chrome),
                "user_data": "",
                "directory": "Default",
            },
            {
                "pid": 51,
                "ppid": 1,
                "name": "chrome.exe",
                "exe": str(beta),
                "cmdline": str(beta),
                "user_data": "",
                "directory": "Default",
            },
        ]
        self.assertEqual(pids_for_install(chrome, chrome_data, rows=rows), [41])
        self.assertEqual(pids_for_install(beta, beta_data, rows=rows), [51])

    def test_does_not_match_chrome_protect_or_vivaldi(self):
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        protect = Path(r"C:\Program Files\Google\Chrome Protect\Application\chrome.exe")
        vivaldi = Path(r"C:\Users\me\AppData\Local\Vivaldi\Application\vivaldi.exe")
        chrome_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome\User Data")
        protect_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome Protect\User Data")
        vivaldi_data = Path(r"C:\Users\me\AppData\Local\Vivaldi\User Data")
        rows = [
            {
                "pid": 61,
                "ppid": 1,
                "name": "chrome.exe",
                "exe": str(chrome),
                "cmdline": str(chrome),
                "user_data": "",
                "directory": "Default",
            },
            {
                "pid": 71,
                "ppid": 1,
                "name": "chrome.exe",
                "exe": str(protect),
                "cmdline": str(protect),
                "user_data": "",
                "directory": "Default",
            },
            {
                "pid": 81,
                "ppid": 1,
                "name": "vivaldi.exe",
                "exe": str(vivaldi),
                "cmdline": str(vivaldi),
                "user_data": "",
                "directory": "Default",
            },
        ]
        self.assertEqual(pids_for_install(chrome, chrome_data, rows=rows), [61])
        self.assertEqual(pids_for_install(protect, protect_data, rows=rows), [71])
        self.assertEqual(pids_for_install(vivaldi, vivaldi_data, rows=rows), [81])
        self.assertEqual(_product_key(protect), "chrome-protect")
        self.assertEqual(_product_key(vivaldi), "vivaldi")
        self.assertNotEqual(_product_key(chrome), _product_key(protect))

    def test_discovers_vivaldi_and_chrome_protect_specs(self):
        names = [item["name"] for item in INSTALLS]
        self.assertIn("Vivaldi", names)
        self.assertIn("Chrome Protect", names)
        self.assertIn("Chrome Canary", names)

    def test_one_install_drops_other_browsers(self):
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        chrome_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome\User Data")
        edge_data = Path(r"C:\Users\me\AppData\Local\Microsoft\Edge\User Data")
        kept, notes = one_install_only(
            [
                BrowserProfile("Chrome", chrome, chrome_data, "Default", "个人"),
                BrowserProfile("Edge", edge, edge_data, "Default", "工作"),
            ]
        )
        self.assertEqual([item.browser for item in kept], ["Chrome"])
        self.assertTrue(notes)

    def test_group_installs_keeps_browsers_separate(self):
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        chrome_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome\User Data")
        edge_data = Path(r"C:\Users\me\AppData\Local\Microsoft\Edge\User Data")
        groups = group_installs(
            [
                BrowserProfile("Chrome", chrome, chrome_data, "Default", "个人"),
                BrowserProfile("Chrome", chrome, chrome_data, "Profile 1", "工作"),
                BrowserProfile("Edge", edge, edge_data, "Default", "Edge"),
            ]
        )
        self.assertEqual([item.browser for item in groups], ["Chrome", "Edge"])
        self.assertEqual(len(groups[0].profiles), 2)

    def test_mark_running_ignores_other_install(self):
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        beta = Path(r"C:\Program Files\Google\Chrome Beta\Application\chrome.exe")
        chrome_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome\User Data")
        beta_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome Beta\User Data")
        profiles = [
            BrowserProfile("Chrome", chrome, chrome_data, "Default", "个人", selected=True),
            BrowserProfile("Chrome Beta", beta, beta_data, "Default", "测试", selected=True),
        ]
        rows = [
            {
                "pid": 41,
                "ppid": 1,
                "name": "chrome.exe",
                "exe": str(chrome),
                "cmdline": f'"{chrome}" --profile-directory=Default',
                "user_data": "",
                "directory": "Default",
            }
        ]
        mark_running_profiles(profiles, rows=rows, visible_pids={41})
        self.assertTrue(profiles[0].selected)
        self.assertFalse(profiles[1].selected)

    def test_parse_user_data_with_spaces(self):
        cmd = (
            r'"C:\Program Files\Google\Chrome\Application\chrome.exe" '
            r'"--user-data-dir=C:\Users\melo\AppData\Local\Google\Chrome\User Data" '
            r"--profile-directory=Default"
        )
        self.assertTrue(parse_chrome_arg(cmd, "--user-data-dir").endswith("User Data"))
        self.assertEqual(parse_chrome_arg(cmd, "--profile-directory"), "Default")

    def test_edge_background_is_not_running(self):
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        chrome_data = Path(r"C:\Users\me\AppData\Local\Google\Chrome\User Data")
        edge_data = Path(r"C:\Users\me\AppData\Local\Microsoft\Edge\User Data")
        profiles = [
            BrowserProfile("Chrome", chrome, chrome_data, "Default", "个人"),
            BrowserProfile("Edge", edge, edge_data, "Default", "Edge"),
        ]
        rows = [
            {
                "pid": 11,
                "ppid": 1,
                "name": "chrome.exe",
                "exe": str(chrome),
                "cmdline": f'"{chrome}" "--user-data-dir={chrome_data}" --profile-directory=Default',
                "user_data": str(chrome_data),
                "directory": "Default",
            },
            {
                "pid": 21,
                "ppid": 2,
                "name": "msedge.exe",
                "exe": str(edge),
                "cmdline": f'"{edge}" --no-startup-window',
                "user_data": "",
                "directory": "Default",
            },
        ]
        mark_running_profiles(profiles, rows=rows, visible_pids=set())
        self.assertTrue(profiles[0].selected)
        self.assertFalse(profiles[1].selected)

    def test_hides_numeric_profile_names(self):
        name, email = profile_display({"name": "7833750", "gaia_id": "7833750"}, "Default")
        self.assertEqual(name, "默认用户")
        self.assertEqual(email, "")
        name, _ = profile_display({"gaia_given_name": "783 375"}, "Default")
        self.assertEqual(name, "默认用户")

    def test_write_gain_config(self):
        path = write_gain_config(3)
        self.assertIn("3.00", path.read_text(encoding="utf-8"))

    def test_strip_gain_extension(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            prefs = root / "Default" / "Preferences"
            prefs.parent.mkdir()
            prefs.write_text(
                json.dumps(
                    {
                        "extensions": {
                            "settings": {
                                "aaa": {"path": r"C:\tmp\gain_ext", "manifest": {"name": "立体声增益"}},
                                "bbb": {"path": r"C:\tmp\other", "manifest": {"name": "其它"}},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(strip_gain_extension(root), 1)
            data = json.loads(prefs.read_text(encoding="utf-8"))
            self.assertNotIn("aaa", data["extensions"]["settings"])
            self.assertIn("bbb", data["extensions"]["settings"])


class PersistLaunchTests(unittest.TestCase):
    def test_adds_and_removes_feature_flag(self):
        self.assertEqual(
            merge_disable_features("", enabled=True),
            "--disable-features=ChromeWideEchoCancellation",
        )
        self.assertEqual(
            merge_disable_features("--profile-directory=Default", enabled=True),
            "--profile-directory=Default --disable-features=ChromeWideEchoCancellation",
        )
        self.assertEqual(
            merge_disable_features(
                "--disable-features=Translate,ChromeWideEchoCancellation",
                enabled=False,
            ),
            "--disable-features=Translate",
        )
        self.assertEqual(
            merge_disable_features("--disable-features=ChromeWideEchoCancellation", enabled=False),
            "",
        )

    def test_keeps_existing_disable_features(self):
        self.assertEqual(
            merge_disable_features("--disable-features=Translate", enabled=True),
            "--disable-features=Translate,ChromeWideEchoCancellation",
        )

    def test_open_command_keeps_url_placeholder(self):
        command = r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --single-argument %1'
        on = merge_open_command(command, enabled=True)
        self.assertIn("--disable-features=ChromeWideEchoCancellation", on)
        self.assertIn("--single-argument %1", on)
        off = merge_open_command(on, enabled=False)
        self.assertEqual(off, command)

    def test_detects_wrapper_shortcut(self):
        self.assertTrue(
            _is_our_shortcut(
                r"C:\Windows\System32\wscript.exe",
                r'//nologo "D:\redownload\ruanjian\tab-stereo-fix\launchers\launch-fixed.vbs"',
            )
        )
        self.assertFalse(_is_our_shortcut(r"C:\Program Files\Google\Chrome\Application\chrome.exe", ""))


class SearchProfilesTests(unittest.TestCase):
    def test_filters_by_user_name(self):
        chrome = Path(r"C:\chrome.exe")
        data = Path(r"C:\Users\me\Chrome")
        profiles = [
            BrowserProfile("Chrome", chrome, data, "Default", "个人"),
            BrowserProfile("Chrome", chrome, data, "Profile 1", "工作", email="work@example.com"),
            BrowserProfile("Edge", chrome, data, "Default", "默认用户"),
        ]
        found = filter_profiles_by_name(profiles, "工作")
        self.assertEqual([item.display_name for item in found], ["工作"])
        found = filter_profiles_by_name(profiles, "WORK@")
        self.assertEqual([item.display_name for item in found], ["工作"])
        found = filter_profiles_by_name(profiles, "edge")
        self.assertEqual([item.display_name for item in found], ["默认用户"])
        self.assertEqual(len(filter_profiles_by_name(profiles, "")), 3)
        self.assertEqual(filter_profiles_by_name(profiles, "没有这个"), [])
        found = filter_profiles_by_name(profiles, "直播", extras={profiles[0].key: "直播"})
        self.assertEqual([item.display_name for item in found], ["个人"])


class CategoryTests(unittest.TestCase):
    def setUp(self) -> None:
        import categories

        self._mod = categories
        self._old = categories.STORE
        self._tmp = tempfile.TemporaryDirectory()
        categories.STORE = Path(self._tmp.name) / "user-categories.json"

    def tearDown(self) -> None:
        self._mod.STORE = self._old
        self._tmp.cleanup()

    def test_assign_and_filter_names(self):
        self.assertEqual(self._mod.category_of("chrome|a|Default"), "未分类")
        self._mod.set_category("chrome|a|Default", "直播")
        self.assertEqual(self._mod.category_of("chrome|a|Default"), "直播")
        self.assertIn("直播", self._mod.category_names())
        self.assertIn("全部", self._mod.filter_options())

    def test_delete_moves_users_back(self):
        self._mod.set_category("edge|b|Default", "工作")
        self._mod.delete_category("工作")
        self.assertEqual(self._mod.category_of("edge|b|Default"), "未分类")
        self.assertNotIn("工作", self._mod.category_names())

    def test_rename_keeps_users(self):
        self._mod.set_category("chrome|a|Default", "直播")
        self.assertEqual(self._mod.rename_category("直播", "开播"), "开播")
        self.assertEqual(self._mod.category_of("chrome|a|Default"), "开播")
        self.assertNotIn("直播", self._mod.category_names())
        self.assertIn("开播", self._mod.category_names())


class PathTests(unittest.TestCase):
    def test_source_root_contains_desktop(self):
        self.assertTrue((app_root() / "desktop").is_dir())

    def test_source_config_stays_in_repo(self):
        self.assertEqual(config_dir(), app_root() / "config")

    def test_app_icon_assets_exist(self):
        self.assertTrue(asset_file("app.ico").is_file())
        self.assertTrue(asset_file("app-48.png").is_file())

    def test_release_version_is_numeric(self):
        self.assertRegex(release_version(), r"^\d+\.\d+\.\d+\.\d+$")

    def test_version_file_names_the_ascii_exe(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "version.txt"
            write_version_file(path)
            text = path.read_text(encoding="utf-8")
        self.assertIn("TabStereoFix.exe", text)
        self.assertIn("MELO MZ", text)


class AutostartTests(unittest.TestCase):
    def test_command_points_at_hidden_launcher(self):
        command = autostart_command()
        self.assertIn("wscript.exe", command.lower())
        self.assertIn("autostart.vbs", command.lower())

    def test_vbs_starts_app_bat(self):
        path = write_autostart_vbs()
        text = path.read_text(encoding="utf-16")
        self.assertIn(str(START_BAT), text)
        self.assertIn("Wscript.Shell", text)


if __name__ == "__main__":
    unittest.main()

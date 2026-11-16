import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from steam_playtime import history, report, steam
from steam_playtime.cli import main
from steam_playtime.sessions import Session, exe_path, name_from_exe, normalize_names, parse_sessions

FIXTURES = Path(__file__).parent / "fixtures"


class FixtureSteam(unittest.TestCase):
    """Copies the fake Steam install to a temp folder and points libraryfolders.vdf at it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.steam_dir = self.tmp / "steam"
        shutil.copytree(FIXTURES / "steam", self.steam_dir)
        shutil.copytree(FIXTURES / "library2", self.tmp / "library2")
        vdf = self.steam_dir / "steamapps" / "libraryfolders.vdf"
        esc = lambda p: str(p).replace("\\", "\\\\")
        vdf.write_text(
            vdf.read_text().replace("__MAIN__", esc(self.steam_dir)).replace("__LIB2__", esc(self.tmp / "library2"))
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sessions(self):
        names = steam.installed_game_names(steam.library_dirs(self.steam_dir))
        return parse_sessions(steam.process_logs(self.steam_dir), names)


class SteamFolderTests(FixtureSteam):
    def test_finds_steam_with_override(self):
        self.assertEqual(steam.find_steam_dir(str(self.steam_dir)), self.steam_dir)

    def test_missing_steam(self):
        self.assertIsNone(steam.find_steam_dir(str(self.tmp / "nope")))

    def test_reads_every_library(self):
        libs = steam.library_dirs(self.steam_dir)
        self.assertIn(self.tmp / "library2", libs)
        names = steam.installed_game_names(libs)
        self.assertEqual(names, {"1000": "Alpha Game", "2000": "Beta: Deluxe Edition"})


class SessionTests(FixtureSteam):
    def by_name(self):
        return {s.name: s for s in self.sessions()}

    def test_overlapping_processes_become_one_session(self):
        alpha = [s for s in self.sessions() if s.app == "1000"]
        self.assertEqual(len(alpha), 1)
        self.assertEqual(alpha[0].minutes, 90)

    def test_session_cut_by_steam_restart_is_dropped(self):
        self.assertFalse(any(s.start.day == 9 for s in self.sessions()))

    def test_short_sessions_are_dropped(self):
        self.assertNotIn("Beta: Deluxe Edition", self.by_name())

    def test_uninstalled_game_named_after_its_folder(self):
        self.assertEqual(self.by_name()["Gamma Uninstalled"].minutes, 60)

    def test_spacewar_sessions_named_after_executable(self):
        names = self.by_name()
        self.assertEqual(names["Cool Indie"].minutes, 60)
        self.assertEqual(names["Spacewar (AppID 480)"].minutes, 15)

    def test_default_exclusions(self):
        apps = {s.app for s in self.sessions()}
        self.assertNotIn("1182480", apps)
        self.assertNotIn("431960", apps)

    def test_include_all(self):
        names = steam.installed_game_names(steam.library_dirs(self.steam_dir))
        apps = {s.app for s in parse_sessions(steam.process_logs(self.steam_dir), names, excluded_apps=set())}
        self.assertIn("431960", apps)
        self.assertNotIn("1182480", apps)  # only ran the EA helper exe, which is always ignored

    def test_remote_play(self):
        self.assertIn("Steam Remote Play", self.by_name())

    def test_session_count(self):
        self.assertEqual(len(self.sessions()), 5)


class PlaytimeTotalsTests(FixtureSteam):
    def test_reads_totals_despite_nested_blocks(self):
        totals = steam.playtime_totals(self.steam_dir)
        self.assertEqual(totals["1000"], {"minutes": 5400, "last_played": 1767225600})
        self.assertEqual(totals["2000"]["minutes"], 90)
        self.assertNotIn("7", totals)  # app entry without playtime

    def test_missing_userdata_is_empty(self):
        self.assertEqual(steam.playtime_totals(self.tmp), {})


class HeaderImageTests(FixtureSteam):
    def test_finds_new_and_flat_cache_layouts(self):
        cache = self.steam_dir / "appcache" / "librarycache"
        (cache / "1000" / "abc123").mkdir(parents=True)
        (cache / "1000" / "abc123" / "library_header.jpg").write_bytes(b"\xff\xd8new")
        (cache / "3000_header.jpg").write_bytes(b"\xff\xd8flat")
        found = steam.header_images(self.steam_dir, ["1000", "3000", "9999"])
        self.assertEqual(found["1000"].name, "library_header.jpg")
        self.assertEqual(found["3000"].name, "3000_header.jpg")
        self.assertNotIn("9999", found)

    def test_images_embedded_in_report(self):
        cache = self.steam_dir / "appcache" / "librarycache" / "1000"
        cache.mkdir(parents=True)
        (cache / "header.jpg").write_bytes(b"\xff\xd8img")
        out = self.tmp / "r.html"
        main(["--steam-dir", str(self.steam_dir), "-o", str(out), "--no-history", "--no-open"])
        html = out.read_text(encoding="utf-8")
        self.assertIn('"1000": "data:image/jpeg;base64,', html)
        self.assertNotIn("__IMAGES__", html)
        main(["--steam-dir", str(self.steam_dir), "-o", str(out), "--no-history", "--no-open", "--no-covers"])
        self.assertNotIn("data:image/jpeg;base64,", out.read_text(encoding="utf-8"))


class DemoTests(unittest.TestCase):
    def test_demo_is_deterministic_and_plausible(self):
        from steam_playtime.demo import demo_sessions

        a, b = demo_sessions(), demo_sessions()
        self.assertEqual(a, b)
        self.assertGreater(len(a), 100)
        self.assertTrue(all(s.minutes >= 8 for s in a))

    def test_demo_cli(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "demo.html"
            self.assertEqual(main(["--demo", "--no-open", "-o", str(out)]), 0)
            html = out.read_text(encoding="utf-8")
            self.assertIn("Ashen Keep", html)
            self.assertNotIn("__DATA__", html)
            self.assertNotIn("__TOTALS__", html)


class ExeTests(unittest.TestCase):
    def test_exe_path(self):
        self.assertEqual(exe_path('""C:\\A B\\game.exe" -x"'), "C:\\A B\\game.exe")
        self.assertEqual(exe_path(""), None)
        self.assertEqual(exe_path('"/home/u/.steam/steamapps/common/G/run.sh" --x'), "/home/u/.steam/steamapps/common/G/run.sh")

    def test_name_from_exe(self):
        self.assertEqual(name_from_exe("C:\\Steam\\steamapps\\common\\My Game\\bin\\x64\\g.exe"), "My Game")
        self.assertEqual(name_from_exe("/home/u/.steam/steam/steamapps/common/Linux Game/run.sh"), "Linux Game")
        self.assertEqual(name_from_exe("C:\\Games\\Thing\\Binaries\\Win64\\Thing-Shipping.exe"), "Thing")


class HistoryTests(unittest.TestCase):
    def test_merge_keeps_old_sessions_and_real_names(self):
        t = lambda h: datetime(2026, 1, 1, h)
        old = [Session("1", "Old Game", t(1), t(2)), Session("2", "Named", t(3), t(4))]
        new = [Session("2", "App 2", t(3), t(5)), Session("3", "New", t(6), t(7))]
        merged = history.merge(old, new)
        self.assertEqual([s.app for s in merged], ["1", "2", "3"])
        self.assertEqual(merged[1].name, "Named")
        self.assertEqual(merged[1].end, t(5))

    def test_normalize_names_uses_known_name(self):
        t = lambda h: datetime(2026, 1, 1, h)
        s = [Session("9", "App 9", t(1), t(2)), Session("9", "Real", t(3), t(4))]
        normalize_names(s, {})
        self.assertEqual({x.name for x in s}, {"Real"})

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sub" / "h.json"
            s = [Session("1", "Ñandú ™", datetime(2026, 1, 1, 1), datetime(2026, 1, 1, 2))]
            history.save(p, s)
            self.assertEqual(history.load(p), s)


class CliTests(FixtureSteam):
    def test_end_to_end(self):
        out, hist, csv_ = self.tmp / "r.html", self.tmp / "h.json", self.tmp / "s.csv"
        args = ["--steam-dir", str(self.steam_dir), "-o", str(out), "--history", str(hist), "--csv", str(csv_), "--no-open", "--lang", "en"]
        self.assertEqual(main(args), 0)
        html = out.read_text(encoding="utf-8")
        self.assertNotIn("__DATA__", html)
        self.assertNotIn("__TOTALS__", html)
        self.assertIn("Cool Indie", html)
        self.assertIn('"1000": 5400', html)  # lifetime minutes embedded for played games
        self.assertEqual(len(json.loads(hist.read_text(encoding="utf-8"))["sessions"]), 5)
        self.assertEqual(len(csv_.read_text(encoding="utf-8").strip().splitlines()), 6)
        # a second run must not duplicate anything
        self.assertEqual(main(args), 0)
        self.assertEqual(len(history.load(hist)), 5)

    def test_missing_steam_returns_error(self):
        self.assertEqual(main(["--steam-dir", str(self.tmp / "nope"), "--no-open"]), 1)


if __name__ == "__main__":
    unittest.main()

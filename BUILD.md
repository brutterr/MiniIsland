```python
import subprocess, tempfile

UPDATE_URL = "https://api.github.com/repos/brutterr/MiniIsland/releases/latest"


def check_update():
    """Запускать в отдельном потоке: threading.Thread(target=check_update, daemon=True).start()"""
    try:
        req = urllib.request.Request(UPDATE_URL, headers={"User-Agent": APP_NAME})
        with urllib.request.urlopen(req, timeout=10) as r:
            info = json.load(r)
        ver = lambda s: tuple(int(x) for x in s.lstrip("v").split("."))
        if ver(info["tag_name"]) <= ver(APP_VERSION):
            return
        url = next(a["browser_download_url"] for a in info["assets"]
                   if a["name"].lower().endswith(".exe"))
        path = os.path.join(tempfile.gettempdir(), "MiniIsland-Setup.exe")
        urllib.request.urlretrieve(url, path)
        subprocess.Popen([path, "/SILENT", "/NORESTART"])  # установщик сам закроет остров и запустит новый
    except Exception as ex:
        log(f"update: {ex}", once=True)
```


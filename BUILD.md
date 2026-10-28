# Как сделать .exe и автообновление

## 1. Один раз: собрать .exe (Python у пользователей не нужен)
1. Запусти `run.bat` (создаст `.venv` со всеми пакетами).
2. Запусти `build_exe.bat`. Результат: папка `dist\MiniIsland\` с `MiniIsland.exe` внутри.
   Это сборка «onedir»: она стартует быстро и реже ругается антивирус, чем «onefile».
3. Если exe не стартует или нет значка в трее/острова: собери версию с консолью (убери `--windowed`
   в `build_exe.bat`) и посмотри ошибку. Обычно не хватает какого-то `winrt`-модуля: добавь для него
   ещё один `--collect-all winrt.windows.<модуль>`.
   Сборку я не мог проверить на Windows, поэтому первый запуск проверь сам.

## 2. Установщик для других людей
1. Поставь [Inno Setup](https://jrsoftware.org/isdl.php).
2. Открой `installer.iss`, нажми Compile. Получишь `installer_out\MiniIsland-Setup-1.0.1.exe`.
   Установка идёт в профиль пользователя, права администратора не нужны.
3. Этот один файл и раздаёшь. Автозапуск остров включит сам при первом старте.

## 3. Автообновление (самый простой надёжный путь: GitHub Releases)
Схема: новая версия = новый релиз на GitHub с файлом `MiniIsland-Setup-X.Y.Z.exe`.
Остров при старте спрашивает у GitHub последнюю версию, скачивает установщик и тихо запускает его.

1. Создай репозиторий на GitHub (можно приватный не делать: для скачивания без токена он должен быть публичным).
2. Для каждой версии: подними `AppVersion` в `installer.iss` и `APP_VERSION` в `island.py`,
   собери установщик, создай Release с тегом `v1.0.2` и приложи `MiniIsland-Setup-1.0.2.exe`.
3. Добавь в `island.py` проверку обновлений (замени `OWNER/REPO`):

```python
import subprocess, tempfile

UPDATE_URL = "https://api.github.com/repos/OWNER/REPO/releases/latest"


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
   Вызов: в `Island.__init__` рядом с `QTimer.singleShot(600, ...)` добавь
   `QTimer.singleShot(8000, lambda: threading.Thread(target=check_update, daemon=True).start())`.
   Проверку включай только для собранного exe: `if getattr(sys, "frozen", False)`.
4. Автоматизация (по желанию): GitHub Actions на Windows-раннере, который по тегу `v*` ставит
   Python, зависимости, запускает PyInstaller и Inno Setup и прикладывает установщик к релизу.

## Важно
- Антивирусы и SmartScreen часто ругаются на неподписанные exe от PyInstaller. Лечится
  сертификатом для подписи кода (платный) или тем, что пользователь жмёт «Подробнее -> Выполнить в любом случае».
- Настройки лежат в `~\.island_config.json`, а не рядом с exe, поэтому при обновлении они сохраняются.

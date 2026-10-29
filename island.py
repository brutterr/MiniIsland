import ast
import asyncio
import json
import math
import operator as op
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from string import Template
from urllib.parse import urlencode, quote

from PySide6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QRectF,
                            QPointF, QPoint, QSize, QLineF, QMimeData, QUrl, QTime, QObject, Signal,
                            QVariantAnimation, QAbstractNativeEventFilter, QEvent, QFileInfo,
                            QBuffer, QIODevice, QLockFile)
from PySide6.QtGui import (QPainter, QColor, QDesktopServices, QPixmap, QPen, QFont,
                           QFontMetrics,
                           QPainterPath, QPolygonF, QLinearGradient, QImage, QIcon, QCursor)
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QListWidget, QListWidgetItem, QPlainTextEdit, QLabel, QSpinBox,
                               QPushButton, QMenu, QLayout, QStackedWidget, QButtonGroup,
                               QLineEdit, QSizePolicy, QGraphicsOpacityEffect, QSlider,
                               QFileDialog, QFileIconProvider, QStyle, QStyledItemDelegate)

COLLAPSED_H = 36
EXPANDED = (680, 432)
WAVE_PAD = 14        # запас снизу окна: сюда выгибается нижний край острова под музыку
IDLE_SLEEP = 45      # через сколько секунд бездействия жильцы засыпают
MARGIN_COLLAPSED = (14, 5, 14, 5 + WAVE_PAD)
TOAST_H = 76                                  # высота острова, когда он показывает новый трек
TOAST_MARGINS = (14, 10, 18, 10 + WAVE_PAD)
TOAST_SECS = 4.0                              # сколько держится показ трека
MUSIC_PILL_W = 170                            # компактная пилюля с музыкой: обложка, время и питомец
MARGIN_EXPANDED = (18, 14, 18, 14 + WAVE_PAD)
EDGE_PX = 1          # самый верх экрана: здесь шторка открывается полностью
PEEK_PX = 14         # полоса у верхнего края: здесь сначала выглядывает пилюля со временем
PEEK_DELAY = 0.12    # сколько секунд держать курсор в полосе до появления пилюли
EDGE_HALF = 220      # полуширина зон от центра экрана
IMG_ROLE = Qt.UserRole + 1
KIND_ROLE = Qt.UserRole + 2
TIME_ROLE = Qt.UserRole + 3
TITLE_ROLE = Qt.UserRole + 4
SUB_ROLE = Qt.UserRole + 5
THUMB_ROLE = Qt.UserRole + 6
FIND_ROLE = Qt.UserRole + 7
COPIED_ROLE = Qt.UserRole + 8
TOP_MARGIN = 8
HOME = os.path.expanduser("~")
NOTE_FILE = os.path.join(HOME, ".island_note.txt")
CONFIG_FILE = os.path.join(HOME, ".island_config.json")
DL_DIR = os.path.join(HOME, "Downloads")
PARTIAL_EXT = (".crdownload", ".part", ".opdownload")
DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# ---------------- темы ----------------
THEMES = {
    "light": dict(name="Светлая", fg="#1c1c1e", sub="#6e6e73", card="rgba(255,255,255,150)",
                  card_hi="rgba(255,255,255,215)", chip="rgba(255,255,255,240)",
                  chipfg="#1c1c1e", hover="rgba(0,0,0,18)", field="rgba(255,255,255,175)",
                  groove="rgba(0,0,0,40)", panel=(246, 241, 247, 240), border=(0, 0, 0, 28),
                  card_rgba=(255, 255, 255, 150), track=(0, 0, 0, 40),
                  play_bg=(17, 17, 19), play_fg=(255, 255, 255),
                  pill=(0, 0, 0), accent=None, eq="bars",
                  eq_pill=("#ffffff", None), eq_card=(None, None), wave=(1.0, 1.0)),
    "dark": dict(name="Тёмная", fg="#f5f5f7", sub="#9a9aa0", card="rgba(255,255,255,20)",
                 card_hi="rgba(255,255,255,36)", chip="rgba(255,255,255,45)",
                 chipfg="#ffffff", hover="rgba(255,255,255,22)", field="rgba(255,255,255,28)",
                 groove="rgba(255,255,255,45)", panel=(20, 20, 22, 250), border=(255, 255, 255, 28),
                 card_rgba=(255, 255, 255, 20), track=(255, 255, 255, 60),
                 play_bg=(255, 255, 255), play_fg=(0, 0, 0),
                 pill=(0, 0, 0), accent=None, eq="bars",
                 eq_pill=("#ffffff", None), eq_card=(None, None), wave=(1.0, 1.0)),
    # розовая: светлая, мягкая; эквалайзер из округлых «бусин», волна пологая и плавная
    "pink": dict(name="Розовая", fg="#4a1730", sub="#a2587a", card="rgba(255,255,255,140)",
                 card_hi="rgba(255,255,255,210)", chip="rgba(255,255,255,235)",
                 chipfg="#b0265f", hover="rgba(200,50,110,24)", field="rgba(255,255,255,170)",
                 groove="rgba(200,50,110,50)", panel=(255, 226, 238, 246),
                 border=(214, 60, 120, 80), card_rgba=(255, 255, 255, 140),
                 track=(214, 60, 120, 45), play_bg=(224, 64, 128), play_fg=(255, 255, 255),
                 pill=(66, 22, 48), accent="#e0407f", eq="dots",
                 eq_pill=("#ff7eb6", "#ffd0e4"), eq_card=("#e0407f", "#ffa3c9"),
                 wave=(0.75, 1.05)),
    # неон: ночной фиолетовый с голубой окантовкой, эквалайзер из светящихся блоков
    "neon": dict(name="Неон", fg="#e9f4ff", sub="#8f95d0", card="rgba(130,120,255,28)",
                 card_hi="rgba(130,120,255,52)", chip="rgba(0,229,255,52)",
                 chipfg="#ffffff", hover="rgba(0,229,255,30)", field="rgba(130,120,255,36)",
                 groove="rgba(150,140,255,70)", panel=(14, 10, 34, 250), border=(0, 229, 255, 95),
                 card_rgba=(130, 120, 255, 28), track=(150, 140, 255, 70),
                 play_bg=(0, 229, 255), play_fg=(8, 6, 28),
                 pill=(18, 8, 42), accent="#00e5ff", eq="blocks",
                 eq_pill=("#00e5ff", "#ff3df0"), eq_card=("#00e5ff", "#ff3df0"),
                 wave=(1.6, 0.9)),
}
THEME_ORDER = ["light", "dark", "pink", "neon"]
PET_ORDER = ["cat", "fox", "ghost", "sprout", "imp", "none"]
PET_NAMES = {"cat": "Кот", "fox": "Лиса", "ghost": "Призрак", "sprout": "Росток",
             "imp": "Проказник", "none": "Без питомца"}

STYLE_TPL = Template("""
QWidget { background: transparent; color: $fg;
          font-family: 'Segoe UI Variable Text','Segoe UI'; font-size: 13px; }
QToolTip { background: #2c2c2e; color: white; border: 0; padding: 4px; }
QWidget#card { background: $card; border-radius: 18px; }
QLabel#sub { color: $sub; }
QLabel#wcell { background: $card; border-radius: 14px; padding: 6px 2px; font-size: 12px;
               color: $sub; }
QListWidget, QPlainTextEdit { background: $card; border: 0; border-radius: 16px; padding: 6px; }
QListWidget::item { padding: 5px; border-radius: 8px; }
QListWidget::item:hover { background: $hover; }
QPushButton { background: $card; border-radius: 12px; padding: 7px 16px; }
QPushButton:hover { background: $card_hi; }
QSpinBox, QLineEdit { background: $field; border-radius: 10px; padding: 5px 8px; border: 0; }
QPushButton#fn { background: $card; border-radius: 16px; text-align: left; padding: 0 14px;
                 font-size: 13px; font-weight: 500; }
QPushButton#fn:hover { background: $card_hi; }
QPushButton#nav { background: transparent; color: $sub; border-radius: 17px;
        padding: 0 10px; min-height: 34px; max-height: 34px; min-width: 14px;
        font-size: 13px; font-weight: 600; }
QPushButton#nav:hover { background: $hover; color: $fg; }
QPushButton#nav:checked { background: $chip; color: $chipfg; }
QPushButton#seg { background: $card; border-radius: 12px; padding: 7px 18px; color: $sub; }
QPushButton#seg:checked { background: $chip; color: $chipfg; }
QPushButton#seg:disabled { color: $groove; }
QPushButton#pick { background: $card; border-radius: 14px; padding: 0; text-align: left; }
QPushButton#pick:hover { background: $card_hi; }
QPushButton#tile { background: transparent; border-radius: 14px; padding: 0; }
QPushButton#tile:hover { background: $hover; }
QPushButton#tile:checked { background: $chip; }
QPushButton#dockbtn { background: transparent; border-radius: 12px; padding: 0; }
QPushButton#dockbtn:hover { background: $hover; }
QPushButton#dockadd { background: transparent; border: 2px dashed $groove; border-radius: 12px;
                      color: $sub; font-size: 18px; padding: 0; }
QPushButton#dockadd:hover { background: $hover; }
QPushButton#spk { background: transparent; padding: 0; }
QSlider::groove:horizontal { height: 6px; background: $groove; border-radius: 3px; }
QSlider::sub-page:horizontal { background: $fg; border-radius: 3px; }
QSlider::handle:horizontal { background: $fg; width: 14px; height: 14px; margin: -4px 0;
                             border-radius: 7px; }
""")

# ---------------- погода: коды WMO ----------------
_W = [((0,), "sun", "Ясно"), ((1,), "partly", "Малооблачно"),
      ((2,), "partly", "Переменная облачность"), ((3,), "cloud", "Пасмурно"),
      ((45, 48), "fog", "Туман"), ((51, 53, 55), "rain", "Морось"),
      ((56, 57), "rain", "Ледяная морось"), ((61,), "rain", "Небольшой дождь"),
      ((63,), "rain", "Дождь"), ((65,), "rain", "Сильный дождь"),
      ((66, 67), "rain", "Ледяной дождь"), ((71,), "snow", "Небольшой снег"),
      ((73,), "snow", "Снег"), ((75, 77), "snow", "Сильный снег"),
      ((80, 81, 82), "rain", "Ливень"), ((85, 86), "snow", "Снегопад"),
      ((95,), "storm", "Гроза"), ((96, 99), "storm", "Гроза с градом")]
WMO = {c: (k, t) for codes, k, t in _W for c in codes}
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}


def wmo(code, is_day):
    """Возвращает (вид значка, текст). Ночью солнце заменяется луной."""
    kind, text = WMO.get(code, ("cloud", "—"))
    if not is_day:
        kind = {"sun": "moon", "partly": "partly_night"}.get(kind, kind)
    return kind, text


# ---------------- утилиты ----------------
def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False)
    except OSError:
        pass


def set_cfg(**kw):
    cfg = load_config()
    cfg.update(kw)
    save_config(cfg)


APP_NAME, APP_VERSION = "MiniIsland", "1.0.9"
UPDATE_URL = "https://api.github.com/repos/brutterr/MiniIsland/releases/latest"
RELEASES_PAGE = "https://github.com/brutterr/MiniIsland/releases/latest"
LOG_FILE = os.path.join(HOME, ".island_log.txt")
_logged = set()


def log(msg, once=False):
    """Пишет диагностику в ~/.island_log.txt (чтобы было что прислать при ошибке)."""
    if once:
        if msg in _logged:
            return
        _logged.add(msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except OSError:
        pass


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def launch_command():
    """Команда запуска для автозапуска: свой .exe или pythonw + island.py."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        pyw = exe[:-10] + "pythonw.exe"
        if os.path.exists(pyw):
            exe = pyw
    return f'"{exe}" "{os.path.abspath(__file__)}"'


def sync_autostart(on):
    """Включает или выключает автозапуск (HKCU\\...\\Run, права администратора не нужны)."""
    if sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
    except Exception as ex:
        log(f"autostart: {ex}", once=True)


def compass(deg):
    if deg is None:
        return ""
    return ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"][int(((deg + 22.5) % 360) // 45)]


def fmt_mm(x):
    if x < 0.05:
        return "0 мм"
    return (f"{x:.1f}".replace(".", ",") if x < 10 else f"{x:.0f}") + " мм"


def weather_gradient(kind):
    table = {"sun": ("#3f86e0", "#7a9bc2"), "partly": ("#3f86e0", "#7a9bc2"),
             "moon": ("#1f2a55", "#4a5680"), "partly_night": ("#1f2a55", "#4a5680"),
             "cloud": ("#5d6f87", "#8d99aa"), "fog": ("#667789", "#97a3b1"),
             "rain": ("#3a4c6c", "#6a7b95"), "storm": ("#2e3550", "#5a6482"),
             "snow": ("#6f8fb0", "#aebfd1")}
    a, b = table.get(kind, table["cloud"])
    return QColor(a), QColor(b)


def fmt_size(n):
    n = float(n)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or unit == "ГБ":
            return f"{n:.0f} {unit}" if unit == "Б" else f"{n:.1f} {unit}"
        n /= 1024


def fmt_time(sec):
    sec = int(max(sec, 0))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def lerp_c(a, b, t):
    return QColor(*(int(x + (y - x) * t) for x, y in
                    ((a.red(), b.red()), (a.green(), b.green()),
                     (a.blue(), b.blue()), (a.alpha(), b.alpha()))))


_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Pow: op.pow, ast.Mod: op.mod, ast.FloorDiv: op.floordiv}


def calc_text(t):
    """Безопасный калькулятор. Возвращает строку результата или None."""
    if not (re.fullmatch(r"[\d\s.,+\-*/^%()×÷]+", t) and re.search(r"\d", t)
            and re.search(r"[+\-*/^%×÷]", t)):
        return None
    expr = t.replace(",", ".").replace("^", "**").replace("×", "*").replace("÷", "/")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 1000:
                raise ValueError
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = ev(n.operand)
            return v if isinstance(n.op, ast.UAdd) else -v
        raise ValueError

    try:
        return f"{ev(ast.parse(expr.strip(), mode='eval')):.10g}"
    except Exception:
        return None


def default_dock():
    root = os.environ.get("SystemRoot", r"C:\Windows")
    cands = [root + r"\explorer.exe", root + r"\notepad.exe",
             root + r"\System32\WindowsPowerShell\v1.0\powershell.exe",
             root + r"\System32\calc.exe", root + r"\System32\mspaint.exe",
             root + r"\System32\taskmgr.exe"]
    return [c for c in cands if os.path.exists(c)]


def pretty_source(aumid):
    name = aumid.split("!")[1] if "!" in aumid else aumid
    name = name.rsplit("\\", 1)[-1]
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return {"msedge": "Edge"}.get(name.lower(), name).upper()



# ======================= минималистичные значки =======================
def _L(p, a, b, c, d):
    p.drawLine(QLineF(a, b, c, d))


def _P(p, pts, close=False):
    poly = QPolygonF([QPointF(x, y) for x, y in pts])
    (p.drawPolygon if close else p.drawPolyline)(poly)


def _R(p, x, y, w, h, r=0):
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def _C(p, x, y, r):
    p.drawEllipse(QPointF(x, y), r, r)


def draw_icon(p, name, c, filled=False):
    """Рисует линейный значок в системе координат 24x24."""
    if name == "home":
        _P(p, [(3, 11), (12, 3.5), (21, 11)])
        _P(p, [(5.5, 9.5), (5.5, 20), (18.5, 20), (18.5, 9.5)])
    elif name == "clipboard":
        _R(p, 5, 4.5, 14, 16.5, 2.5)
        _R(p, 9, 2.5, 6, 4, 1.5)
    elif name == "download":
        _L(p, 12, 4, 12, 15)
        _P(p, [(7, 10.5), (12, 15.5), (17, 10.5)])
        _L(p, 5, 20, 19, 20)
    elif name == "weather":
        path = QPainterPath()
        path.moveTo(7, 18.5)
        path.cubicTo(3.2, 18.5, 2.6, 12.8, 7.6, 12.2)
        path.cubicTo(8.2, 7.8, 14.8, 7.4, 16.2, 12)
        path.cubicTo(21, 11.6, 21.6, 18.5, 17.5, 18.5)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "timer":
        _C(p, 12, 13.5, 7.5)
        _L(p, 12, 13.5, 12, 9)
        _L(p, 12, 13.5, 15, 15)
        _L(p, 9.5, 3, 14.5, 3)
    elif name == "note":
        _P(p, [(4, 20), (5, 15.5), (16, 4.5), (19.5, 8), (8.5, 19), (4, 20)], True)
        _L(p, 14, 6.5, 17.5, 10)
    elif name == "shelf":
        _P(p, [(3, 12.5), (6.5, 12.5), (8.5, 15.5), (15.5, 15.5), (17.5, 12.5), (21, 12.5)])
        _P(p, [(3, 12.5), (3, 19.5), (21, 19.5), (21, 12.5)])
    elif name == "settings":
        _L(p, 4, 7, 6.5, 7)
        _L(p, 11.5, 7, 20, 7)
        _C(p, 9, 7, 2.5)
        _L(p, 4, 12, 12.5, 12)
        _L(p, 17.5, 12, 20, 12)
        _C(p, 15, 12, 2.5)
        _L(p, 4, 17, 5.5, 17)
        _L(p, 10.5, 17, 20, 17)
        _C(p, 8, 17, 2.5)
    elif name == "pin":
        if filled:
            p.setBrush(c)
        _P(p, [(9, 3.5), (15, 3.5), (14.5, 10), (18, 14), (6, 14), (9.5, 10)], True)
        _L(p, 12, 14, 12, 21)
    elif name == "area":
        pen = p.pen()
        pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        _R(p, 4, 4, 16, 16, 2.5)
    elif name == "screen":
        _R(p, 3, 4.5, 18, 12, 2)
        _L(p, 8.5, 20, 15.5, 20)
        _L(p, 12, 16.5, 12, 20)
    elif name == "ocr":
        _P(p, [(4, 8.5), (4, 4), (8.5, 4)])
        _P(p, [(15.5, 4), (20, 4), (20, 8.5)])
        _P(p, [(20, 15.5), (20, 20), (15.5, 20)])
        _P(p, [(8.5, 20), (4, 20), (4, 15.5)])
        _L(p, 9, 9.5, 15, 9.5)
        _L(p, 12, 9.5, 12, 15.5)
    elif name == "qr":
        _R(p, 4, 4, 6, 6, 1.2)
        _R(p, 14, 4, 6, 6, 1.2)
        _R(p, 4, 14, 6, 6, 1.2)
        p.setBrush(c)
        _R(p, 14, 14, 2.6, 2.6, .6)
        _R(p, 17.6, 17.6, 2.6, 2.6, .6)
    elif name == "pick":
        p.save()
        p.translate(14.5, 9.5)
        p.rotate(45)
        _R(p, -2.8, -8, 5.6, 5, 1.5)
        _P(p, [(-1.8, -3), (-1.8, 5), (0, 8), (1.8, 5), (1.8, -3)])
        p.restore()
    elif name == "clean":
        p.save()
        p.translate(12, 11)
        p.rotate(-45)
        _R(p, -9, -4.5, 18, 9, 2.2)
        _L(p, -2.5, -4.5, -2.5, 4.5)
        p.restore()
        _L(p, 5, 21, 19, 21)
    elif name == "record":
        _C(p, 12, 12, 8)
        p.setBrush(c)
        _C(p, 12, 12, 3.6)
    elif name == "stop":
        p.setBrush(c)
        _R(p, 6.5, 6.5, 11, 11, 2.5)
    elif name == "command":
        _P(p, [(5, 8), (10, 12), (5, 16)])
        _L(p, 12.5, 17, 19, 17)
    elif name == "location":
        p.drawArc(QRectF(5, 3, 14, 14), 205 * 16, -230 * 16)
        _L(p, 5.66, 12.96, 12, 21)
        _L(p, 18.34, 12.96, 12, 21)
        _C(p, 12, 10, 2.6)
    elif name == "search":
        _C(p, 10.5, 10.5, 6)
        _L(p, 15.2, 15.2, 20, 20)
    elif name == "refresh":
        p.drawArc(QRectF(4.5, 4.5, 15, 15), 40 * 16, 280 * 16)
        _P(p, [(18.5, 3), (18.5, 7.4), (14.1, 7.4)])
    elif name == "wind":
        path = QPainterPath()
        path.moveTo(3, 9)
        path.lineTo(13.5, 9)
        path.cubicTo(17.5, 9, 17.5, 4.5, 14, 4.5)
        path.moveTo(3, 13.2)
        path.lineTo(19, 13.2)
        path.cubicTo(22.6, 13.2, 22.6, 18, 19, 18)
        path.moveTo(3, 17.2)
        path.lineTo(9.5, 17.2)
        path.cubicTo(12.4, 17.2, 12.4, 20.8, 9.8, 20.8)
        p.drawPath(path)
    elif name == "drop":
        path = QPainterPath()
        path.moveTo(12, 3.5)
        path.cubicTo(12, 3.5, 6, 10.2, 6, 14.5)
        path.cubicTo(6, 18, 8.7, 20.5, 12, 20.5)
        path.cubicTo(15.3, 20.5, 18, 18, 18, 14.5)
        path.cubicTo(18, 10.2, 12, 3.5, 12, 3.5)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "umbrella":
        path = QPainterPath()
        path.moveTo(3, 12.5)
        path.cubicTo(3, 7.2, 7.4, 4, 12, 4)
        path.cubicTo(16.6, 4, 21, 7.2, 21, 12.5)
        path.closeSubpath()
        p.drawPath(path)
        _L(p, 12, 12.5, 12, 18.5)
        p.drawArc(QRectF(9, 16.5, 3, 4), 180 * 16, 180 * 16)
    elif name in ("sunrise", "sunset"):
        _L(p, 3, 19, 21, 19)
        p.drawArc(QRectF(7, 14, 10, 10), 0, 180 * 16)
        _L(p, 12, 4, 12, 10)
        _P(p, [(9, 7), (12, 4), (15, 7)] if name == "sunrise" else [(9, 7), (12, 10), (15, 7)])
    elif name in ("speaker", "mute"):
        _P(p, [(4, 9.5), (8, 9.5), (13, 5.5), (13, 18.5), (8, 14.5), (4, 14.5)], True)
        if name == "speaker":
            p.drawArc(QRectF(10, 7.5, 7, 9), -60 * 16, 120 * 16)
            p.drawArc(QRectF(9, 4, 12, 16), -55 * 16, 110 * 16)
        else:
            _L(p, 16.5, 9.5, 21, 14.5)
            _L(p, 21, 9.5, 16.5, 14.5)


def make_icon(name, normal, hover=None, on=None, size=20, filled_on=False):
    """QIcon из векторного значка: обычный, при наведении и в нажатом состоянии."""
    def pm(color, filled=False):
        dpr = 2
        pix = QPixmap(size * dpr, size * dpr)
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(size / 24, size / 24)
        col = QColor(color)
        pen = QPen(col, 1.7)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        draw_icon(p, name, col, filled)
        p.end()
        return pix

    icon = QIcon()
    icon.addPixmap(pm(normal), QIcon.Normal, QIcon.Off)
    icon.addPixmap(pm(hover or normal), QIcon.Active, QIcon.Off)
    if on is not None:
        icon.addPixmap(pm(on, filled_on), QIcon.Normal, QIcon.On)
        icon.addPixmap(pm(on, filled_on), QIcon.Active, QIcon.On)
    return icon



# ======================= погода: значки и карточки =======================
def _cloud(p, x, y, s, color):
    p.save()
    p.translate(x, y)
    p.scale(s, s)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    _R(p, 0, 8, 30, 10, 5)
    _C(p, 9, 10, 6.5)
    _C(p, 17.5, 7, 8)
    _C(p, 24.5, 11, 5.5)
    p.restore()


def _sun(p, cx, cy, r):
    col = QColor("#ffc83d")
    p.setPen(Qt.NoPen)
    p.setBrush(col)
    _C(p, cx, cy, r)
    pen = QPen(col, r * 0.28)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    for k in range(8):
        a = k * math.pi / 4
        _L(p, cx + math.cos(a) * r * 1.45, cy + math.sin(a) * r * 1.45,
           cx + math.cos(a) * r * 1.85, cy + math.sin(a) * r * 1.85)


def _moon(p, cx, cy, r):
    full, cut = QPainterPath(), QPainterPath()
    full.addEllipse(QPointF(cx, cy), r, r)
    cut.addEllipse(QPointF(cx + r * 0.55, cy - r * 0.3), r * 0.85, r * 0.85)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#ffe7a3"))
    p.drawPath(full.subtracted(cut))


def draw_weather_icon(p, kind):
    """Цветные значки погоды в системе координат 48x48."""
    light, grey, dark = QColor("#eef2f8"), QColor("#b9c4d6"), QColor("#8e9bb1")
    if kind == "sun":
        _sun(p, 24, 24, 9)
    elif kind == "moon":
        _moon(p, 24, 24, 12)
    elif kind == "partly":
        _sun(p, 18, 17, 7.5)
        _cloud(p, 8, 18, 1.2, light)
    elif kind == "partly_night":
        _moon(p, 17, 17, 9)
        _cloud(p, 8, 18, 1.2, light)
    elif kind == "cloud":
        _cloud(p, 4, 12, 1.3, grey)
    elif kind == "rain":
        _cloud(p, 4, 6, 1.3, grey)
        pen = QPen(QColor("#5aa9ff"), 2.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        for x in (15, 24, 33):
            _L(p, x, 34, x - 2.5, 41)
    elif kind == "snow":
        _cloud(p, 4, 6, 1.3, light)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#d6ecff"))
        for x, y in ((14, 37), (24, 40), (34, 37)):
            _C(p, x, y, 2.3)
    elif kind == "storm":
        _cloud(p, 4, 5, 1.3, dark)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ffd23f"))
        _P(p, [(26, 26), (19, 37), (24.5, 37), (21.5, 46), (32, 33), (26, 33), (29, 26)], True)
    elif kind == "fog":
        _cloud(p, 4, 6, 1.3, light)
        pen = QPen(QColor("#c7d0de"), 2.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        _L(p, 10, 35, 38, 35)
        _L(p, 14, 41, 34, 41)


class WeatherIcon(QWidget):
    def __init__(self, size=28):
        super().__init__()
        self.kind = ""
        self.setFixedSize(size, size)

    def set_kind(self, k):
        if k != self.kind:
            self.kind = k
            self.update()

    def paintEvent(self, e):
        if not self.kind:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(self.width() / 48.0, self.height() / 48.0)
        draw_weather_icon(p, self.kind)


class WeatherCard(QWidget):
    """Цветная карточка с текущей погодой; цвет зависит от состояния неба."""

    def __init__(self):
        super().__init__()
        self.c1, self.c2 = QColor("#3f86e0"), QColor("#7a9bc2")

    def set_colors(self, a, b):
        self.c1, self.c2 = a, b
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, self.c1)
        g.setColorAt(1, self.c2)
        p.setBrush(g)
        p.drawRoundedRect(QRectF(self.rect()), 22, 22)


class RangeBar(QWidget):
    """Полоса диапазона температур дня на фоне всей недели."""
    STOPS = [(-10, "#6ab0ff"), (0, "#7fc4e8"), (10, "#a9d98c"), (18, "#f0d977"),
             (26, "#f5a45f"), (34, "#ee6a55")]

    def __init__(self):
        super().__init__()
        self.lo = self.hi = self.gmin = self.gmax = 0.0
        self.setFixedHeight(14)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_range(self, lo, hi, gmin, gmax):
        self.lo, self.hi, self.gmin, self.gmax = lo, hi, gmin, gmax
        self.update()

    @classmethod
    def color(cls, t):
        if t <= cls.STOPS[0][0]:
            return QColor(cls.STOPS[0][1])
        for (t0, c0), (t1, c1) in zip(cls.STOPS, cls.STOPS[1:]):
            if t <= t1:
                return lerp_c(QColor(c0), QColor(c1), (t - t0) / float(t1 - t0))
        return QColor(cls.STOPS[-1][1])

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        w, h, th = self.width(), self.height(), 5
        y = (h - th) / 2
        p.setBrush(QColor(128, 128, 128, 55))
        p.drawRoundedRect(QRectF(0, y, w, th), th / 2, th / 2)
        span = max(self.gmax - self.gmin, 0.1)
        x0 = (self.lo - self.gmin) / span * w
        x1 = max((self.hi - self.gmin) / span * w, x0 + th)
        g = QLinearGradient(x0, 0, x1, 0)
        g.setColorAt(0, self.color(self.lo))
        g.setColorAt(1, self.color(self.hi))
        p.setBrush(g)
        p.drawRoundedRect(QRectF(x0, y, x1 - x0, th), th / 2, th / 2)


class ClickSlider(QSlider):
    """Слайдер: клик в любое место сразу ставит значение, дальше можно тянуть."""

    def _val(self, x):
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(),
                                              int(x - 7), max(1, self.width() - 14))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setSliderDown(True)
            self.setValue(self._val(e.position().x()))
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.isSliderDown():
            self.setValue(self._val(e.position().x()))
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.isSliderDown():
            self.setSliderDown(False)
            e.accept()
        else:
            super().mouseReleaseEvent(e)


# ======================= маленькие виджеты =======================
class ElideLabel(QLabel):
    """Текст, который сам обрезается многоточием."""

    def __init__(self, text=""):
        super().__init__()
        self._full = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(10)

    def setText(self, t):
        self._full = t
        self._apply()

    def resizeEvent(self, e):
        self._apply()
        super().resizeEvent(e)

    def _apply(self):
        QLabel.setText(self, self.fontMetrics().elidedText(
            self._full, Qt.ElideRight, max(self.width() - 2, 10)))


EQ_PREVIEW = [0.45, 0.95, 0.6, 1.0, 0.5]


def draw_eq(p, rect, vals, style, c1, c2=None):
    """Столбики эквалайзера в стиле темы: bars (штрихи), dots (бусины), blocks (блоки).
    c1 снизу, c2 сверху (если задан, цвет плавно переходит)."""
    x0, y0, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    n = len(vals)
    p.setPen(Qt.NoPen)
    if style == "dots":
        gap = max(1.2, w / (n * 5.0))
        d = (w - gap * (n - 1)) / n
        rows = max(3, int((h - d) // (d + gap)) + 1)
        pitch = (h - d) / (rows - 1)
        for i, v in enumerate(vals):
            x = x0 + i * (d + gap)
            for k in range(max(1, round(v * rows))):
                p.setBrush(lerp_c(c1, c2, k / (rows - 1)) if c2 else c1)
                p.drawEllipse(QRectF(x, y0 + h - d - k * pitch, d, d))
    elif style == "blocks":
        gx = max(1.5, w / (n * 5.0))
        bw = (w - gx * (n - 1)) / n
        rows = 5 if h >= 14 else 4
        bh = (h - (rows - 1)) / rows
        for i, v in enumerate(vals):
            x = x0 + i * (bw + gx)
            for k in range(max(1, round(v * rows))):
                p.setBrush(lerp_c(c1, c2, k / (rows - 1)) if c2 else c1)
                p.drawRoundedRect(QRectF(x, y0 + h - bh - k * (bh + 1), bw, bh), 0.7, 0.7)
    else:
        gap = max(2, w // (n * 3))
        bw = (w - gap * (n - 1)) / n
        for i, v in enumerate(vals):
            bh = max(3.0, h * v)
            x = x0 + i * (bw + gap)
            if c2:
                g = QLinearGradient(0, y0 + h, 0, y0 + h - bh)
                g.setColorAt(0, c1)
                g.setColorAt(1, c2)
                p.setBrush(g)
            else:
                p.setBrush(c1)
            p.drawRoundedRect(QRectF(x, y0 + h - bh, bw, bh), min(bw / 2, 3), min(bw / 2, 3))


class Equalizer(QWidget):
    """Анимированные столбики (визуальный эффект, не реальный спектр). Вид задаёт тема."""

    def __init__(self, bars=5, color="#ffffff"):
        super().__init__()
        self.n = bars
        self.vals = [0.1] * bars
        self.targets = [0.1] * bars
        self.active = False
        self.color = QColor(color)
        self.color2 = None
        self.style = "bars"
        t = QTimer(self)
        t.setInterval(90)
        t.timeout.connect(self.step)
        t.start()

    def set_active(self, a):
        self.active = a

    def step(self):
        for i in range(self.n):
            if self.active:
                if random.random() < 0.6:
                    self.targets[i] = random.uniform(0.2, 1.0)
            else:
                self.targets[i] = 0.1
            self.vals[i] += (self.targets[i] - self.vals[i]) * 0.5
        if self.isVisible():
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        draw_eq(p, QRectF(self.rect()), self.vals, self.style, self.color, self.color2)
        p.end()


class AlbumArt(QWidget):
    """Обложка со скруглёнными углами. Без обложки: градиент с нотой."""

    def __init__(self, radius):
        super().__init__()
        self.radius = radius
        self.pix = None

    def set_pixmap(self, pix):
        self.pix = pix
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), self.radius, self.radius)
        p.setClipPath(path)
        if self.pix and not self.pix.isNull():
            sc = self.pix.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap(0, 0, sc, (sc.width() - w) // 2, (sc.height() - h) // 2, w, h)
        else:
            g = QLinearGradient(0, 0, w, h)
            g.setColorAt(0, QColor("#5e5ce6"))
            g.setColorAt(1, QColor("#bf5af2"))
            p.fillRect(self.rect(), g)
            p.setPen(QColor(255, 255, 255, 230))
            p.setFont(QFont("Segoe UI Symbol", max(8, int(h * 0.42))))
            p.drawText(self.rect(), Qt.AlignCenter, "♪")


class IconButton(QPushButton):
    """Кнопка плеера: prev / play / pause / next, нарисована вручную."""

    def __init__(self, kind, size=44):
        super().__init__()
        self.kind = kind
        self.fg = QColor("#ffffff")
        self.bg = None
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def set_kind(self, k):
        if k != self.kind:
            self.kind = k
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        s = min(self.width(), self.height())
        cx, cy = self.width() / 2, self.height() / 2
        if self.bg is not None:
            p.setBrush(self.bg)
            p.drawEllipse(QPointF(cx, cy), s / 2, s / 2)
        elif self.underMouse():
            hv = QColor(self.fg)
            hv.setAlpha(28)
            p.setBrush(hv)
            p.drawEllipse(QPointF(cx, cy), s / 2, s / 2)
        c = QColor(self.fg)
        c.setAlpha(170 if self.isDown() else 255)
        p.setBrush(c)
        k = self.kind
        if k == "play":
            p.drawPolygon(QPolygonF([QPointF(cx - s * .13, cy - s * .22),
                                     QPointF(cx - s * .13, cy + s * .22),
                                     QPointF(cx + s * .25, cy)]))
        elif k == "pause":
            for dx in (-s * .13, s * .04):
                p.drawRoundedRect(QRectF(cx + dx, cy - s * .21, s * .09, s * .42), 2, 2)
        elif k == "next":
            p.drawPolygon(QPolygonF([QPointF(cx - s * .24, cy - s * .2),
                                     QPointF(cx - s * .24, cy + s * .2),
                                     QPointF(cx + s * .1, cy)]))
            p.drawRoundedRect(QRectF(cx + s * .14, cy - s * .2, s * .07, s * .4), 2, 2)
        elif k == "prev":
            p.drawPolygon(QPolygonF([QPointF(cx + s * .24, cy - s * .2),
                                     QPointF(cx + s * .24, cy + s * .2),
                                     QPointF(cx - s * .1, cy)]))
            p.drawRoundedRect(QRectF(cx - s * .21, cy - s * .2, s * .07, s * .4), 2, 2)


class ProgressBar(QWidget):
    """Тонкий прогресс-бар; клик или перетаскивание = перемотка."""
    seek = Signal(float)

    def __init__(self):
        super().__init__()
        self.frac = 0.0
        self.hover = False
        self.dragging = False
        self.fill = QColor("#ff5b8a")
        self.track = QColor(0, 0, 0, 40)
        self.setFixedHeight(16)
        self.setCursor(Qt.PointingHandCursor)

    def set_fraction(self, f):
        self.frac = max(0.0, min(1.0, f))
        self.update()

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def _set_x(self, x):
        self.frac = max(0.0, min(1.0, x / max(self.width(), 1)))
        self.update()

    def mousePressEvent(self, e):
        self.dragging = True
        self._set_x(e.position().x())

    def mouseMoveEvent(self, e):
        if self.dragging:
            self._set_x(e.position().x())

    def mouseReleaseEvent(self, e):
        if self.dragging:
            self.dragging = False
            self.seek.emit(self.frac)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        w, h = self.width(), self.height()
        th = 7 if (self.hover or self.dragging) else 5
        y = (h - th) / 2
        p.setBrush(self.track)
        p.drawRoundedRect(QRectF(0, y, w, th), th / 2, th / 2)
        p.setBrush(self.fill)
        p.drawRoundedRect(QRectF(0, y, max(th, w * self.frac), th), th / 2, th / 2)


class PlayerCard(QWidget):
    """Карточка плеера с мягким цветным свечением от обложки."""

    def __init__(self):
        super().__init__()
        self.base = QColor(255, 255, 255, 150)
        self.tint = None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        r = QRectF(self.rect())
        p.setBrush(self.base)
        p.drawRoundedRect(r, 20, 20)
        if self.tint:
            g = QLinearGradient(0, 0, r.width(), r.height())
            c1, c2 = QColor(self.tint), QColor(self.tint)
            c1.setAlpha(95)
            c2.setAlpha(15)
            g.setColorAt(0, c1)
            g.setColorAt(1, c2)
            p.setBrush(g)
            p.drawRoundedRect(r, 20, 20)


# ======================= экран: выделение области и пипетка =======================
class ScreenOverlay(QWidget):
    """Полноэкранный оверлей. mode='region' -> QImage, mode='pick' -> QColor, отмена -> None."""
    done = Signal(object)

    def __init__(self, pix, mode):
        super().__init__()
        self.pix, self.mode = pix, mode
        self.dpr = pix.devicePixelRatio()
        self.img = pix.toImage() if mode == "pick" else None
        self.start = None
        self.cur = QPoint(-100, -100)
        self.finished = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

    def show_full(self):
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def finish(self, value):
        if self.finished:
            return
        self.finished = True
        self.hide()
        self.done.emit(value)
        self.deleteLater()

    def _src(self, r):
        d = self.dpr
        return QRect(int(r.x() * d), int(r.y() * d), int(r.width() * d), int(r.height() * d))

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.pix)
        if self.mode == "region":
            p.fillRect(self.rect(), QColor(0, 0, 0, 110))
            if self.start is not None:
                r = QRect(self.start, self.cur).normalized()
                p.drawPixmap(r, self.pix, self._src(r))
                p.setPen(QPen(QColor("#ffffff"), 2))
                p.setBrush(Qt.NoBrush)
                p.drawRect(r)
                p.setPen(QColor("white"))
                p.drawText(r.x(), max(14, r.y() - 6), f"{r.width()} × {r.height()}")
        else:
            self.paint_magnifier(p)

    def paint_magnifier(self, p):
        px, py = int(self.cur.x() * self.dpr), int(self.cur.y() * self.dpr)
        px = max(0, min(px, self.img.width() - 1))
        py = max(0, min(py, self.img.height() - 1))
        col = self.img.pixelColor(px, py)
        size = 120
        x, y = self.cur.x() + 26, self.cur.y() + 26
        if x + size > self.width():
            x = self.cur.x() - 26 - size
        if y + size + 30 > self.height():
            y = self.cur.y() - 26 - size - 30
        target = QRect(x, y, size, size)
        p.setRenderHint(QPainter.Antialiasing)
        p.save()
        path = QPainterPath()
        path.addEllipse(QRectF(target))
        p.setClipPath(path)
        p.fillRect(target, QColor(0, 0, 0))
        p.drawPixmap(target, self.pix, QRect(px - 7, py - 7, 15, 15))
        p.restore()
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("white"), 3))
        p.drawEllipse(QRectF(target))
        cell = size / 15
        p.setPen(QPen(QColor(0, 0, 0), 2))
        p.drawRect(QRectF(x + cell * 7, y + cell * 7, cell, cell))
        box = QRect(x + 10, y + size + 4, size - 20, 24)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 200))
        p.drawRoundedRect(box, 10, 10)
        p.setBrush(col)
        p.drawEllipse(QRectF(box.x() + 6, box.y() + 5, 14, 14))
        p.setPen(QColor("white"))
        p.drawText(box.adjusted(26, 0, 0, 0), Qt.AlignVCenter, col.name().upper())

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.finish(None)
            return
        self.cur = e.position().toPoint()
        if self.mode == "pick":
            px = max(0, min(int(self.cur.x() * self.dpr), self.img.width() - 1))
            py = max(0, min(int(self.cur.y() * self.dpr), self.img.height() - 1))
            self.finish(self.img.pixelColor(px, py))
        else:
            self.start = self.cur
            self.update()

    def mouseMoveEvent(self, e):
        self.cur = e.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, e):
        if self.mode == "region" and self.start is not None:
            r = QRect(self.start, self.cur).normalized()
            if r.width() > 4 and r.height() > 4:
                self.finish(self.pix.copy(self._src(r)).toImage())
            else:
                self.finish(None)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.finish(None)


# ======================= OCR, запись экрана, громкость =======================
class OcrWorker(QObject):
    """Распознавание текста встроенным OCR Windows."""
    result = Signal(str, str)  # текст, ошибка

    def run(self, img):
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        img.save(buf, "PNG")
        threading.Thread(target=self._thread, args=(bytes(buf.data()),), daemon=True).start()

    def _thread(self, data):
        try:
            self.result.emit(asyncio.run(self._ocr(data)), "")
        except Exception as e:
            self.result.emit("", str(e) or e.__class__.__name__)

    @staticmethod
    async def _ocr(data):
        from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.media.ocr import OcrEngine
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream.get_output_stream_at(0))
        writer.write_bytes(bytearray(data))
        await writer.store_async()
        stream.seek(0)
        decoder = await BitmapDecoder.create_async(stream)
        bmp = await decoder.get_software_bitmap_async()
        engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            raise RuntimeError("не установлен язык для OCR")
        return (await engine.recognize_async(bmp)).text


class Recorder:
    """Запись экрана в MP4 (mss + OpenCV), в отдельном потоке."""

    def __init__(self):
        self.thread = None
        self.stop_ev = threading.Event()
        self.error = None

    @property
    def active(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, path, fps=12):
        import cv2  # noqa: F401  (проверяем, что пакеты установлены)
        import mss  # noqa: F401
        import numpy  # noqa: F401
        self.error = None
        self.stop_ev.clear()
        self.thread = threading.Thread(target=self._run, args=(path, fps), daemon=True)
        self.thread.start()

    def _run(self, path, fps):
        try:
            import cv2
            import mss
            import numpy as np
            with mss.mss() as sct:
                mon = sct.monitors[1]
                out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps,
                                      (mon["width"], mon["height"]))
                period, nxt = 1.0 / fps, time.time()
                while not self.stop_ev.is_set():
                    frame = np.ascontiguousarray(np.array(sct.grab(mon))[:, :, :3])
                    out.write(frame)
                    nxt += period
                    delay = nxt - time.time()
                    if delay > 0:
                        time.sleep(delay)
                    else:
                        nxt = time.time()
                out.release()
        except Exception as e:
            self.error = str(e)

    def stop(self):
        self.stop_ev.set()
        if self.thread:
            self.thread.join(timeout=5)


class Volume:
    """Системная громкость: напрямую через Core Audio, запасной вариант pycaw."""

    def __init__(self, core=None):
        self.core, self.ep, self._err = core, None, ""
        if core is None or not core.ok:
            self._init_pycaw()

    def _init_pycaw(self):
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER
            dev = AudioUtilities.GetSpeakers()
            if hasattr(dev, "EndpointVolume"):
                self.ep = dev.EndpointVolume
            else:
                iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.ep = cast(iface, POINTER(IAudioEndpointVolume))
        except Exception as e:
            self.ep = None
            self._err = f"pycaw: {e.__class__.__name__}: {e}"
            log("Volume " + self._err, once=True)

    @property
    def error(self):
        if self.core is not None and not self.core.ok and self.core.error:
            return self.core.error
        return self._err

    def _core(self):
        return self.core is not None and self.core.ok

    @property
    def ok(self):
        return self._core() or self.ep is not None

    def get(self):
        if self._core():
            return self.core.get_volume()
        try:
            return round(self.ep.GetMasterVolumeScalar() * 100)
        except Exception:
            return None

    def set(self, v):
        if self._core():
            self.core.set_volume(v)
            return
        try:
            self.ep.SetMasterVolumeScalar(max(0.0, min(1.0, v / 100)), None)
        except Exception:
            pass

    def muted(self):
        if self._core():
            return self.core.get_mute()
        try:
            return bool(self.ep.GetMute())
        except Exception:
            return False

    def toggle_mute(self):
        if self._core():
            self.core.set_mute(not self.core.get_mute())
            return
        try:
            self.ep.SetMute(0 if self.muted() else 1, None)
        except Exception:
            pass


class HotkeyFilter(QAbstractNativeEventFilter):
    """Глобальная горячая клавиша Alt+Space (только Windows)."""

    def __init__(self, callback):
        super().__init__()
        self.cb = callback

    def nativeEventFilter(self, event_type, message):
        try:
            if bytes(event_type) == b"windows_generic_MSG":
                import ctypes.wintypes
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == 0x0312 and msg.wParam == 1:  # WM_HOTKEY
                    QTimer.singleShot(0, self.cb)
        except Exception:
            pass
        return False, 0


# ======================= командная строка =======================
class CommandBar(QWidget):
    submitted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QWidget{background:transparent;color:white;"
                           "font-family:'Segoe UI Variable Text','Segoe UI';}"
                           "QLineEdit{background:transparent;border:0;font-size:20px;}"
                           "QLabel{color:#9a9aa0;font-size:12px;}")
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 16, 24, 14)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Программа, ссылка, 2+2, таймер 10 мин, найти…")
        self.hint = QLabel("Enter — выполнить · Esc — закрыть")
        v.addWidget(self.edit)
        v.addWidget(self.hint)
        self.edit.returnPressed.connect(self.submit)
        self.edit.textChanged.connect(self.on_text)
        self.resize(620, 96)

    def popup(self):
        scr = QApplication.primaryScreen().geometry()
        self.move(scr.x() + (scr.width() - self.width()) // 2, scr.y() + int(scr.height() * .22))
        self.edit.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self.edit.setFocus()

    def on_text(self, t):
        r = calc_text(t.strip())
        self.hint.setText(f"= {r}" if r else "Enter — выполнить · Esc — закрыть")

    def submit(self):
        t = self.edit.text()
        self.hide()
        if t.strip():
            self.submitted.emit(t)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(e)

    def event(self, e):
        if e.type() == QEvent.WindowDeactivate:
            self.hide()
        return super().event(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(28, 28, 31, 245))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 28, 28)


# ======================= музыка (Windows) =======================
class MediaWorker(QObject):
    """Читает текущую медиа-сессию Windows (Spotify, браузер, Яндекс Музыка...)."""
    changed = Signal(str, str, bool, bool, float, float, str)
    thumb = Signal(object)

    def __init__(self):
        super().__init__()
        self.loop = None
        self.manager = None
        self._key = "init"
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._poll())

    async def _thumbnail(self, props):
        try:
            ref = props.thumbnail
            if not ref:
                return b""
            stream = await ref.open_read_async()
            size = int(stream.size)
            if size <= 0:
                return b""
            from winrt.windows.storage.streams import DataReader
            reader = DataReader(stream)
            await reader.load_async(size)
            data = bytearray(size)
            reader.read_bytes(data)
            return bytes(data)
        except Exception:
            return b""

    async def _poll(self):
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as Manager)
            self.manager = await Manager.request_async()
        except Exception:
            self.changed.emit("", "", False, False, 0.0, 0.0, "")
            return
        while True:
            try:
                s = self.manager.get_current_session()
                if s:
                    props = await s.try_get_media_properties_async()
                    info = s.get_playback_info()
                    playing = int(info.playback_status) == 4
                    pos = dur = 0.0
                    try:
                        tl = s.get_timeline_properties()
                        dur = (tl.end_time - tl.start_time).total_seconds()
                        pos = tl.position.total_seconds()
                        if playing:
                            try:
                                pos += (datetime.now(timezone.utc)
                                        - tl.last_updated_time).total_seconds()
                            except Exception:
                                pass
                        if dur > 0:
                            pos = max(0.0, min(pos, dur))
                    except Exception:
                        pass
                    src = ""
                    try:
                        src = pretty_source(s.source_app_user_model_id or "")
                    except Exception:
                        pass
                    self.changed.emit(props.title or "", props.artist or "",
                                      playing, True, float(pos), float(dur), src)
                    key = (props.title, props.artist)
                    if key != self._key:
                        self._key = key
                        self.thumb.emit(await self._thumbnail(props))
                else:
                    self.changed.emit("", "", False, True, 0.0, 0.0, "")
                    if self._key is not None:
                        self._key = None
                        self.thumb.emit(b"")
            except Exception:
                pass
            await asyncio.sleep(1)

    def _cmd(self, name, *args):
        if not self.loop:
            return

        async def go():
            s = self.manager.get_current_session() if self.manager else None
            if s:
                await getattr(s, name)(*args)

        asyncio.run_coroutine_threadsafe(go(), self.loop)

    def toggle(self):
        self._cmd("try_toggle_play_pause_async")

    def next(self):
        self._cmd("try_skip_next_async")

    def prev(self):
        self._cmd("try_skip_previous_async")

    def seek(self, seconds):
        self._cmd("try_change_playback_position_async", int(seconds * 10_000_000))


# ======================= погода (Open-Meteo, без ключа) =======================
class WeatherWorker(QObject):
    updated = Signal(object)

    def refresh(self, city=None):
        threading.Thread(target=self._fetch, args=(city,), daemon=True).start()

    @staticmethod
    def _get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "mini-island"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    def _fetch(self, city):
        try:
            cfg = load_config()
            if city:
                geo = self._get("https://geocoding-api.open-meteo.com/v1/search?"
                                + urlencode({"name": city, "count": 1, "language": "ru"}))
                res = (geo.get("results") or [None])[0]
                if not res:
                    self.updated.emit({"error": "Город не найден"})
                    return
                set_cfg(city=res["name"], lat=res["latitude"], lon=res["longitude"])
                cfg = load_config()
            elif not cfg.get("lat"):
                ip = self._get("https://ipwho.is/")
                set_cfg(city=ip.get("city", ""), lat=ip["latitude"], lon=ip["longitude"])
                cfg = load_config()
            data = self._get("https://api.open-meteo.com/v1/forecast?" + urlencode({
                "latitude": cfg["lat"], "longitude": cfg["lon"],
                "current": "temperature_2m,apparent_temperature,weather_code,is_day,"
                           "relative_humidity_2m,wind_speed_10m,wind_direction_10m",
                "hourly": "temperature_2m,weather_code,precipitation_probability,is_day",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                         "precipitation_sum,sunrise,sunset",
                "wind_speed_unit": "ms", "timezone": "auto", "forecast_days": 7}))
            data["city"] = cfg.get("city", "")
            self.updated.emit(data)
        except Exception:
            self.updated.emit({"error": "Нет связи. Введи город вручную или проверь интернет"})


# ======================= буфер обмена: карточки =======================
def css_color(text):
    m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", text)
    return QColor(int(m[1]), int(m[2]), int(m[3]), int(m[4])) if m else QColor(text)


# вид записи: (значок, цвет, название)
CLIP_KINDS = {"text": ("Aa", "#8e8e93", "Текст"), "link": ("\u2197", "#0a84ff", "Ссылка"),
              "mail": ("@", "#30b0c7", "Почта"), "number": ("#", "#ff9f0a", "Число"),
              "color": ("", "#ff375f", "Цвет"), "image": ("", "#bf5af2", "Изображение")}


def classify_clip(text):
    """Определяет вид текста и готовит строки для карточки: (вид, заголовок, подпись)."""
    t = text.strip()
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    title = (lines[0] if lines else t)[:200]
    if re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})", t):
        return "color", t.upper(), "Цвет"
    if re.fullmatch(r"(?:https?://|www\.)\S+", t, re.I):
        host = re.sub(r"^(?:https?://)?(?:www\.)?", "", t, flags=re.I).split("/")[0]
        return "link", t, f"Ссылка · {host}"
    if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", t):
        return "mail", t, "Почта"
    if len(t) >= 4 and re.fullmatch(r"[\d\s.,+\-()]+", t) and re.search(r"\d{3}", t):
        return "number", t, "Число"
    n = len(lines)
    meta = f"{n} стр. · {len(t)} симв." if n > 1 else f"{len(t)} симв."
    return "text", title, f"Текст · {meta}"


def rel_time(ts):
    d = time.time() - ts
    if d < 45:
        return "сейчас"
    if d < 3600:
        return f"{max(1, int(d // 60))} мин"
    if d < 86400:
        return f"{int(d // 3600)} ч"
    return datetime.fromtimestamp(ts).strftime("%d.%m")


class ClipDelegate(QStyledItemDelegate):
    PAD = 10

    def __init__(self, view):
        super().__init__(view)
        self.view = view

    def sizeHint(self, opt, idx):
        return QSize(max(opt.rect.width(), 10), 88 if idx.data(KIND_ROLE) == "image" else 62)

    def del_rect(self, rect):
        return QRect(rect.right() - self.PAD - 24, rect.center().y() - 12, 24, 24)

    def paint(self, p, opt, idx):
        v, C = self.view, self.view.colors
        kind = idx.data(KIND_ROLE) or "text"
        glyph, tint, _label = CLIP_KINDS[kind]
        tint = QColor(tint)
        r = QRectF(opt.rect).adjusted(0, 0, -1, 0)
        hover = bool(opt.state & QStyle.State_MouseOver)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(C["card_hi"] if hover else C["card"])
        p.drawRoundedRect(r, 14, 14)

        # --- значок слева ---
        pad = self.PAD
        if kind == "image":
            tile = QRectF(r.left() + pad, r.top() + pad, 76, r.height() - 2 * pad)
        else:
            tile = QRectF(r.left() + pad, r.center().y() - 21, 42, 42)
        if kind == "image":
            pm = idx.data(THUMB_ROLE)
            if pm is not None:
                path = QPainterPath()
                path.addRoundedRect(tile, 10, 10)
                p.setClipPath(path)
                p.drawPixmap(tile.toRect(), pm)
                p.setClipping(False)
        elif kind == "color":
            p.setBrush(QColor(idx.data(Qt.UserRole).strip()))
            p.setPen(QPen(QColor(128, 128, 128, 90), 1))
            p.drawRoundedRect(tile, 11, 11)
            p.setPen(Qt.NoPen)
        else:
            bg = QColor(tint)
            bg.setAlpha(46)
            p.setBrush(bg)
            p.drawRoundedRect(tile, 11, 11)
            f = QFont(opt.font)
            f.setPixelSize(16 if glyph != "Aa" else 15)
            f.setWeight(QFont.Bold)
            p.setFont(f)
            p.setPen(tint)
            p.drawText(tile, Qt.AlignCenter, glyph)

        # --- две строки текста ---
        left = tile.right() + 12
        right = r.right() - pad - 56
        y0 = r.center().y() - 18
        f = QFont(opt.font)
        f.setPixelSize(13)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(C["fg"])
        title = idx.data(TITLE_ROLE) or ""
        p.drawText(QRectF(left, y0, max(right - left, 10), 18), Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(title, Qt.ElideRight, int(max(right - left, 10))))
        f2 = QFont(opt.font)
        f2.setPixelSize(12)
        p.setFont(f2)
        p.setPen(C["sub"])
        sub_w = max(r.right() - pad - left - 4, 10)
        p.drawText(QRectF(left, y0 + 20, sub_w, 16), Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(idx.data(SUB_ROLE) or "", Qt.ElideRight, int(sub_w)))

        # --- справа: время, а при наведении кнопка удаления ---
        if hover:
            dr = QRectF(self.del_rect(opt.rect))
            over = v.mouse_pos is not None and self.del_rect(opt.rect).contains(v.mouse_pos)
            if over:
                p.setPen(Qt.NoPen)
                p.setBrush(C["hover"])
                p.drawEllipse(dr)
            p.setPen(QPen(C["fg"] if over else C["sub"], 1.6, Qt.SolidLine, Qt.RoundCap))
            c = dr.center()
            p.drawLine(QPointF(c.x() - 4, c.y() - 4), QPointF(c.x() + 4, c.y() + 4))
            p.drawLine(QPointF(c.x() - 4, c.y() + 4), QPointF(c.x() + 4, c.y() - 4))
        else:
            f3 = QFont(opt.font)
            f3.setPixelSize(11)
            p.setFont(f3)
            p.setPen(C["sub"])
            p.drawText(QRectF(r.right() - pad - 52, y0, 52, 18), Qt.AlignVCenter | Qt.AlignRight,
                       rel_time(idx.data(TIME_ROLE) or time.time()))

        # --- подтверждение копирования ---
        copied = idx.data(COPIED_ROLE)
        if copied and time.time() - copied < 1.4:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(48, 209, 88, 205))
            p.drawRoundedRect(r, 14, 14)
            f4 = QFont(opt.font)
            f4.setPixelSize(14)
            f4.setWeight(QFont.Bold)
            p.setFont(f4)
            p.setPen(QColor("white"))
            p.drawText(r, Qt.AlignCenter, "\u2713  Скопировано")
        p.restore()


class ClipView(QListWidget):
    removeRequested = Signal(object)

    def __init__(self):
        super().__init__()
        self.mouse_pos = None
        self.hint = ""
        self.colors = {k: QColor() for k in ("card", "card_hi", "fg", "sub", "hover")}
        self.setItemDelegate(ClipDelegate(self))
        self.setMouseTracking(True)
        self.setSpacing(3)
        self.setFrameShape(QListWidget.NoFrame)
        self.setSelectionMode(QListWidget.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(24)
        self.viewport().setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QListWidget { background: transparent; border: 0; padding: 0; }"
            "QListWidget::item { background: transparent; padding: 0; margin: 0; }"
            "QScrollBar:vertical { width: 6px; background: transparent; margin: 4px 0; }"
            "QScrollBar::handle:vertical { background: rgba(128,128,128,110);"
            " border-radius: 3px; min-height: 28px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }")

    def set_colors(self, T):
        self.colors = {"card": css_color(T["card"]), "card_hi": css_color(T["card_hi"]),
                       "fg": QColor(T["fg"]), "sub": QColor(T["sub"]),
                       "hover": css_color(T["hover"])}
        self.viewport().update()

    def mouseMoveEvent(self, e):
        self.mouse_pos = e.position().toPoint()
        self.viewport().update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self.mouse_pos = None
        self.viewport().update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        pos = e.position().toPoint()
        it = self.itemAt(pos)
        if (it is not None and e.button() == Qt.LeftButton
                and self.itemDelegate().del_rect(self.visualItemRect(it)).contains(pos)):
            self.removeRequested.emit(it)   # клик по крестику: удалить, а не копировать
            return
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.hint:
            p = QPainter(self.viewport())
            p.setRenderHint(QPainter.TextAntialiasing)
            f = QFont(self.font())
            f.setPixelSize(14)
            p.setFont(f)
            p.setPen(self.colors["sub"])
            p.drawText(self.viewport().rect().adjusted(20, 0, -20, 0),
                       Qt.AlignCenter | Qt.TextWordWrap, self.hint)


# ======================= загрузки: карточки =======================
# вид файла: (цвет, название, расширения)
DL_KINDS = [("#bf5af2", "Изображение", "jpg jpeg png gif webp bmp svg heic ico tiff"),
            ("#ff375f", "Видео", "mp4 mkv avi mov webm wmv flv m4v"),
            ("#ff9f0a", "Аудио", "mp3 wav flac ogg m4a aac opus wma"),
            ("#e0a800", "Архив", "zip rar 7z tar gz bz2 xz iso"),
            ("#0a84ff", "Документ", "pdf doc docx txt rtf odt xls xlsx ppt pptx csv epub fb2 md"),
            ("#27b85a", "Программа", "exe msi apk bat cmd ps1 jar dmg")]
DL_OTHER = ("#8e8e93", "Файл")


def dl_kind(name):
    ext = os.path.splitext(name)[1].lstrip(".").lower()
    for color, label, exts in DL_KINDS:
        if ext in exts.split():
            return color, label, ext
    return DL_OTHER[0], DL_OTHER[1], ext


def recent_downloads(limit=40):
    """Последние файлы из папки загрузок: чтобы вкладка не была пустой после запуска."""
    out = []
    try:
        for name in os.listdir(DL_DIR):
            path = os.path.join(DL_DIR, name)
            low = name.lower()
            if (low.endswith(PARTIAL_EXT) or name.startswith((".", "~$"))
                    or low == "desktop.ini" or not os.path.isfile(path)):
                continue
            try:
                out.append({"name": name, "path": path, "size": os.path.getsize(path),
                            "t": os.path.getmtime(path)})
            except OSError:
                continue
    except OSError:
        return []
    out.sort(key=lambda d: d["t"], reverse=True)
    return out[:limit]


class DlDelegate(ClipDelegate):
    def sizeHint(self, opt, idx):
        return QSize(max(opt.rect.width(), 10), 66)

    def del_rect(self, rect):
        return QRect(rect.right() - self.PAD - 24, rect.center().y() - 12, 24, 24)

    def dir_rect(self, rect):
        return QRect(rect.right() - self.PAD - 24 - 28, rect.center().y() - 12, 24, 24)

    def _button(self, p, rect, over, C, draw):
        if over:
            p.setPen(Qt.NoPen)
            p.setBrush(C["hover"])
            p.drawEllipse(QRectF(rect))
        p.setPen(QPen(C["fg"] if over else C["sub"], 1.6, Qt.SolidLine, Qt.RoundCap,
                      Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        draw(QRectF(rect).center())

    def paint(self, p, opt, idx):
        v, C = self.view, self.view.colors
        active = idx.data(KIND_ROLE) == "active"
        tint = QColor("#0a84ff" if active else idx.data(THUMB_ROLE))
        r = QRectF(opt.rect).adjusted(0, 0, -1, 0)
        hover = bool(opt.state & QStyle.State_MouseOver)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(C["card_hi"] if hover else C["card"])
        p.drawRoundedRect(r, 14, 14)

        pad = self.PAD
        tile = QRectF(r.left() + pad, r.center().y() - 21, 42, 42)
        bg = QColor(tint)
        bg.setAlpha(46)
        p.setBrush(bg)
        p.drawRoundedRect(tile, 11, 11)
        label = "\u2193" if active else (idx.data(FIND_ROLE).split("\n")[0][:4].upper() or "\u2022")
        f = QFont(opt.font)
        f.setPixelSize(18 if active else (12 if len(label) > 3 else 13))
        f.setWeight(QFont.Bold)
        p.setFont(f)
        p.setPen(tint)
        p.drawText(tile, Qt.AlignCenter, label)

        left = tile.right() + 12
        right = r.right() - pad - (56 if hover else 60)
        y0 = r.center().y() - 18
        f = QFont(opt.font)
        f.setPixelSize(13)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(C["fg"])
        w = int(max(right - left, 10))
        p.drawText(QRectF(left, y0, w, 18), Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(idx.data(TITLE_ROLE) or "", Qt.ElideMiddle, w))
        f2 = QFont(opt.font)
        f2.setPixelSize(12)
        p.setFont(f2)
        p.setPen(C["sub"])
        sw = int(max(r.right() - pad - left - 4, 10))
        p.drawText(QRectF(left, y0 + 20, sw, 16), Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(idx.data(SUB_ROLE) or "", Qt.ElideRight, sw))

        if active:   # бегущая полоска: размер файла заранее неизвестен
            track = QRectF(left, r.bottom() - 7, max(r.right() - pad - left, 10), 3)
            tc = QColor(tint)
            tc.setAlpha(50)
            p.setPen(Qt.NoPen)
            p.setBrush(tc)
            p.drawRoundedRect(track, 1.5, 1.5)
            seg = track.width() * 0.3
            x = track.left() + ((time.time() * 0.9) % 1.0) * (track.width() + seg) - seg
            clip = QPainterPath()
            clip.addRoundedRect(track, 1.5, 1.5)
            p.setClipPath(clip)
            p.setBrush(tint)
            p.drawRoundedRect(QRectF(x, track.top(), seg, track.height()), 1.5, 1.5)
            p.setClipping(False)
        if hover and not active:
            mp = v.mouse_pos
            dr, fr = self.del_rect(opt.rect), self.dir_rect(opt.rect)

            def cross(c):
                p.drawLine(QPointF(c.x() - 4, c.y() - 4), QPointF(c.x() + 4, c.y() + 4))
                p.drawLine(QPointF(c.x() - 4, c.y() + 4), QPointF(c.x() + 4, c.y() - 4))

            def folder(c):
                body = QRectF(c.x() - 6.5, c.y() - 3.5, 13, 9.5)
                p.drawRoundedRect(body, 2, 2)
                p.drawLine(QPointF(c.x() - 6.5, c.y() - 3.5), QPointF(c.x() - 3, c.y() - 6))
                p.drawLine(QPointF(c.x() - 3, c.y() - 6), QPointF(c.x() - 0.5, c.y() - 6))
                p.drawLine(QPointF(c.x() - 0.5, c.y() - 6), QPointF(c.x() + 1, c.y() - 3.5))

            self._button(p, dr, mp is not None and dr.contains(mp), C, cross)
            self._button(p, fr, mp is not None and fr.contains(mp), C, folder)
        else:
            f3 = QFont(opt.font)
            f3.setPixelSize(11)
            p.setFont(f3)
            p.setPen(C["sub"])
            txt = "идёт" if active else rel_time(idx.data(TIME_ROLE) or time.time())
            p.drawText(QRectF(r.right() - pad - 52, y0, 52, 18), Qt.AlignVCenter | Qt.AlignRight,
                       txt)
        p.restore()


class DlView(ClipView):
    revealRequested = Signal(object)

    def __init__(self):
        super().__init__()
        self.setItemDelegate(DlDelegate(self))

    def mouseReleaseEvent(self, e):
        pos = e.position().toPoint()
        it = self.itemAt(pos)
        if it is not None and e.button() == Qt.LeftButton and it.data(KIND_ROLE) != "active":
            rect = self.visualItemRect(it)
            d = self.itemDelegate()
            if d.del_rect(rect).contains(pos):
                self.removeRequested.emit(it)
                return
            if d.dir_rect(rect).contains(pos):
                self.revealRequested.emit(it)
                return
        QListWidget.mouseReleaseEvent(self, e)


# ======================= прогресс обновления =======================
class UpdateProgress(QWidget):
    """Полоска с подписью; без известного размера бежит неопределённая полоска."""

    def __init__(self):
        super().__init__()
        self.frac, self.text = 0.0, ""
        self.fill, self.track, self.fg = QColor("#0a84ff"), QColor(128, 128, 128, 60), QColor("#888")
        self.setFixedHeight(26)
        self.tm = QTimer(self)
        self.tm.setInterval(40)
        self.tm.timeout.connect(self._tick)

    def set_colors(self, T):
        self.fill = QColor(T["accent"]) if T.get("accent") else QColor(T["fg"])
        self.track = css_color(T["groove"])
        self.fg = QColor(T["sub"])
        self.update()

    def set_state(self, frac, text):
        self.frac, self.text = frac, text
        if frac is None:
            if not self.tm.isActive():
                self.tm.start()
        else:
            self.tm.stop()
        self.update()

    def _tick(self):
        if self.isVisible():
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w = self.width()
        bar = QRectF(0, 2, w, 6)
        p.setPen(Qt.NoPen)
        p.setBrush(self.track)
        p.drawRoundedRect(bar, 3, 3)
        clip = QPainterPath()
        clip.addRoundedRect(bar, 3, 3)
        p.setClipPath(clip)
        p.setBrush(self.fill)
        if self.frac is None:
            seg = w * 0.3
            x = ((time.time() * 0.8) % 1.0) * (w + seg) - seg
            p.drawRect(QRectF(x, 2, seg, 6))
        else:
            p.drawRect(QRectF(0, 2, w * max(0.0, min(1.0, self.frac)), 6))
        p.setClipping(False)
        f = QFont(self.font())
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(self.fg)
        p.drawText(QRectF(0, 10, w, 16), Qt.AlignCenter, self.text)


# ======================= редактор интерфейса =======================
NAV_KEYS = ["home", "clipboard", "download", "weather", "timer", "note", "shelf", "settings"]
NAV_LABELS = ["Главная", "Буфер", "Загрузки", "Погода", "Таймер", "Заметка", "Полка",
              "Настройки"]
FN_ORDER = ["area", "screen", "ocr", "qr", "pick", "clean", "record", "command"]
FN_LABELS = {"area": "Область", "screen": "Весь экран", "ocr": "Текст с экрана",
             "qr": "QR-код", "pick": "Пипетка", "clean": "Чистый текст",
             "record": "Запись экрана", "command": "Команда"}
EDITOR_PAGE = 8      # номер страницы редактора в стеке (в панели вкладок её нет)


def clean_order(order, default):
    """Оставляет только известные ключи без повторов, недостающие дописывает в конец."""
    out = []
    for k in (order if isinstance(order, list) else []):
        if k in default and k not in out:
            out.append(k)
    return out + [k for k in default if k not in out]


class BoardChip(QWidget):
    """Плитка в редакторе: тянуть = переставить, нажать = скрыть или показать."""

    def __init__(self, board, key, label, icon_name, locked):
        super().__init__(board)
        self.board, self.key, self.label = board, key, label
        self.icon_name, self.locked = icon_name, locked
        self.icon = QIcon()
        self.on = True
        self._press, self._moved, self._hover = None, False, False
        self._off = QPoint()
        self._anim = None
        self.setCursor(Qt.OpenHandCursor)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        C = self.board.colors
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setOpacity(1.0 if self.on else 0.45)
        r = QRectF(0.5, 0.5, w - 1, h - 1)
        p.setPen(Qt.NoPen)
        p.setBrush(C["card_hi"] if (self._hover or self._moved) else C["card"])
        p.drawRoundedRect(r, 12, 12)
        if self._moved:
            ring = QColor(C["fg"])
            ring.setAlpha(130)
            p.setPen(QPen(ring, 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 12, 12)
        p.setPen(Qt.NoPen)
        p.setBrush(C["sub"])
        for cx in (12, 17):               # «ручка» для перетаскивания
            for cy in (h / 2 - 5, h / 2, h / 2 + 5):
                p.drawEllipse(QPointF(cx, cy), 1.3, 1.3)
        if not self.icon.isNull():
            self.icon.paint(p, QRect(28, (h - 18) // 2, 18, 18))
        f = QFont(self.font())
        f.setPixelSize(13)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(C["fg"])
        tw = max(w - 54 - 34, 10)
        p.drawText(QRectF(54, 0, tw, h), Qt.AlignVCenter | Qt.AlignLeft,
                   p.fontMetrics().elidedText(self.label, Qt.ElideRight, int(tw)))
        if not self.locked:               # кружок: заполнен с галочкой = показано
            c = QPointF(w - 18, h / 2)
            if self.on:
                p.setPen(Qt.NoPen)
                p.setBrush(C["fg"])
                p.drawEllipse(c, 8, 8)
                p.setPen(QPen(C["bg"], 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawLine(QPointF(c.x() - 3.5, c.y()), QPointF(c.x() - 1, c.y() + 2.8))
                p.drawLine(QPointF(c.x() - 1, c.y() + 2.8), QPointF(c.x() + 3.8, c.y() - 3))
            else:
                p.setPen(QPen(C["sub"], 1.5))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(c, 7.5, 7.5)

    def stop_anim(self):
        if self._anim is not None:
            self._anim.stop()

    def glide_to(self, target):
        if self.pos() == target:
            return
        self.stop_anim()
        a = QPropertyAnimation(self, b"pos", self)
        a.setDuration(150)
        a.setEasingCurve(QEasingCurve.OutCubic)
        a.setEndValue(target)
        self._anim = a
        a.start()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self._press = e.globalPosition().toPoint()
        self._off = e.position().toPoint()
        self._moved = False

    def mouseMoveEvent(self, e):
        if self._press is None:
            return
        gp = e.globalPosition().toPoint()
        if not self._moved:
            if (gp - self._press).manhattanLength() < 6:
                return
            self._moved = True
            self.stop_anim()
            self.raise_()
            self.setCursor(Qt.ClosedHandCursor)
        pos = self.parentWidget().mapFromGlobal(gp) - self._off
        self.move(self.board.clamp(pos, self))
        self.board.reflow(self)
        self.update()

    def mouseReleaseEvent(self, e):
        if self._press is None:
            return
        moved, self._press, self._moved = self._moved, None, False
        self.setCursor(Qt.OpenHandCursor)
        if moved:
            self.board.settle(self)
        elif (e.button() == Qt.LeftButton and not self.locked
              and self.rect().contains(e.position().toPoint())):
            self.on = not self.on
            self.board.changed.emit()
        self.update()


class DragBoard(QWidget):
    """Сетка плиток с перетаскиванием: остальные плитки расступаются во время движения."""
    changed = Signal()
    GAP = 8

    def __init__(self, cols, cell):
        super().__init__()
        self.cols, self.cell = cols, cell
        self.chips = []
        self.fg_hex = "#000000"
        self.colors = {k: QColor() for k in ("card", "card_hi", "fg", "sub", "bg")}

    def slot(self, i):
        cw, ch = self.cell
        return QPoint((i % self.cols) * (cw + self.GAP), (i // self.cols) * (ch + self.GAP))

    def set_items(self, items):
        """items: [(ключ, подпись, имя значка, нельзя_скрыть, показан)]"""
        for c in self.chips:
            c.hide()
            c.deleteLater()
        self.chips = []
        for key, label, icon_name, locked, on in items:
            c = BoardChip(self, key, label, icon_name, locked)
            c.on = on
            c.resize(*self.cell)
            self.chips.append(c)
        rows = max(1, -(-len(items) // self.cols))
        cw, ch = self.cell
        self.setFixedSize(self.cols * cw + (self.cols - 1) * self.GAP,
                          rows * ch + (rows - 1) * self.GAP)
        self.refresh_icons()
        for i, c in enumerate(self.chips):
            c.move(self.slot(i))
            c.show()

    def order(self):
        return [c.key for c in self.chips]

    def hidden(self):
        return [c.key for c in self.chips if not c.on]

    def set_colors(self, T):
        self.fg_hex = T["fg"]
        bg = QColor(*T["panel"])
        bg.setAlpha(255)
        self.colors = {"card": css_color(T["card"]), "card_hi": css_color(T["card_hi"]),
                       "fg": QColor(T["fg"]), "sub": QColor(T["sub"]), "bg": bg}
        self.refresh_icons()

    def refresh_icons(self):
        for c in self.chips:
            c.icon = make_icon(c.icon_name, self.fg_hex)
            c.update()

    def clamp(self, pos, chip):
        x = max(0, min(pos.x(), self.width() - chip.width()))
        y = max(0, min(pos.y(), self.height() - chip.height()))
        return QPoint(x, y)

    def reflow(self, chip):
        cw, ch = self.cell
        cen = chip.geometry().center()
        rows = max(1, -(-len(self.chips) // self.cols))
        col = max(0, min(self.cols - 1, cen.x() // (cw + self.GAP)))
        row = max(0, min(rows - 1, cen.y() // (ch + self.GAP)))
        idx = min(row * self.cols + col, len(self.chips) - 1)
        cur = self.chips.index(chip)
        if idx != cur:
            self.chips.insert(idx, self.chips.pop(cur))
            for i, c in enumerate(self.chips):
                if c is not chip:
                    c.glide_to(self.slot(i))

    def settle(self, chip):
        chip.glide_to(self.slot(self.chips.index(chip)))
        self.changed.emit()


# ======================= проверка обновлений (GitHub Releases) =======================
def parse_version(text):
    """'v1.0.4' -> (1, 0, 4); нечисловые хвосты игнорируются."""
    nums = re.findall(r"\d+", str(text).split("-")[0])
    return tuple(int(n) for n in nums[:4]) or (0,)


class UpdateWorker(QObject):
    checked = Signal(object)     # {"status": "new"|"latest"|"error", ...}
    installing = Signal(object)  # {"status": "downloading"|"started"|"error", ...}

    def check(self):
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        try:
            req = urllib.request.Request(UPDATE_URL, headers={
                "User-Agent": APP_NAME, "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                info = json.load(r)
            tag = info.get("tag_name") or info.get("name") or ""
            if parse_version(tag) <= parse_version(APP_VERSION):
                self.checked.emit({"status": "latest", "version": tag.lstrip("vV")})
                return
            url = next((a["browser_download_url"] for a in info.get("assets", [])
                        if a.get("name", "").lower().endswith(".exe")), "")
            size = next((a.get("size", 0) for a in info.get("assets", [])
                         if a.get("browser_download_url") == url), 0)
            self.checked.emit({"status": "new", "version": tag.lstrip("vV"), "url": url,
                               "size": size, "page": info.get("html_url") or RELEASES_PAGE})
        except Exception as ex:
            log(f"update check: {ex}", once=True)
            self.checked.emit({"status": "error"})

    def install(self, url, size=0):
        threading.Thread(target=self._install, args=(url, size), daemon=True).start()

    def _install(self, url, size=0):
        try:
            self.installing.emit({"status": "downloading", "done": 0, "total": size})
            path = os.path.join(tempfile.gettempdir(), "MiniIsland-Setup.exe")
            req = urllib.request.Request(url, headers={"User-Agent": APP_NAME})
            with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0) or size
                done, last_t, last_pct = 0, 0.0, -1
                while True:
                    chunk = r.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    pct = int(done * 100 / total) if total else -1
                    now = time.time()
                    if pct != last_pct and now - last_t > 0.08 or now - last_t > 0.5:
                        last_pct, last_t = pct, now
                        self.installing.emit({"status": "downloading", "done": done,
                                              "total": total})
            if done <= 0 or (total and done < total):
                raise IOError(f"incomplete download: {done}/{total}")
            self.installing.emit({"status": "started", "done": done, "total": done})
            # установщик сам запустит новую версию; отвязываем его от нашего процесса
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            subprocess.Popen([path, "/SILENT", "/NORESTART"], creationflags=flags,
                             close_fds=True)
        except Exception as ex:
            log(f"update install: {ex}", once=True)
            self.installing.emit({"status": "error"})


# ======================= полка для файлов =======================
class ShelfList(QListWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.CopyAction)

    def add_paths(self, paths):
        existing = {self.item(i).data(Qt.UserRole) for i in range(self.count())}
        for p in paths:
            if p and p not in existing:
                it = QListWidgetItem(os.path.basename(p) or p)
                it.setData(Qt.UserRole, p)
                it.setToolTip(p)
                self.addItem(it)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.add_paths([u.toLocalFile() for u in e.mimeData().urls()])
        e.acceptProposedAction()

    def mimeData(self, items):
        m = QMimeData()
        m.setUrls([QUrl.fromLocalFile(i.data(Qt.UserRole)) for i in items])
        return m

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            for it in self.selectedItems():
                self.takeItem(self.row(it))
        else:
            super().keyPressEvent(e)



# ======================= Windows: окна и простой системы =======================
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _LII(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    class _GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

_idle_fallback = [None, time.time()]


def system_idle_seconds():
    """Сколько секунд пользователь не трогает мышь и клавиатуру."""
    if sys.platform == "win32":
        try:
            li = _LII()
            li.cbSize = ctypes.sizeof(li)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
                tick = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
                return ((tick - li.dwTime) & 0xFFFFFFFF) / 1000.0
        except Exception:
            pass
    pos = QCursor.pos()  # запасной вариант: следим за курсором
    if _idle_fallback[0] != pos:
        _idle_fallback[0], _idle_fallback[1] = pos, time.time()
    return time.time() - _idle_fallback[1]


class WinShell:
    """Определяет, виден ли рабочий стол: нет ни одного открытого окна программы."""
    SHELL = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
             "Windows.UI.Core.CoreWindow", "XamlExplorerHostIslandWindow",
             "NotifyIconOverflowWindow", "TopLevelWindowForOverflowXamlIsland"}

    def __init__(self):
        self.u = ctypes.windll.user32
        self.dwm = ctypes.windll.dwmapi
        u = self.u
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.IsIconic.argtypes = [wintypes.HWND]
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetWindowLongW.restype = ctypes.c_long
        u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                                   ctypes.c_void_p, wintypes.DWORD]
        proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        u.EnumWindows.argtypes = [proc_type, wintypes.LPARAM]
        self.proc = proc_type(self._cb)  # ссылку держим, чтобы её не удалил сборщик мусора
        self.found = False

    def _cb(self, hwnd, lparam):
        try:
            u = self.u
            if not u.IsWindowVisible(hwnd) or u.IsIconic(hwnd):
                return True
            ex = u.GetWindowLongW(hwnd, -20) & 0xFFFFFFFF
            if (ex & 0x80) and not (ex & 0x40000):  # служебное окно (не APPWINDOW)
                return True
            if ex & 0x08000000:  # NOACTIVATE
                return True
            if u.GetWindowTextLengthW(hwnd) == 0:
                return True
            cloaked = wintypes.DWORD(0)
            self.dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4)
            if cloaked.value:  # скрытые окна UWP
                return True
            buf = ctypes.create_unicode_buffer(64)
            u.GetClassNameW(hwnd, buf, 64)
            if buf.value in self.SHELL:
                return True
            self.found = True
            return False
        except Exception:
            return True

    def desktop_visible(self):
        self.found = False
        self.u.EnumWindows(self.proc, 0)
        return not self.found


class CoreAudio:
    """Громкость и уровень звука напрямую через Windows Core Audio (ctypes, без pycaw)."""
    CLSID_ENUM = "BCDE0395-E52F-467C-8E3D-C4579291692E"
    IID_ENUM = "A95664D2-9614-4F35-A746-DE8DB63617E6"
    IID_VOL = "5CDF2C82-841E-4546-9722-0CF74078229A"
    IID_METER = "C02216F6-8C67-4B5B-9D00-D008E73E0064"

    def __init__(self):
        self.vol = self.meter = None
        self.error = ""
        self._t = time.time()
        self._get_v = self._set_v = self._get_m = self._set_m = self._peek = None
        try:
            self.acquire()
        except Exception as e:
            self.error = f"{e.__class__.__name__}: {e}"
            log("CoreAudio init: " + self.error, once=True)

    @property
    def ok(self):
        return self.vol is not None

    @staticmethod
    def _guid(s):
        return _GUID.from_buffer_copy(uuid.UUID(s).bytes_le)

    @staticmethod
    def _method(ptr, idx, *argtypes):
        vtbl = ctypes.cast(ctypes.c_void_p(ptr), ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
        proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)
        return proto(vtbl[0][idx])

    def acquire(self):
        """Берёт текущее устройство вывода звука по умолчанию."""
        P, V = ctypes.POINTER, ctypes.c_void_p
        ole32 = ctypes.windll.ole32
        ole32.CoInitializeEx(None, 2)
        ole32.CoCreateInstance.argtypes = [P(_GUID), V, wintypes.DWORD, P(_GUID), P(V)]
        ole32.CoCreateInstance.restype = ctypes.c_long
        enum = V()
        hr = ole32.CoCreateInstance(ctypes.byref(self._guid(self.CLSID_ENUM)), None, 0x17,
                                    ctypes.byref(self._guid(self.IID_ENUM)), ctypes.byref(enum))
        if hr < 0 or not enum.value:
            raise OSError(f"CoCreateInstance 0x{hr & 0xFFFFFFFF:08X}")
        dev = V()
        hr = self._method(enum.value, 4, ctypes.c_int, ctypes.c_int, P(V))(
            enum, 0, 1, ctypes.byref(dev))
        if hr < 0 or not dev.value:
            raise OSError(f"нет устройства вывода звука 0x{hr & 0xFFFFFFFF:08X}")

        def activate(iid):
            out = V()
            r = self._method(dev.value, 3, P(_GUID), wintypes.DWORD, V, P(V))(
                dev, ctypes.byref(self._guid(iid)), 0x17, None, ctypes.byref(out))
            if r < 0 or not out.value:
                raise OSError(f"Activate 0x{r & 0xFFFFFFFF:08X}")
            return out

        vol = activate(self.IID_VOL)
        try:
            meter = activate(self.IID_METER)
        except Exception:
            meter = None
        old = (self.vol, self.meter)
        f = ctypes.c_float
        self._get_v = self._method(vol.value, 9, P(f))
        self._set_v = self._method(vol.value, 7, f, V)
        self._get_m = self._method(vol.value, 15, P(wintypes.BOOL))
        self._set_m = self._method(vol.value, 14, wintypes.BOOL, V)
        self._peek = self._method(meter.value, 3, P(f)) if meter else None
        self.vol, self.meter, self.error = vol, meter, ""
        for obj in (enum, dev) + old:  # освобождаем старые ссылки COM
            if obj is not None and obj.value:
                try:
                    self._method(obj.value, 2)(obj)
                except Exception:
                    pass

    def _maybe_refresh(self):
        now = time.time()
        if now - self._t > 15:  # следим за сменой устройства вывода по умолчанию
            self._t = now
            try:
                self.acquire()
            except Exception as e:
                self.error = f"{e.__class__.__name__}: {e}"
                log("CoreAudio refresh: " + self.error, once=True)

    def _fail(self, what):
        self.error = what
        log("CoreAudio: " + what, once=True)
        self._t = time.time() - 10  # повторная попытка через ~5 секунд

    def get_volume(self):
        self._maybe_refresh()
        if not self.ok:
            return None
        v = ctypes.c_float()
        hr = self._get_v(self.vol, ctypes.byref(v))
        if hr < 0:
            self._fail(f"GetMasterVolume 0x{hr & 0xFFFFFFFF:08X}")
            return None
        return round(v.value * 100)

    def set_volume(self, pct):
        if not self.ok:
            return
        hr = self._set_v(self.vol, ctypes.c_float(max(0, min(100, pct)) / 100.0), None)
        if hr < 0:
            self._fail(f"SetMasterVolume 0x{hr & 0xFFFFFFFF:08X}")

    def get_mute(self):
        if not self.ok:
            return False
        m = wintypes.BOOL()
        return bool(m.value) if self._get_m(self.vol, ctypes.byref(m)) >= 0 else False

    def set_mute(self, mute):
        if self.ok:
            self._set_m(self.vol, int(bool(mute)), None)

    def peak(self):
        self._maybe_refresh()
        if not (self.ok and self._peek):
            return None
        v = ctypes.c_float()
        hr = self._peek(self.meter, ctypes.byref(v))
        return v.value if hr >= 0 else None


class AudioMeter:
    """Реальный уровень звука системы. Если недоступен, возвращает None."""

    def __init__(self, core=None):
        self.core, self.meter = core, None
        if core is None or core._peek is None:
            self._init_pycaw()

    def _init_pycaw(self):
        try:
            try:
                from pycaw.api.endpointvolume import IAudioMeterInformation
            except ImportError:
                from pycaw.pycaw import IAudioMeterInformation
            from pycaw.pycaw import AudioUtilities
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER
            dev = AudioUtilities.GetSpeakers()
            imm = getattr(dev, "_dev", dev)
            iface = imm.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
            self.meter = cast(iface, POINTER(IAudioMeterInformation))
        except Exception:
            self.meter = None

    def peak(self):
        if self.core is not None and self.core.ok and self.core._peek is not None:
            return self.core.peak()
        if self.meter is None:
            return None
        try:
            return float(self.meter.GetPeakValue())
        except Exception:
            self.meter = None
            return None


# ======================= жильцы острова =======================
PEACH = QColor("#f29c7e")
INK = QColor("#2b2024")
CAT_WHITE = QColor("#f6f2ef")
GHOST_ROWS = ["...#####...", ".#########.", "###########", "###########", "###########",
              "###########", "###########", "###########", "###########", "###########"]
GHOST_FEET_A, GHOST_FEET_B = "###.###.###", "#.###.###.#"


class ResState:
    """Общее состояние жильцов: музыка, сон, моргание."""

    def __init__(self):
        self.level = 0.0     # громкость музыки 0..1
        self.beat = 0.0      # вспышка на ударе, быстро затухает
        self.dir = 1         # в какую сторону качаемся
        self.tilt = 0.0      # наклон в градусах
        self.sleep = 0.0     # 0 бодрствует, 1 крепко спит
        self.blink = 0.0
        self.next_blink = time.time() + 3
        self.blink_until = 0.0
        self.audio_on = False


class Resident(QWidget):
    """Жилец: следит глазами за курсором, танцует под музыку, засыпает без хозяина."""

    def __init__(self, state, tile=False):
        super().__init__()
        self.state, self.tile, self.kind = state, tile, "cat"
        self.preview = False   # превью в списке выбора: рисуем значок «нет», когда питомца нет
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedSize(56, 34) if tile else self.setFixedSize(30, 26)

    def set_kind(self, k):
        self.kind = k
        self.update()

    def gaze(self):
        c = self.mapToGlobal(QPoint(self.width() // 2, self.height() // 2))
        cur = QCursor.pos()
        dx, dy = cur.x() - c.x(), cur.y() - c.y()
        d = math.hypot(dx, dy)
        if d < 1:
            return 0.0, 0.0
        k = min(1.0, d / 140.0)
        return dx / d * k, dy / d * k

    def paintEvent(self, e):
        if self.kind == "none":
            if self.preview:
                self.draw_none()
            return
        R, now = self.state, time.time()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.tile:  # в раскрытой шторке жилец сидит в своём чёрном окошке
            p.setBrush(QColor(0, 0, 0))
            p.setPen(QPen(QColor(255, 255, 255, 28), 1))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 12, 12)
        awake = 1.0 - R.sleep
        gx, gy = self.gaze() if awake > 0.5 else (0.0, 0.0)
        closed = max(R.blink, R.sleep) > 0.55
        happy = R.level > 0.12 and awake > 0.5
        hop = R.beat * 3.2 * awake
        bob = math.sin(now * 7) * R.level * awake
        s = min(self.width(), self.height()) / 40.0 * (0.92 if self.tile else 1.0)
        p.translate(self.width() / 2, self.height() / 2)
        p.scale(s, s)
        p.translate(0, 8)
        p.rotate(R.tilt)
        br = math.sin(now * 1.7) * R.sleep  # дыхание во сне
        p.scale(1 + 0.025 * br, 1 + 0.035 * br)
        p.translate(0, -8)
        p.translate(-20, -20 - hop - bob)
        {"ghost": self.draw_ghost, "cat": self.draw_cat, "fox": self.draw_fox,
         "sprout": self.draw_sprout, "imp": self.draw_imp}.get(self.kind, self.draw_cat)(p, gx, gy, closed, happy, now)
        if R.sleep > 0.25:
            self.draw_zzz(p, now, R.sleep)

    def draw_none(self):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(150, 150, 160, 200), 1.7))
        p.setBrush(Qt.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2
        r = min(self.width(), self.height()) * 0.28
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.drawLine(QLineF(cx - r * 0.7, cy + r * 0.7, cx + r * 0.7, cy - r * 0.7))
        p.end()

    def draw_zzz(self, p, now, k):
        f = QFont("Segoe UI")
        f.setBold(True)
        for i in range(3):
            ph = (now * 0.55 + i / 3.0) % 1.0
            col = QColor(PEACH)
            col.setAlpha(int(230 * math.sin(math.pi * ph) * k))
            f.setPixelSize(int(6 + ph * 5))
            p.setFont(f)
            p.setPen(col)
            p.drawText(QPointF(27 + ph * 5, 13 - ph * 9), "z")

    def draw_ghost(self, p, gx, gy, closed, happy, now):
        c, ox, oy = 3.0, 3.5, 4.0
        p.setPen(Qt.NoPen)
        p.setBrush(PEACH)
        rows = GHOST_ROWS + [GHOST_FEET_B if (happy and int(now * 3) % 2) else GHOST_FEET_A]
        for ri, row in enumerate(rows):
            for ci, ch in enumerate(row):
                if ch == "#":
                    p.drawRect(QRectF(ox + ci * c, oy + ri * c, c + 0.2, c + 0.2))
        for ex in (2, 7):  # глаза: белый квадрат + зрачок, который смотрит на курсор
            x, y = ox + ex * c, oy + 3 * c
            if closed:
                p.setBrush(INK)
                p.drawRect(QRectF(x + 0.5, y + 2.6, 5, 1.6))
            else:
                p.setBrush(QColor("#ffffff"))
                p.drawRect(QRectF(x, y, 6, 6))
                p.setBrush(INK)
                p.drawRect(QRectF(x + 1.5 + gx * 1.5, y + 1.5 + gy * 1.5, 3, 3))
        p.setBrush(INK)
        p.drawRect(QRectF(17.75, 23.4, 4.5, 3.0 if happy else 1.4))

    def draw_cat(self, p, gx, gy, closed, happy, now):
        p.setPen(Qt.NoPen)
        p.setBrush(CAT_WHITE)
        _P(p, [(7.5, 17), (9, 4.5), (18.5, 11)], True)
        _P(p, [(32.5, 17), (31, 4.5), (21.5, 11)], True)
        p.setBrush(QColor("#f0a595"))
        _P(p, [(9.6, 13.5), (10.2, 8), (14.2, 11.2)], True)
        _P(p, [(30.4, 13.5), (29.8, 8), (25.8, 11.2)], True)
        p.setBrush(CAT_WHITE)
        p.drawEllipse(QPointF(20, 22), 15, 12.5)
        p.setBrush(QColor(242, 156, 126, 110))
        p.drawEllipse(QPointF(11.5, 25.5), 2.4, 1.7)
        p.drawEllipse(QPointF(28.5, 25.5), 2.4, 1.7)
        pen = QPen(INK, 1.5)
        pen.setCapStyle(Qt.RoundCap)
        for x in (14.5, 25.5):
            if closed:
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawArc(QRectF(x - 2.6, 19.2, 5.2, 4), 180 * 16, 180 * 16)
            elif happy:
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawArc(QRectF(x - 2.6, 20, 5.2, 4.4), 0, 180 * 16)
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(INK)
                p.drawEllipse(QPointF(x + gx * 1.5, 21.2 + gy * 1.2), 2.1, 2.5)
                p.setBrush(QColor("#ffffff"))
                p.drawEllipse(QPointF(x + gx * 1.5 - 0.7, 20.4 + gy * 1.2), 0.7, 0.7)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ef8f86"))
        _P(p, [(18.7, 24.6), (21.3, 24.6), (20, 26)], True)
        mp = QPen(INK, 1.0)
        mp.setCapStyle(Qt.RoundCap)
        p.setPen(mp)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(17.4, 25.2, 2.6, 2.4), 180 * 16, 180 * 16)
        p.drawArc(QRectF(20, 25.2, 2.6, 2.4), 180 * 16, 180 * 16)
        if happy:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#ef8f86"))
            p.drawEllipse(QPointF(20, 28.4), 1.1, 1.3)
        p.setPen(QPen(QColor(150, 140, 135), 0.8))
        for a, b, c2, d in ((8.5, 23.5, 2.5, 22), (8.5, 25.5, 2.5, 26.5),
                            (31.5, 23.5, 37.5, 22), (31.5, 25.5, 37.5, 26.5)):
            _L(p, a, b, c2, d)

    def draw_fox(self, p, gx, gy, closed, happy, now):
        """Лиса: рыжая мордочка, белые щёки, тёмные кончики ушей, хвост виляет в такт музыке."""
        R = self.state
        orange, cream = QColor("#ee8a3a"), QColor("#fff4e6")
        wag = math.sin(now * 9) * 14 * R.level if happy else math.sin(now * 1.6) * 3
        p.setPen(Qt.NoPen)
        p.save()  # хвост рисуем первым: голова перекроет его основание
        p.translate(29.5, 31.5)
        p.rotate(-38 + wag)
        p.setBrush(orange)
        p.drawEllipse(QPointF(4.8, 0), 6.8, 3.9)
        p.setBrush(cream)
        p.drawEllipse(QPointF(8.7, 0), 2.6, 2.6)
        p.restore()
        p.setBrush(orange)
        _P(p, [(6.5, 17), (8, 3.2), (17.5, 11)], True)
        _P(p, [(33.5, 17), (32, 3.2), (22.5, 11)], True)
        p.setBrush(QColor("#4a2a24"))
        _P(p, [(8, 3.2), (7.475, 8.03), (11.33, 5.98)], True)
        _P(p, [(32, 3.2), (32.525, 8.03), (28.67, 5.98)], True)
        p.setBrush(cream)
        _P(p, [(9.3, 14.2), (10, 9.8), (13.6, 11.8)], True)
        _P(p, [(30.7, 14.2), (30, 9.8), (26.4, 11.8)], True)
        head = QPainterPath()
        head.addEllipse(QPointF(20, 22), 15.5, 12.5)
        p.setBrush(orange)
        p.drawPath(head)
        p.save()  # белые щёки и подбородок: рыжий лоб клином спускается к носу
        p.setClipPath(head)
        p.setBrush(cream)
        _P(p, [(3, 24), (13, 22.6), (20, 26.4), (27, 22.6), (37, 24), (37, 38), (3, 38)], True)
        p.restore()
        _P(p, [(5.4, 21.5), (1.8, 25.6), (6.4, 27.6)], True)
        _P(p, [(34.6, 21.5), (38.2, 25.6), (33.6, 27.6)], True)
        pen = QPen(INK, 1.5)
        pen.setCapStyle(Qt.RoundCap)
        for x in (13.6, 26.4):
            p.setPen(Qt.NoPen)
            p.setBrush(cream)
            p.drawEllipse(QPointF(x, 15.8), 0.9, 0.9)  # светлые «брови»
            if closed:
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawArc(QRectF(x - 2.4, 18.4, 4.8, 4), 180 * 16, 180 * 16)
            elif happy:
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawArc(QRectF(x - 2.4, 19.2, 4.8, 4.2), 0, 180 * 16)
            else:
                p.setBrush(INK)
                p.drawEllipse(QPointF(x + gx * 1.4, 20.2 + gy * 1.1), 1.9, 2.4)
                p.setBrush(QColor("#ffffff"))
                p.drawEllipse(QPointF(x + gx * 1.4 - 0.6, 19.4 + gy * 1.1), 0.65, 0.65)
        p.setPen(Qt.NoPen)
        p.setBrush(INK)
        p.drawEllipse(QPointF(20, 25.9), 1.9, 1.3)
        mp = QPen(INK, 1.0)
        mp.setCapStyle(Qt.RoundCap)
        p.setPen(mp)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(17.2, 27.0, 2.8, 2.2), 180 * 16, 180 * 16)
        p.drawArc(QRectF(20, 27.0, 2.8, 2.2), 180 * 16, 180 * 16)
        if happy:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#e8746f"))
            p.drawEllipse(QPointF(20, 30.2), 1.3, 1.5)

    def draw_imp(self, p, gx, gy, closed, happy, now):
        """Лиловый проказник: пушистая мордочка, красные глаза, широкая улыбка и язык."""
        R = self.state
        body, dark = QColor("#8257e6"), QColor("#6a43c4")
        p.setPen(Qt.NoPen)
        p.setBrush(dark)
        _P(p, [(5.5, 15), (7.5, 2.5), (16.5, 9.5)], True)
        _P(p, [(34.5, 15), (32.5, 2.5), (23.5, 9.5)], True)
        p.setBrush(body)
        p.drawEllipse(QPointF(13, 35), 4.6, 2.6)
        p.drawEllipse(QPointF(27, 35), 4.6, 2.6)
        _P(p, [(15.5, 10), (17.5, 4.2), (19.5, 9), (21.5, 3.2), (23, 8.5), (25, 5), (25.5, 11)], True)
        p.drawEllipse(QPointF(20, 22), 15.5, 12.5)
        _P(p, [(5.5, 20), (1.8, 24), (6, 27)], True)
        _P(p, [(34.5, 20), (38.2, 24), (34, 27)], True)
        p.setBrush(QColor("#a98bf0"))
        _P(p, [(8.6, 12.5), (9.2, 6.5), (13.2, 10)], True)
        _P(p, [(31.4, 12.5), (30.8, 6.5), (26.8, 10)], True)
        for cx, rot in ((13.2, 14), (26.8, -14)):  # глаза: сердитый наклон, зрачки следят за курсором
            p.save()
            p.translate(cx, 18.6)
            p.rotate(rot)
            if closed:
                pen = QPen(QColor("#2e1a66"), 1.4)
                pen.setCapStyle(Qt.RoundCap)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawArc(QRectF(-3.6, -2.2, 7.2, 4.4), 180 * 16, 180 * 16)
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#ff5c4d"))
                p.drawEllipse(QPointF(0, 0), 4.3, 3.2)
                p.setBrush(QColor("#ffffff"))
                p.drawEllipse(QPointF(gx * 1.7, gy * 0.9), 1.1, 1.8)
            p.restore()
        mo = 0.2 if R.sleep > 0.5 else (1.0 if happy else 0.6)  # насколько открыт рот
        top = 25.0
        mouth = QPainterPath()
        mouth.moveTo(9.5, top)
        mouth.quadTo(20, top + 2.2, 30.5, top)
        mouth.quadTo(20, top + 3 + 10 * mo, 9.5, top)
        mouth.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#3b1230"))
        p.drawPath(mouth)
        p.save()
        p.setClipPath(mouth)
        p.setBrush(QColor("#ffffff"))
        p.drawRect(QRectF(9, top, 22, 3.2))
        p.setBrush(QColor("#3b1230"))
        for gx_ in (15.5, 24.5):
            p.drawRect(QRectF(gx_ - 0.35, top, 0.7, 3.2))
        p.restore()
        if R.sleep < 0.5:  # язык: виляет в такт музыке
            wag = math.sin(now * 9) * 1.4 * R.level if happy else 0.0
            tl = 6.5 if happy else 4.0
            p.setBrush(QColor("#ff7fae"))
            _R(p, 21 + wag, top + 2.5, 6.2, tl, 3.0)
            p.setBrush(QColor("#e85d92"))
            _R(p, 23.9 + wag, top + 3.4, 0.5, tl - 2.6, 0.25)

    def draw_sprout(self, p, gx, gy, closed, happy, now):
        R = self.state
        sway = R.tilt * 0.8 + math.sin(now * 1.4) * 2.0 * (1 - R.sleep) - R.sleep * 40
        green = QColor("#86c08a")
        p.save()
        p.translate(20, 25)
        p.rotate(sway)
        pen = QPen(green, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        stem = QPainterPath()
        stem.moveTo(0, 0)
        stem.quadTo(1.8, -6, 0, -13)
        p.drawPath(stem)
        p.setPen(Qt.NoPen)
        p.setBrush(green)
        p.save()
        p.translate(0, -6)
        p.rotate(-40)
        p.drawEllipse(QRectF(-7, -2.2, 7, 4.4))
        p.restore()
        p.save()
        p.translate(0, -9)
        p.rotate(40)
        p.drawEllipse(QRectF(0, -2.2, 7, 4.4))
        p.restore()
        p.setBrush(PEACH)
        p.drawEllipse(QPointF(0, -15), 3.4, 3.4)
        p.setBrush(QColor(255, 255, 255, 150))
        p.drawEllipse(QPointF(-1, -16), 0.9, 0.9)
        p.restore()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#e2825a"))
        _P(p, [(12.5, 29), (27.5, 29), (25.6, 38), (14.4, 38)], True)
        _R(p, 10.5, 24.5, 19, 5, 1.8)
        fp = QPen(INK, 1.1)
        fp.setCapStyle(Qt.RoundCap)
        if closed:
            p.setPen(fp)
            p.setBrush(Qt.NoBrush)
            for x in (17.2, 22.8):
                p.drawArc(QRectF(x - 1.5, 31, 3, 2.4), 180 * 16, 180 * 16)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(INK)
            for x in (17.2, 22.8):
                p.drawEllipse(QPointF(x + gx * 0.7, 32 + gy * 0.5), 1.15, 1.15)
        p.setPen(fp)
        p.setBrush(Qt.NoBrush)
        w = 4.6 if happy else 3.6
        p.drawArc(QRectF(20 - w / 2, 32.6, w, 3.2), 180 * 16, 180 * 16)


class ThemeSwatch(QWidget):
    """Миниатюра темы: фон, пара строк и эквалайзер в стиле этой темы."""

    def __init__(self, key, w=72, h=42):
        super().__init__()
        self.key = key
        self.setFixedSize(w, h)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_key(self, key):
        self.key = key
        self.update()

    def paintEvent(self, e):
        T = THEMES[self.key]
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bd = QColor(*T["border"])
        bd.setAlpha(max(bd.alpha(), 90))
        p.setPen(QPen(bd, 1))
        p.setBrush(QColor(*T["panel"][:3]))
        r = min(10.0, h * 0.28)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), r, r)
        fg = QColor(T["fg"])
        fg.setAlpha(80)
        p.setPen(Qt.NoPen)
        p.setBrush(fg)
        lh = max(2.0, h * 0.1)
        p.drawRoundedRect(QRectF(w * 0.12, h * 0.3, w * 0.34, lh), lh / 2, lh / 2)
        p.drawRoundedRect(QRectF(w * 0.12, h * 0.3 + lh * 2.2, w * 0.24, lh), lh / 2, lh / 2)
        c1, c2 = T["eq_card"]
        c1 = QColor(c1) if c1 else QColor(T["fg"])
        c2 = QColor(c2) if c2 else None
        draw_eq(p, QRectF(w * 0.56, h * 0.22, w * 0.32, h * 0.56), EQ_PREVIEW, T["eq"], c1, c2)
        p.end()


class PickButton(QPushButton):
    """Кнопка-список: превью, название и стрелка. Сам список открывает остров."""

    def __init__(self, preview):
        super().__init__()
        self.setObjectName("pick")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(40)
        self.setMinimumWidth(200)
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 0, 12, 0)
        h.setSpacing(10)
        self.preview = preview
        self.label = QLabel("")
        self.label.setStyleSheet("font-size: 13px; font-weight: 600;")
        chev = QLabel("▾")
        chev.setObjectName("sub")
        for w in (preview, self.label, chev):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        h.addWidget(preview)
        h.addWidget(self.label, 1)
        h.addWidget(chev)

    def set_name(self, t):
        self.label.setText(t)


class PickPopup(QWidget):
    """Выпадающая сетка с вариантами: превью + подпись. Закрывается кликом снаружи."""
    picked = Signal(str)
    opened = Signal()
    closed = Signal()

    def __init__(self, parent, cols=3, tile=(100, 86)):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.cols, self.tile_size = cols, tile
        self.keys, self.tiles = [], {}
        self.bg, self.border = QColor(20, 20, 22, 250), QColor(255, 255, 255, 40)
        self._open, self.closed_at = False, 0.0
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(10, 10, 10, 10)
        self.grid.setSpacing(6)

    def add_tile(self, key, name, preview):
        t = QPushButton()
        t.setObjectName("tile")
        t.setCheckable(True)
        t.setCursor(Qt.PointingHandCursor)
        t.setFocusPolicy(Qt.NoFocus)
        t.setFixedSize(*self.tile_size)
        v = QVBoxLayout(t)
        v.setContentsMargins(4, 8, 4, 6)
        v.setSpacing(5)
        lab = QLabel(name)
        lab.setAlignment(Qt.AlignCenter)
        lab.setStyleSheet("font-size: 12px; font-weight: 600;")
        for w in (preview, lab):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        v.addWidget(preview, 1, Qt.AlignHCenter)
        v.addWidget(lab)
        t.clicked.connect(lambda *_, k=key: self._pick(k))
        i = len(self.keys)
        self.grid.addWidget(t, i // self.cols, i % self.cols)
        self.keys.append(key)
        self.tiles[key] = t

    def _pick(self, key):
        self.picked.emit(key)
        self.close()

    def set_current(self, key):
        for k, t in self.tiles.items():
            t.setChecked(k == key)

    def set_colors(self, bg, border):
        self.bg, self.border = bg, border
        self.update()

    def open_for(self, btn):
        self.adjustSize()
        scr = QApplication.screenAt(btn.mapToGlobal(QPoint(0, 0))) or QApplication.primaryScreen()
        g = scr.availableGeometry()
        pos = btn.mapToGlobal(QPoint(btn.width() - self.width(), btn.height() + 6))
        x = max(g.left() + 6, min(pos.x(), g.right() - self.width() - 6))
        y = pos.y()
        if y + self.height() > g.bottom() - 6:  # не влезает вниз: открываем над кнопкой
            y = btn.mapToGlobal(QPoint(0, 0)).y() - self.height() - 6
        self.move(x, y)
        self.show()

    def showEvent(self, e):
        if not self._open:
            self._open = True
            self.opened.emit()
        super().showEvent(e)

    def hideEvent(self, e):
        if self._open:
            self._open = False
            self.closed_at = time.time()
            self.closed.emit()
        super().hideEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(self.border, 1))
        p.setBrush(self.bg)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 18, 18)
        p.end()


# ======================= сам остров =======================
class Island(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)

        cfg = load_config()
        self.theme = cfg.get("theme", "light")
        if self.theme not in THEMES:
            self.theme = "light"
        self.T = THEMES[self.theme]
        self.pick_res = []   # превью питомцев в списке выбора (оживают, пока список открыт)
        self.autohide = cfg.get("autohide", True)
        self.resident_kind = cfg.get("resident", "cat")
        self.autostart = cfg.get("autostart", True)   # по умолчанию стартуем вместе с Windows
        sync_autostart(self.autostart)               # заодно обновляет путь, если папку перенесли
        self.res, self.residents = ResState(), []
        self.core_audio = CoreAudio() if sys.platform == "win32" else None
        self.meter = AudioMeter(self.core_audio)
        self.winshell = None
        if sys.platform == "win32":
            try:
                self.winshell = WinShell()
            except Exception:
                self.winshell = None
        self._desk_t, self._desk_cand, self._desk_cand_t = 0.0, None, 0.0
        self.peak_max, self.avg, self.last_beat = 0.1, 0.0, 0.0
        self._live_t, self._idle_t, self.idle, self._wave_on = time.time(), 0.0, 0.0, False
        self.hide_on_desktop = cfg.get("hide_on_desktop", True)
        self.desktop_now, self._last_desktop = False, False
        self.peek_hover = False          # пилюля показана по наведению к краю
        self._zone_since, self._peek_gone = None, None
        self.hidden_state = False
        self._hiding = False
        self.pill_since = time.time() + 1.5
        self.clip_images, self.img_seq = {}, 0
        self.expanded = False
        self.pinned = False
        self.busy = 0
        self.collapsed_w = 200
        self.bg_mix = 0.0
        self.accent = None
        self._own_clip = False
        self._vol_sync = False
        self.remaining = 0
        self.timer_running = False
        self.flash_text, self.flash_until = "", 0.0
        self.title, self.artist, self.music_playing = "", "", False
        self.pos, self.dur, self.pos_stamp = 0.0, 0.0, time.monotonic()
        self.weather_brief, self.rain_warned, self.last_weather = "", "", None
        self.weather_kind, self.weather_temp = "", ""
        self.dl_state, self.dl_done = {}, recent_downloads()
        self.update_frac = None
        self.toast_active, self.toast_w, self._toast_gen = False, 330, 0
        self.track_key, self._toast_wait = None, False
        self.downloads_active, self.dl_speed = False, 0.0
        self.rec_start = 0.0
        self.dock_paths = cfg.get("dock") or default_dock()
        self.icons = QFileIconProvider()

        self.recorder = Recorder()
        self.ocr = OcrWorker()
        self.ocr.result.connect(self.on_ocr)
        self.volume = Volume(self.core_audio)
        self.cmdbar = CommandBar()
        self.cmdbar.submitted.connect(self.run_command)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(*MARGIN_COLLAPSED)
        self.root.setSizeConstraint(QLayout.SetNoConstraint)
        self.build_pill()
        self.build_body()

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.finished.connect(self._anim_done)
        self.fx = QGraphicsOpacityEffect(self.body)
        self.body.setGraphicsEffect(self.fx)
        self.fx.setEnabled(False)
        self.fade = QPropertyAnimation(self.fx, b"opacity")
        self.fade.setDuration(280)
        self.fade.setStartValue(0.0)
        self.fade.setEndValue(1.0)
        self.fade.finished.connect(lambda: self.fx.setEnabled(False))
        self.mix_anim = QVariantAnimation(self)
        self.mix_anim.valueChanged.connect(self._set_mix)

        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.setInterval(450)
        self.collapse_timer.timeout.connect(self.collapse)
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.start()
        self.fast_timer = QTimer(self)
        self.fast_timer.setInterval(250)
        self.fast_timer.timeout.connect(self.update_progress)
        self.fast_timer.start()
        self.edge_timer = QTimer(self)  # следит за курсором у верхнего края экрана
        self.edge_timer.setInterval(80)
        self.edge_timer.timeout.connect(self.poll_edge)
        self.edge_timer.start()
        self.foot_timer = QTimer(self)  # волна нижнего края и жильцы
        self.foot_timer.setInterval(40)
        self.foot_timer.timeout.connect(self.live_tick)
        self.foot_timer.start()

        self.updater = UpdateWorker()
        self.updater.checked.connect(self.on_update_checked)
        self.updater.installing.connect(self.on_update_installing)
        self.update_info = None
        self.weather = WeatherWorker()
        self.weather.updated.connect(self.on_weather)
        self.weather_timer = QTimer(self)
        self.weather_timer.setInterval(10 * 60 * 1000)
        self.weather_timer.timeout.connect(lambda: self.weather.refresh())
        self.weather_timer.start()
        QTimer.singleShot(600, lambda: self.weather.refresh())

        self.apply_theme()
        self.apply_resident()
        self.setGeometry(self.rect_for(self.collapsed_w, COLLAPSED_H))
        self.tick()

    # ---------- построение интерфейса ----------
    @staticmethod
    def card(name="card"):
        w = QWidget()
        w.setObjectName(name)
        w.setAttribute(Qt.WA_StyledBackground, True)
        return w

    @staticmethod
    def sub_label(text="", size=12):
        l = QLabel(text)
        l.setObjectName("sub")
        l.setStyleSheet(f"font-size: {size}px;")
        return l

    def build_pill(self):
        self.pill_box = QWidget()
        pl = QHBoxLayout(self.pill_box)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(8)
        self.mini_art = AlbumArt(7)
        self.mini_art.setFixedSize(24, 24)
        self.mini_art.hide()
        self.pill = ElideLabel()
        self.pill.setAlignment(Qt.AlignCenter)
        self.pill.setStyleSheet("font-size: 13px; font-weight: 600; color: white;")
        self.pill_wicon = WeatherIcon(20)
        self.pill_wicon.hide()
        self.resident_pill = Resident(self.res, False)
        self.residents.append(self.resident_pill)
        # слева обложка (когда играет музыка), по центру значок погоды вплотную к тексту,
        # справа питомец: он на месте всегда, и с музыкой, и без неё
        mid = QHBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(5)
        mid.addWidget(self.pill_wicon)
        mid.addWidget(self.pill)
        pl.addWidget(self.mini_art)
        pl.addStretch(1)
        pl.addLayout(mid)
        pl.addStretch(1)
        pl.addWidget(self.resident_pill)
        self.root.addWidget(self.pill_box)

        # --- показ нового трека: большая обложка, название и исполнитель ---
        self.toast_box = QWidget()
        tl = QHBoxLayout(self.toast_box)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(12)
        self.toast_art = AlbumArt(12)
        self.toast_art.setFixedWidth(56)
        self.toast_art.setMinimumHeight(0)
        self.toast_art.setMaximumHeight(56)
        self.toast_art.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.toast_title = ElideLabel()
        self.toast_title.setStyleSheet("font-size: 15px; font-weight: 700; color: white;")
        self.toast_artist = ElideLabel()
        self.toast_artist.setStyleSheet("font-size: 12px; color: rgba(255,255,255,175);")
        col.addStretch(1)
        col.addWidget(self.toast_title)
        col.addWidget(self.toast_artist)
        col.addStretch(1)
        self.toast_eq = Equalizer(4)
        self.toast_eq.setFixedSize(18, 14)
        tl.addWidget(self.toast_art)
        tl.addLayout(col, 1)
        tl.addWidget(self.toast_eq)
        self.toast_fx = QGraphicsOpacityEffect(self.toast_box)
        self.toast_fx.setOpacity(0.0)
        self.toast_box.setGraphicsEffect(self.toast_fx)
        self.toast_fade = QVariantAnimation(self)
        self.toast_fade.valueChanged.connect(lambda v: self.toast_fx.setOpacity(float(v)))
        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(self.end_toast)
        self.toast_box.hide()
        self.root.addWidget(self.toast_box)

    def build_body(self):
        self.body = QWidget()
        bl = QVBoxLayout(self.body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(10)

        # --- верхняя панель вкладок: активная вкладка показывает своё название ---
        navrow = QHBoxLayout()
        navrow.setSpacing(4)
        self.nav_group = QButtonGroup(self)
        self.nav_btns = []
        self.navrow = navrow
        self.nav_names = list(NAV_LABELS)
        self.nav_icon_names = list(NAV_KEYS)
        cfg_ui = load_config()
        self.nav_order = clean_order(cfg_ui.get("nav_order"), NAV_KEYS[:7])
        self.nav_hidden = [k for k in cfg_ui.get("nav_hidden", [])
                           if k in NAV_KEYS[1:7]] if isinstance(cfg_ui.get("nav_hidden"), list) else []
        self.fn_order = clean_order(cfg_ui.get("fn_order"), FN_ORDER)
        self.fn_hidden = [k for k in cfg_ui.get("fn_hidden", []) if k in FN_ORDER] \
            if isinstance(cfg_ui.get("fn_hidden"), list) else []
        self.btn_pin = QPushButton()
        self.btn_pin.setObjectName("nav")
        self.btn_pin.setCheckable(True)
        self.btn_pin.setToolTip("Закрепить (не сворачивать)")
        self.btn_pin.setCursor(Qt.PointingHandCursor)
        self.btn_pin.setFocusPolicy(Qt.NoFocus)
        self.btn_pin.toggled.connect(self.toggle_pin)
        self.resident_tile = Resident(self.res, True)
        self.residents.append(self.resident_tile)
        for i, tip in enumerate(self.nav_names):
            b = QPushButton()
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setIconSize(QSize(18, 18))
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            self.nav_group.addButton(b, i)
            self.nav_btns.append(b)
        self.btn_pin.setIconSize(QSize(18, 18))
        self.nav_group.idClicked.connect(self.set_page)
        self.nav_btns[0].setChecked(True)
        bl.addLayout(navrow)
        self.layout_nav()

        self.stack = QStackedWidget()
        bl.addWidget(self.stack, 1)
        self.stack.addWidget(self.build_home())      # 0
        self.stack.addWidget(self.build_clipboard())  # 1
        self.stack.addWidget(self.build_downloads())  # 2
        self.stack.addWidget(self.build_weather())    # 3
        self.stack.addWidget(self.build_timer())      # 4
        self.stack.addWidget(self.build_note())       # 5
        self.shelf = ShelfList()
        self.stack.addWidget(self.shelf)              # 6
        self.stack.addWidget(self.build_settings())   # 7
        self.stack.addWidget(self.build_editor())     # 8 (редактор, без кнопки во вкладках)

        self.root.addWidget(self.body)
        self.body.hide()

    def build_home(self):
        page = QWidget()
        pv = QVBoxLayout(page)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(10)
        mid = QHBoxLayout()
        mid.setSpacing(10)

        # ---- левая колонка: плеер + громкость ----
        left = QVBoxLayout()
        left.setSpacing(8)
        self.player_card = PlayerCard()
        cl = QVBoxLayout(self.player_card)
        cl.setContentsMargins(14, 12, 14, 8)
        cl.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(14)
        self.art = AlbumArt(14)
        self.art.setFixedSize(84, 84)
        info = QVBoxLayout()
        info.setSpacing(1)
        srow = QHBoxLayout()
        self.music_src = ElideLabel("")
        self.music_src.setObjectName("sub")
        self.music_src.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.card_eq = Equalizer(4)
        self.card_eq.setFixedSize(16, 12)
        srow.addWidget(self.music_src, 1)
        srow.addWidget(self.card_eq)
        self.music_title = ElideLabel("Ничего не играет")
        self.music_title.setStyleSheet("font-size: 17px; font-weight: 700;")
        self.music_artist = ElideLabel("")
        self.music_artist.setObjectName("sub")
        self.music_artist.setStyleSheet("font-size: 14px;")
        info.addLayout(srow)
        info.addSpacing(6)
        info.addWidget(self.music_title)
        info.addWidget(self.music_artist)
        info.addStretch(1)
        top.addWidget(self.art)
        top.addLayout(info, 1)
        cl.addLayout(top)
        cl.addSpacing(2)
        self.progress = ProgressBar()
        self.progress.seek.connect(self.on_seek)
        cl.addWidget(self.progress)
        trow = QHBoxLayout()
        self.time_l = self.sub_label("0:00", 11)
        self.time_r = self.sub_label("--:--", 11)
        trow.addWidget(self.time_l)
        trow.addStretch(1)
        trow.addWidget(self.time_r)
        cl.addLayout(trow)

        self.media = MediaWorker()
        self.btn_prev = IconButton("prev", 38)
        self.play_btn = IconButton("play", 44)
        self.btn_next = IconButton("next", 38)
        self.btn_prev.clicked.connect(self.media.prev)
        self.play_btn.clicked.connect(self.media.toggle)
        self.btn_next.clicked.connect(self.media.next)
        ctrl = QHBoxLayout()
        ctrl.setSpacing(22)
        ctrl.addStretch(1)
        for b in (self.btn_prev, self.play_btn, self.btn_next):
            ctrl.addWidget(b)
        ctrl.addStretch(1)
        cl.addLayout(ctrl)
        self.media.changed.connect(self.on_media)
        self.media.thumb.connect(self.on_thumb)
        left.addWidget(self.player_card, 1)

        vol = self.card()
        vl = QHBoxLayout(vol)
        vl.setContentsMargins(10, 0, 14, 0)
        vl.setSpacing(8)
        self.spk = QPushButton()
        self.spk.setIconSize(QSize(20, 20))
        self.spk.setObjectName("spk")
        self.spk.setFixedSize(32, 32)
        self.spk.setCursor(Qt.PointingHandCursor)
        self.spk.setFocusPolicy(Qt.NoFocus)
        self.spk.clicked.connect(self.mute_clicked)
        self.vol_slider = ClickSlider(Qt.Horizontal)
        self.vol_slider.setFocusPolicy(Qt.NoFocus)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.valueChanged.connect(self.on_vol_changed)
        self.vol_label = QLabel("--")
        self.vol_label.setFixedWidth(26)
        self.vol_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vl.addWidget(self.spk)
        vl.addWidget(self.vol_slider, 1)
        vl.addWidget(self.vol_label)
        vol.setFixedHeight(44)
        left.addWidget(vol)
        mid.addLayout(left, 11)

        # ---- правая колонка: кнопки-инструменты ----
        grid = QGridLayout()
        grid.setSpacing(8)
        funcs = [("area", "Область", self.act_area), ("screen", "Весь экран", self.act_full),
                 ("ocr", "Текст с экрана", self.act_ocr), ("qr", "QR-код", self.act_qr),
                 ("pick", "Пипетка", self.act_pick), ("clean", "Чистый текст", self.act_clean),
                 ("record", "Запись экрана", self.act_rec), ("command", "Команда", self.act_cmd)]
        self.fn_icons = []
        self.fn_btns = {}
        self.fn_grid = grid
        for i, (icon_name, label, fn) in enumerate(funcs):
            b = QPushButton("  " + label)
            b.setObjectName("fn")
            b.setIconSize(QSize(18, 18))
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            b.clicked.connect(fn)
            self.fn_btns[icon_name] = b
            self.fn_icons.append((b, icon_name))
            if icon_name == "record":
                self.rec_btn = b
        mid.addLayout(grid, 9)
        pv.addLayout(mid, 1)
        self.layout_fn()

        # ---- док с программами ----
        self.dock = self.card()
        self.dock_layout = QHBoxLayout(self.dock)
        self.dock_layout.setContentsMargins(10, 6, 10, 6)
        self.dock_layout.setSpacing(8)
        self.dock.setFixedHeight(58)
        pv.addWidget(self.dock)
        self.rebuild_dock()
        return page

    def build_clipboard(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.clip_search = QLineEdit()
        self.clip_search.setPlaceholderText("Поиск по буферу…")
        self.clip_search.setClearButtonEnabled(True)
        self.clip_search.setFixedHeight(38)
        self.clip_search.setStyleSheet(
            "QLineEdit { border-radius: 19px; padding: 0 14px 0 6px; font-size: 14px; }")
        self.clip_search_act = self.clip_search.addAction(
            make_icon("search", "#8e8e93", size=18), QLineEdit.LeadingPosition)
        self.clip_search.textChanged.connect(self.apply_clip_filter)
        self.clip_search.returnPressed.connect(self.copy_first_clip)
        btn_clear = QPushButton("Очистить")
        btn_clear.setObjectName("seg")
        btn_clear.setFixedHeight(38)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setFocusPolicy(Qt.NoFocus)
        btn_clear.setToolTip("Очистить историю буфера")
        btn_clear.clicked.connect(self.clear_clips)
        top.addWidget(self.clip_search, 1)
        top.addWidget(btn_clear)
        v.addLayout(top)
        self.clip_list = ClipView()
        self.clip_list.itemClicked.connect(self.restore_clip)
        self.clip_list.removeRequested.connect(self.remove_clip)
        v.addWidget(self.clip_list, 1)
        QApplication.clipboard().dataChanged.connect(self.on_clipboard)
        self.clip_tick = QTimer(self)   # обновляем «5 мин назад»
        self.clip_tick.setInterval(30000)
        self.clip_tick.timeout.connect(self.clip_list.viewport().update)
        self.clip_tick.start()
        self.apply_clip_filter()
        return page

    def build_downloads(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.dl_search = QLineEdit()
        self.dl_search.setPlaceholderText("Поиск по загрузкам…")
        self.dl_search.setClearButtonEnabled(True)
        self.dl_search.setFixedHeight(38)
        self.dl_search.setStyleSheet(
            "QLineEdit { border-radius: 19px; padding: 0 14px 0 6px; font-size: 14px; }")
        self.dl_search_act = self.dl_search.addAction(
            make_icon("search", "#8e8e93", size=18), QLineEdit.LeadingPosition)
        self.dl_search.textChanged.connect(self.apply_dl_filter)
        self.dl_search.returnPressed.connect(self.open_first_download)
        btn_dir = QPushButton("Папка")
        btn_dir.setObjectName("seg")
        btn_dir.setFixedHeight(38)
        btn_dir.setCursor(Qt.PointingHandCursor)
        btn_dir.setFocusPolicy(Qt.NoFocus)
        btn_dir.setToolTip("Открыть папку загрузок")
        btn_dir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(DL_DIR)))
        top.addWidget(self.dl_search, 1)
        top.addWidget(btn_dir)
        v.addLayout(top)
        self.dl_list = DlView()
        self.dl_list.itemDoubleClicked.connect(self.open_download)
        self.dl_list.removeRequested.connect(self.remove_download)
        self.dl_list.revealRequested.connect(self.reveal_download)
        v.addWidget(self.dl_list, 1)
        self.dl_tick = QTimer(self)   # время «5 мин» и бегущая полоска у активных загрузок
        self.dl_tick.setInterval(60)
        self.dl_tick.timeout.connect(self._dl_anim)
        self.dl_tick.start()
        self._dl_frames = 0
        self._dl_key = None
        self.refresh_dl_list()
        return page

    def _dl_anim(self):
        self._dl_frames += 1
        has_active = bool(self.dl_state)
        if has_active or self._dl_frames % 500 == 0:   # время обновляем раз в ~30 секунд
            if self.expanded or self._dl_frames % 500 == 0:
                self.dl_list.viewport().update()

    def make_chip(self, icon_name):
        w = QWidget()
        w.setObjectName("chip")
        w.setAttribute(Qt.WA_StyledBackground, True)
        w.setStyleSheet("QWidget#chip { background: rgba(255,255,255,46); border-radius: 12px; }")
        v = QVBoxLayout(w)
        v.setContentsMargins(4, 8, 4, 7)
        v.setSpacing(4)
        ic = QLabel()
        ic.setAlignment(Qt.AlignHCenter)
        ic.setPixmap(make_icon(icon_name, "#ffffff").pixmap(QSize(16, 16)))
        t = QLabel("--")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size: 11px; font-weight: 700; color: white;")
        v.addWidget(ic)
        v.addWidget(t)
        return w, t

    def build_weather(self):
        page = QWidget()
        h = QHBoxLayout(page)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)

        # ---- левая карточка: сейчас ----
        self.w_card = WeatherCard()
        self.w_card.setFixedWidth(232)
        lv = QVBoxLayout(self.w_card)
        lv.setContentsMargins(16, 14, 16, 12)
        lv.setSpacing(0)
        head = QHBoxLayout()
        head.setSpacing(6)
        loc = QLabel()
        loc.setPixmap(make_icon("location", "#ffffff").pixmap(QSize(16, 16)))
        self.city_edit = QLineEdit()
        self.city_edit.setPlaceholderText("Город…")
        self.city_edit.setToolTip("Нажми, впиши город и Enter")
        self.city_edit.setStyleSheet(
            "QLineEdit { background: transparent; border: 0; color: white; font-size: 14px;"
            " font-weight: 700; padding: 0; }"
            "QLineEdit:focus { border-bottom: 1px solid rgba(255,255,255,170); }")
        self.city_edit.returnPressed.connect(self.change_city)
        btn_ref = QPushButton()
        btn_ref.setIcon(make_icon("refresh", "#ffffff"))
        btn_ref.setIconSize(QSize(16, 16))
        btn_ref.setToolTip("Обновить")
        btn_ref.setCursor(Qt.PointingHandCursor)
        btn_ref.setFocusPolicy(Qt.NoFocus)
        btn_ref.setStyleSheet("QPushButton { background: transparent; padding: 4px;"
                              " border-radius: 10px; }"
                              "QPushButton:hover { background: rgba(255,255,255,45); }")
        btn_ref.clicked.connect(lambda: self.weather.refresh())
        head.addWidget(loc)
        head.addWidget(self.city_edit, 1)
        head.addWidget(btn_ref)
        lv.addLayout(head)
        lv.addSpacing(8)
        big = QHBoxLayout()
        big.setSpacing(8)
        self.w_icon = WeatherIcon(60)
        self.w_temp = QLabel("--°")
        self.w_temp.setStyleSheet("font-size: 50px; font-weight: 600; color: white;")
        big.addWidget(self.w_icon)
        big.addWidget(self.w_temp)
        big.addStretch(1)
        lv.addLayout(big)
        lv.addSpacing(8)
        self.w_cond = QLabel("Загрузка…")
        self.w_cond.setWordWrap(True)
        self.w_cond.setStyleSheet("font-size: 15px; font-weight: 700; color: white;")
        self.w_sub = QLabel("")
        self.w_sub.setWordWrap(True)
        self.w_sub.setStyleSheet("font-size: 11px; color: rgba(255,255,255,190);")
        lv.addWidget(self.w_cond)
        lv.addWidget(self.w_sub)
        lv.addStretch(1)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        self.c_wind = self.make_chip("wind")
        self.c_hum = self.make_chip("drop")
        self.c_rain = self.make_chip("umbrella")
        for w, _ in (self.c_wind, self.c_hum, self.c_rain):
            chips.addWidget(w, 1)
        lv.addLayout(chips)
        lv.addSpacing(8)
        srow = QHBoxLayout()
        srow.setSpacing(5)
        for icon_name, attr in (("sunrise", "w_rise"), ("sunset", "w_set")):
            ic = QLabel()
            ic.setPixmap(make_icon(icon_name, "#ffffff").pixmap(QSize(16, 16)))
            t = QLabel("--:--")
            t.setStyleSheet("font-size: 11px; color: rgba(255,255,255,205);")
            setattr(self, attr, t)
            srow.addWidget(ic)
            srow.addWidget(t)
            srow.addSpacing(8)
        srow.addStretch(1)
        lv.addLayout(srow)
        h.addWidget(self.w_card)

        # ---- правая колонка: по часам и по дням ----
        right = QVBoxLayout()
        right.setSpacing(10)
        hourly = self.card()
        hourly.setFixedHeight(100)
        hl = QHBoxLayout(hourly)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.setSpacing(0)
        self.hour_cols = []
        for _ in range(8):
            col = QVBoxLayout()
            col.setSpacing(3)
            t = self.sub_label("", 11)
            t.setAlignment(Qt.AlignCenter)
            ic = WeatherIcon(30)
            tmp = QLabel("")
            tmp.setAlignment(Qt.AlignCenter)
            tmp.setStyleSheet("font-size: 13px; font-weight: 700;")
            col.addWidget(t)
            col.addWidget(ic, 0, Qt.AlignHCenter)
            col.addWidget(tmp)
            hl.addLayout(col, 1)
            self.hour_cols.append((t, ic, tmp))
        right.addWidget(hourly)

        daily = self.card()
        dl = QVBoxLayout(daily)
        dl.setContentsMargins(14, 8, 14, 6)
        dl.setSpacing(0)
        self.day_rows = []
        for _ in range(7):
            row = QHBoxLayout()
            row.setSpacing(8)
            d = QLabel("")
            d.setFixedWidth(66)
            d.setStyleSheet("font-size: 12px; font-weight: 700;")
            ic = WeatherIcon(22)
            lo = self.sub_label("", 12)
            lo.setFixedWidth(30)
            lo.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            bar = RangeBar()
            hi = QLabel("")
            hi.setFixedWidth(30)
            hi.setStyleSheet("font-size: 12px; font-weight: 700;")
            mm = QLabel("")
            mm.setFixedWidth(52)
            mm.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            mm.setStyleSheet("font-size: 11px; color: #6aa9e9;")
            for wgt in (d, ic, lo, bar, hi, mm):
                row.addWidget(wgt, 1 if wgt is bar else 0)
            dl.addLayout(row, 1)
            self.day_rows.append((d, ic, lo, bar, hi, mm))
        src_lbl = self.sub_label("Данные Open-Meteo", 10)
        src_lbl.setAlignment(Qt.AlignRight)
        dl.addWidget(src_lbl)
        right.addWidget(daily, 1)
        h.addLayout(right, 1)
        return page

    def build_timer(self):
        tw = QWidget()
        tl = QVBoxLayout(tw)
        row = QHBoxLayout()
        self.spin = QSpinBox()
        self.spin.setRange(1, 600)
        self.spin.setValue(10)
        self.spin.setSuffix(" мин")
        self.btn_timer = QPushButton("Старт")
        self.btn_timer.clicked.connect(self.toggle_timer)
        row.addStretch(1)
        row.addWidget(self.spin)
        row.addWidget(self.btn_timer)
        row.addStretch(1)
        self.timer_label = QLabel("00:00", alignment=Qt.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 64px; font-weight: 200;")
        tl.addLayout(row)
        tl.addWidget(self.timer_label, 1)
        return tw

    def build_note(self):
        self.note = QPlainTextEdit()
        self.note.setPlaceholderText("Заметка…")
        if os.path.exists(NOTE_FILE):
            with open(NOTE_FILE, encoding="utf-8") as f:
                self.note.setPlainText(f.read())
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(500)
        self.save_timer.timeout.connect(self.save_note)
        self.note.textChanged.connect(self.save_timer.start)
        return self.note

    def build_settings(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        def row(title, widgets):
            c = self.card()
            h = QHBoxLayout(c)
            h.setContentsMargins(18, 0, 12, 0)
            lab = QLabel(title)
            lab.setStyleSheet("font-size: 14px; font-weight: 600;")
            h.addWidget(lab)
            h.addStretch(1)
            for w in widgets:
                h.addWidget(w)
            c.setFixedHeight(44)
            v.addWidget(c)

        def seg(text, checkable=True):
            b = QPushButton(text)
            b.setObjectName("seg")
            b.setCheckable(checkable)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            return b

        # --- тема: выпадающий список с миниатюрами ---
        self.theme_pop = PickPopup(self, cols=4, tile=(104, 86))
        for key in THEME_ORDER:
            self.theme_pop.add_tile(key, THEMES[key]["name"], ThemeSwatch(key, 74, 44))
        self.theme_pop.picked.connect(self.set_theme)
        self.theme_btn = PickButton(ThemeSwatch(self.theme, 42, 26))
        self.theme_btn.clicked.connect(lambda *_: self.open_popup(self.theme_pop, self.theme_btn))
        row("Тема", [self.theme_btn])

        self.btn_autohide = seg("")
        self.btn_autohide.setChecked(self.autohide)
        self.btn_autohide.setText("Вкл" if self.autohide else "Выкл")
        self.btn_autohide.toggled.connect(self.set_autohide)
        row("Скрывать у края экрана", [self.btn_autohide])

        self.btn_desk = seg("")
        self.btn_desk.setChecked(self.hide_on_desktop)
        self.btn_desk.setText("Вкл" if self.hide_on_desktop else "Выкл")
        self.btn_desk.setEnabled(self.autohide)
        self.btn_desk.toggled.connect(self.set_hide_on_desktop)
        self.desk_state = self.sub_label("", 12)
        row("Скрывать на рабочем столе", [self.desk_state, self.btn_desk])

        # --- питомец: выпадающий список, питомцы в нём живые ---
        self.pet_pop = PickPopup(self, cols=3, tile=(104, 90))
        for key in PET_ORDER:
            r = Resident(self.res)
            r.preview = True
            r.setFixedSize(56, 48)
            r.set_kind(key)
            self.pick_res.append(r)
            self.pet_pop.add_tile(key, PET_NAMES[key], r)
        self.pet_pop.picked.connect(self.set_resident)
        pr = Resident(self.res)
        pr.preview = True
        pr.setFixedSize(38, 32)
        self.pick_res.append(pr)
        self.pet_btn = PickButton(pr)
        self.pet_btn.clicked.connect(lambda *_: self.open_popup(self.pet_pop, self.pet_btn))
        row("Питомец", [self.pet_btn])

        self.btn_autostart = seg("")
        self.btn_autostart.setChecked(self.autostart)
        self.btn_autostart.setText("Автозапуск: вкл" if self.autostart else "Автозапуск: выкл")
        self.btn_autostart.toggled.connect(self.set_autostart_pref)
        self.btn_update = seg("Проверить обновления", checkable=False)
        self.btn_update.clicked.connect(self.on_update_clicked)
        b_quit = seg("Выйти", checkable=False)
        b_quit.clicked.connect(QApplication.quit)
        row("Приложение", [self.btn_autostart, self.btn_update, b_quit])
        b_edit = seg("Редактор интерфейса", checkable=False)
        b_edit.clicked.connect(self.open_editor)
        row("Расположение кнопок", [b_edit])
        for pop in (self.theme_pop, self.pet_pop):
            pop.opened.connect(self._popup_opened)
            pop.closed.connect(self._popup_closed)
        v.addStretch(1)
        self.ver_label = self.sub_label(f"Mini-Island · версия {APP_VERSION}", 11)
        self.ver_label.setAlignment(Qt.AlignCenter)
        fx = QGraphicsOpacityEffect(self.ver_label)
        fx.setOpacity(0.45)   # полупрозрачная подпись внизу
        self.ver_label.setGraphicsEffect(fx)
        v.addWidget(self.ver_label)
        self.upd_progress = UpdateProgress()
        self.upd_progress.hide()
        v.addWidget(self.upd_progress)
        return page

    # ---------- обновления ----------
    def set_update_status(self, text):
        self.ver_label.setText(f"Mini-Island · версия {APP_VERSION} · {text}" if text
                               else f"Mini-Island · версия {APP_VERSION}")

    def on_update_clicked(self):
        info = self.update_info
        if info and info.get("status") == "new":
            if info.get("url"):
                self.btn_update.setEnabled(False)
                self.updater.install(info["url"], info.get("size", 0))
            else:   # в релизе нет установщика: открываем страницу релиза
                QDesktopServices.openUrl(QUrl(info.get("page") or RELEASES_PAGE))
            return
        self.btn_update.setEnabled(False)
        self.btn_update.setText("Проверяю…")
        self.set_update_status("проверка обновлений…")
        self.updater.check()

    def on_update_checked(self, info):
        self.update_info = info
        self.btn_update.setEnabled(True)
        st = info.get("status")
        if st == "new":
            self.btn_update.setText(f"Обновить до {info['version']}")
            self.set_update_status(f"доступна версия {info['version']}")
            self.flash(f"Доступно обновление {info['version']}")
        elif st == "latest":
            self.btn_update.setText("Проверить обновления")
            self.set_update_status("установлена последняя версия")
        else:
            self.btn_update.setText("Проверить обновления")
            self.set_update_status("не удалось проверить, нет связи")

    def show_update_progress(self, frac, text):
        """frac: 0..1, None = размер неизвестен; text = подпись под полоской."""
        self.update_frac = frac if frac is not None else -1.0
        self.ver_label.hide()
        self.upd_progress.show()
        self.upd_progress.set_state(frac, text)
        self.update_pill()

    def hide_update_progress(self):
        self.update_frac = None
        self.upd_progress.hide()
        self.ver_label.show()
        self.update_pill()

    def on_update_installing(self, info):
        st = info.get("status")
        if st == "downloading":
            done, total = info.get("done", 0), info.get("total", 0)
            self.btn_update.setText("Скачиваю…")
            if total:
                frac = min(1.0, done / total)
                self.show_update_progress(
                    frac, f"Скачиваю обновление · {int(frac * 100)}% "
                          f"({fmt_size(done)} из {fmt_size(total)})")
            else:
                self.show_update_progress(None, f"Скачиваю обновление · {fmt_size(done)}")
        elif st == "started":
            self.btn_update.setText("Устанавливаю…")
            self.show_update_progress(1.0, "Скачано · запускаю установщик…")
            # закрываем остров сами, чтобы не висел старый экземпляр рядом с новым
            QTimer.singleShot(1200, QApplication.quit)
        else:
            self.hide_update_progress()
            self.btn_update.setEnabled(True)
            self.btn_update.setText("Повторить")
            self.set_update_status("не удалось скачать обновление")

    # ---------- расположение вкладок и кнопок ----------
    def layout_nav(self):
        while self.navrow.count():
            self.navrow.takeAt(0)
        hidden = set(self.nav_hidden)
        for key in self.nav_order:
            b = self.nav_btns[NAV_KEYS.index(key)]
            self.navrow.addWidget(b)
            b.setVisible(key not in hidden)
        self.navrow.addStretch(1)
        self.navrow.addWidget(self.resident_tile)
        self.navrow.addWidget(self.btn_pin)
        self.navrow.addWidget(self.nav_btns[7])

    def layout_fn(self):
        while self.fn_grid.count():
            self.fn_grid.takeAt(0)
        hidden = set(self.fn_hidden)
        shown = [k for k in self.fn_order if k not in hidden]
        for k in self.fn_order:
            self.fn_btns[k].setVisible(k not in hidden)
        for i, k in enumerate(shown):
            self.fn_grid.addWidget(self.fn_btns[k], i // 2, i % 2)

    @staticmethod
    def make_seg(text):
        b = QPushButton(text)
        b.setObjectName("seg")
        b.setCursor(Qt.PointingHandCursor)
        b.setFocusPolicy(Qt.NoFocus)
        return b

    def build_editor(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(8)
        title = QLabel("Редактор интерфейса")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        btn_reset = self.make_seg("Сбросить")
        btn_reset.clicked.connect(self.editor_reset)
        btn_done = self.make_seg("Готово")
        btn_done.clicked.connect(lambda: self.set_page(7))
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(btn_reset)
        head.addWidget(btn_done)
        v.addLayout(head)
        v.addWidget(self.sub_label("Перетащи плитку, чтобы поменять порядок. "
                                   "Нажми на неё, чтобы скрыть или показать.", 12))
        v.addSpacing(2)
        v.addWidget(self.sub_label("Вкладки сверху", 12))
        self.tab_board = DragBoard(4, (150, 38))
        self.tab_board.changed.connect(self.editor_changed)
        v.addWidget(self.tab_board, 0, Qt.AlignLeft)
        v.addSpacing(2)
        v.addWidget(self.sub_label("Кнопки на главной", 12))
        self.fn_board = DragBoard(4, (150, 38))
        self.fn_board.changed.connect(self.editor_changed)
        v.addWidget(self.fn_board, 0, Qt.AlignLeft)
        v.addStretch(1)
        self.fill_editor()
        return page

    def fill_editor(self):
        hid = set(self.nav_hidden)
        self.tab_board.set_items([(k, NAV_LABELS[NAV_KEYS.index(k)], k, k == "home", k not in hid)
                                  for k in self.nav_order])
        fh = set(self.fn_hidden)
        self.fn_board.set_items([(k, FN_LABELS[k], k, False, k not in fh)
                                 for k in self.fn_order])

    def editor_changed(self):
        self.nav_order = self.tab_board.order()
        self.nav_hidden = [k for k in self.tab_board.hidden() if k != "home"]
        self.fn_order = self.fn_board.order()
        self.fn_hidden = self.fn_board.hidden()
        set_cfg(nav_order=self.nav_order, nav_hidden=self.nav_hidden,
                fn_order=self.fn_order, fn_hidden=self.fn_hidden)
        self.layout_nav()
        self.layout_fn()
        self.refresh_nav()

    def editor_reset(self):
        self.nav_order, self.nav_hidden = list(NAV_KEYS[:7]), []
        self.fn_order, self.fn_hidden = list(FN_ORDER), []
        set_cfg(nav_order=self.nav_order, nav_hidden=[], fn_order=self.fn_order, fn_hidden=[])
        self.fill_editor()
        self.layout_nav()
        self.layout_fn()
        self.refresh_nav()

    def open_editor(self):
        self.fill_editor()
        self.nav_group.setExclusive(False)
        for b in self.nav_btns:
            b.setChecked(False)
        self.nav_group.setExclusive(True)
        self.stack.setCurrentIndex(EDITOR_PAGE)
        self.refresh_nav()

    def open_popup(self, popup, btn):
        if time.time() - popup.closed_at < 0.25:  # клик, закрывший список, не должен открыть его снова
            return
        popup.open_for(btn)

    def _popup_opened(self):
        self.busy += 1   # пока список открыт, шторка не сворачивается

    def _popup_closed(self):
        self.busy = max(0, self.busy - 1)
        if not self.underMouse():
            self.collapse_timer.start()

    def set_page(self, i):
        self.stack.setCurrentIndex(i)
        self.nav_btns[i].setChecked(True)
        self.refresh_nav()

    def refresh_nav(self):
        # название показывается только у активной вкладки
        for i, b in enumerate(self.nav_btns):
            b.setText(" " + self.nav_names[i] if b.isChecked() else "")

    # ---------- тема ----------
    def apply_theme(self):
        T = self.T = THEMES[self.theme]
        self.setStyleSheet(STYLE_TPL.substitute(T))
        self.player_card.base = QColor(*T["card_rgba"])
        self.progress.track = QColor(*T["track"])
        for b in (self.btn_prev, self.btn_next):
            b.fg = QColor(T["fg"])
        self.play_btn.bg = QColor(*T["play_bg"])
        self.play_btn.fg = QColor(*T["play_fg"])
        self.apply_icons()
        self.refresh_nav()
        self.update_accent()
        bg = QColor(*T["panel"])
        bg.setAlpha(max(bg.alpha(), 246))
        for pop in (self.theme_pop, self.pet_pop):
            pop.set_colors(bg, QColor(*T["border"]))
        self.clip_list.set_colors(T)
        self.tab_board.set_colors(T)
        self.fn_board.set_colors(T)
        self.upd_progress.set_colors(T)
        self.dl_list.set_colors(T)
        self.dl_search_act.setIcon(make_icon("search", T["sub"], size=18))
        self.clip_search_act.setIcon(make_icon("search", T["sub"], size=18))
        self.theme_btn.set_name(T["name"])
        self.theme_btn.preview.set_key(self.theme)
        self.theme_pop.set_current(self.theme)
        if self.last_weather:
            self.on_weather(self.last_weather)
        self.player_card.update()
        self.update()

    def apply_icons(self):
        T = self.T
        fg, sub_c, chipfg = T["fg"], T["sub"], T["chipfg"]
        for b, name in zip(self.nav_btns, self.nav_icon_names):
            b.setIcon(make_icon(name, sub_c, fg, chipfg))
        self.btn_pin.setIcon(make_icon("pin", sub_c, fg, chipfg, filled_on=True))
        for b, name in self.fn_icons:
            if name != "record":
                b.setIcon(make_icon(name, fg))
        self._spk_icons = {"speaker": make_icon("speaker", fg), "mute": make_icon("mute", fg)}
        self.spk.setIcon(self._spk_icons["speaker"])
        self.refresh_rec_icon()

    def refresh_rec_icon(self):
        if self.recorder.active:
            self.rec_btn.setIcon(make_icon("stop", "#ff453a"))
            self.rec_btn.setText("  Остановить запись")
        else:
            self.rec_btn.setIcon(make_icon("record", self.T["fg"]))
            self.rec_btn.setText("  Запись экрана")

    def set_theme(self, name):
        if name not in THEMES:
            return
        self.theme = name
        set_cfg(theme=name)
        self.apply_theme()

    def set_autostart_pref(self, on):
        self.autostart = on
        self.btn_autostart.setText("Автозапуск: вкл" if on else "Автозапуск: выкл")
        set_cfg(autostart=on)
        sync_autostart(on)

    def set_resident(self, kind):
        self.resident_kind = kind
        set_cfg(resident=kind)
        self.apply_resident()

    def apply_resident(self):
        for r in self.residents:
            r.set_kind(self.resident_kind)
            r.setVisible(self.resident_kind != "none")
        self.pet_btn.preview.set_kind(self.resident_kind)
        self.pet_btn.set_name(PET_NAMES.get(self.resident_kind, ""))
        self.pet_pop.set_current(self.resident_kind)

    def set_hide_on_desktop(self, on):
        self.hide_on_desktop = on
        self.btn_desk.setText("Вкл" if on else "Выкл")
        set_cfg(hide_on_desktop=on)

    def set_autohide(self, on):
        self.autohide = on
        self.btn_autohide.setText("Вкл" if on else "Выкл")
        self.btn_desk.setEnabled(on)
        set_cfg(autohide=on)
        if not on and (self.hidden_state or self._hiding):
            self.reveal(False)

    def toggle_pin(self, *_):
        self.pinned = self.btn_pin.isChecked()

    def update_accent(self):
        a, T = self.accent, self.T
        fg = QColor(T["fg"])
        self.progress.fill = a or (QColor(T["accent"]) if T.get("accent") else fg)
        self.player_card.tint = a
        # эквалайзер: стиль и цвета берём из темы, а цвет обложки трека перекрывает их
        for eq, key, default in ((self.card_eq, "eq_card", fg),
                                 (self.toast_eq, "eq_pill", QColor("#ffffff"))):
            c1, c2 = T.get(key, (None, None))
            eq.style = T.get("eq", "bars")
            eq.color = QColor(a) if a else (QColor(c1) if c1 else default)
            eq.color2 = None if a else (QColor(c2) if c2 else None)
            eq.update()
        self.progress.update()
        self.player_card.update()

    # ---------- геометрия и анимация ----------
    def rect_for(self, w, h):
        scr = QApplication.primaryScreen().geometry()
        return QRect(scr.x() + (scr.width() - w) // 2, scr.y() + TOP_MARGIN, w, h + WAVE_PAD)

    def _set_mix(self, v):
        self.bg_mix = float(v)
        self.update()

    def fade_bg(self, target):
        self.mix_anim.stop()
        self.mix_anim.setStartValue(self.bg_mix)
        self.mix_anim.setEndValue(target)
        self.mix_anim.setDuration(380 if target else 250)
        self.mix_anim.start()

    def expand(self):
        self.collapse_timer.stop()
        self.peek_hover = False
        if self.expanded:
            return
        self.cancel_toast()
        self.expanded = True
        self.root.setContentsMargins(*MARGIN_EXPANDED)
        self.pill_box.hide()
        self.fx.setEnabled(True)
        self.fx.setOpacity(0.0)
        self.body.show()
        self.fade.stop()
        self.fade.start()
        self.fade_bg(1.0)
        curve = QEasingCurve(QEasingCurve.OutBack)
        curve.setOvershoot(0.7)
        self.animate_to(self.rect_for(*EXPANDED), curve, 420)
        self.update_progress()
        self.sync_volume()

    def collapse(self):
        if (not self.expanded or self.pinned or self.busy
                or self.note.hasFocus() or self.city_edit.hasFocus()
                or self.clip_search.hasFocus() or self.dl_search.hasFocus()
                or self.stack.currentIndex() == EDITOR_PAGE):
            return
        if QApplication.mouseButtons() != Qt.NoButton:
            self.collapse_timer.start()
            return
        if self.autohide and not self.recorder.active and not self.desktop_keep():
            self.hide_away()  # шторка уезжает за верхний край экрана
            return
        self.expanded = False
        self.fade.stop()
        self.fx.setEnabled(False)
        self.body.hide()
        self.root.setContentsMargins(*MARGIN_COLLAPSED)
        self.pill_box.show()
        self.fade_bg(0.0)
        self.animate_to(self.rect_for(self.collapsed_w, COLLAPSED_H),
                        QEasingCurve(QEasingCurve.OutCubic), 300)

    def animate_to(self, rect, curve, ms):
        self.anim.stop()
        self.anim.setDuration(ms)
        self.anim.setEasingCurve(curve)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(rect)
        self.anim.start()

    def off_y(self, h):
        return QApplication.primaryScreen().geometry().y() - h - 12

    def hide_away(self):
        if self.hidden_state or self._hiding:
            return
        self._hiding = True
        self.collapse_timer.stop()
        r = self.geometry()
        r.moveTop(self.off_y(r.height()))
        self.animate_to(r, QEasingCurve(QEasingCurve.InCubic), 330)

    def _anim_done(self):
        if not self._hiding:
            return
        self._hiding = False
        self.hidden_state = True
        self.peek_hover = False
        self.hide()
        # возвращаем свёрнутое состояние, чтобы следующий показ начинался с чистого листа
        self.expanded = False
        self.fade.stop()
        self.fx.setEnabled(False)
        self.body.hide()
        self.pill_box.show()
        self.root.setContentsMargins(*MARGIN_COLLAPSED)
        self.mix_anim.stop()
        self.bg_mix = 0.0
        self.setGeometry(self.rect_for(self.collapsed_w, COLLAPSED_H))

    def reveal(self, expand=True):
        """Показывает остров: expand=True -> шторка, False -> только пилюля."""
        if self._hiding:  # передумали прятать
            self._hiding = False
            if expand and not self.expanded:
                self.expand()
            else:
                target = EXPANDED if self.expanded else (self.collapsed_w, COLLAPSED_H)
                self.animate_to(self.rect_for(*target), QEasingCurve(QEasingCurve.OutCubic), 250)
            return
        if not self.hidden_state:
            if expand:
                self.expand()
            return
        self.hidden_state = False
        self.anim.stop()
        if expand:
            r = self.rect_for(*EXPANDED)
            r.moveTop(self.off_y(EXPANDED[1]))
            self.setGeometry(r)
            self.show()
            self.expand()
        else:
            self.pill_since = time.time()
            r = self.rect_for(self.collapsed_w, COLLAPSED_H)
            r.moveTop(self.off_y(COLLAPSED_H))
            self.setGeometry(r)
            self.show()
            self.animate_to(self.rect_for(self.collapsed_w, COLLAPSED_H),
                            QEasingCurve(QEasingCurve.OutCubic), 300)

    def desktop_keep(self):
        """На рабочем столе остров не прячем (если так выбрано в настройках)."""
        return self.autohide and not self.hide_on_desktop and self.desktop_now

    def update_desktop_state(self, now):
        """Рабочий стол = нет ни одного открытого окна программы. Смена состояния с задержкой 0.5 с."""
        if now - self._desk_t < 0.3:
            return
        self._desk_t = now
        raw = self.winshell.desktop_visible() if self.winshell else False
        if raw == self.desktop_now:
            self._desk_cand = None
        elif self._desk_cand != raw:
            self._desk_cand, self._desk_cand_t = raw, now
        elif now - self._desk_cand_t >= 0.5:
            self.desktop_now, self._desk_cand = raw, None

    def poll_edge(self):
        now = time.time()
        self.update_desktop_state(now)
        if not self.autohide:
            return
        if self.desktop_keep() and (self.hidden_state or self._hiding):
            self.reveal(False)  # рабочий стол: остров остаётся на виду
        scr = QApplication.primaryScreen().geometry()
        pos = QCursor.pos()
        in_x = abs(pos.x() - scr.center().x()) <= EDGE_HALF
        top = pos.y() - scr.top()
        if in_x and top <= EDGE_PX:
            # ступень 2: курсор у самого верха -> шторка открывается полностью
            self._zone_since = None
            if not self.expanded:
                self.reveal(True)
            return
        if in_x and top <= PEEK_PX:
            # ступень 1: курсор у края -> выглядывает пилюля со временем
            if self._zone_since is None:
                self._zone_since = now
            if now - self._zone_since >= PEEK_DELAY and (self.hidden_state or self._hiding):
                self.peek_hover = True
                self.reveal(False)
            self._peek_gone = None
            return
        self._zone_since = None
        # убираем пилюлю, показанную по наведению, когда курсор ушёл
        if (self.peek_hover and not self.expanded and not self.hidden_state
                and not self._hiding):
            if self.underMouse():
                self._peek_gone = None
            elif self._peek_gone is None:
                self._peek_gone = now
            elif now - self._peek_gone > 0.35:
                self.peek_hover = False
                self._peek_gone = None
                self.hide_away()
        else:
            self._peek_gone = None

    def autohide_check(self):
        """Прячет пилюлю, если ничего не происходит."""
        if (self.autohide and not self.hidden_state and not self._hiding
                and not self.expanded and not self.pinned and not self.busy
                and not self.peek_hover and not self.desktop_keep()
                and not self.toast_active
                and not self.underMouse() and not self.recorder.active
                and time.time() > self.flash_until + 0.7
                and time.time() - self.pill_since > 1.5):
            self.hide_away()

    # ---------- музыка: волна нижнего края и жильцы ----------
    def live_tick(self):
        now = time.time()
        dt = max(0.001, min(0.1, now - self._live_t))
        self._live_t = now
        if self.hidden_state:
            return
        R = self.res
        peak = self.meter.peak()
        if peak is None:  # нет pycaw: имитируем ритм, пока играет музыка
            raw = 0.0
            if self.music_playing:
                raw = 0.25 + 0.55 * max(0.0, 1.0 - ((now * 1.9) % 1.0) * 2.2)
        else:
            raw = peak
        self.peak_max = max(raw, self.peak_max * 0.998, 0.04)
        norm = min(1.0, raw / self.peak_max) if raw > 0.012 else 0.0
        R.audio_on = norm > 0.02 and (peak is not None or self.music_playing)
        R.level += (norm - R.level) * (0.55 if norm > R.level else 0.10)
        self.avg += (norm - self.avg) * 0.05
        if norm > self.avg * 1.25 + 0.06 and now - self.last_beat > 0.2:  # удар в музыке
            R.beat, R.dir, self.last_beat = 1.0, -R.dir, now
        R.beat *= math.exp(-dt * 8)
        if now - self._idle_t > 0.25:
            self._idle_t = now
            self.idle = system_idle_seconds()
        target = 1.0 if (self.idle > IDLE_SLEEP and not R.audio_on) else 0.0
        R.sleep += (target - R.sleep) * (1 - math.exp(-dt * (0.7 if target > R.sleep else 5.0)))
        if now > R.next_blink:
            R.blink_until = now + 0.14
            R.next_blink = now + random.uniform(2.2, 6.0)
        R.blink = 1.0 if now < R.blink_until else 0.0
        R.tilt += (R.dir * 8.0 * R.level * (1 - R.sleep) - R.tilt) * 0.25
        active = R.level > 0.003 or R.beat > 0.01
        if active or self._wave_on:
            self._wave_on = active
            self.update(0, max(0, self.height() - WAVE_PAD - 6), self.width(), WAVE_PAD + 8)
        for w in self.residents + self.pick_res:
            if w.isVisible():
                w.update()

    def shape_path(self, amp, now):
        """Силуэт острова. Нижний край выгибается волной в такт музыке."""
        R = self.res
        w, h = self.width(), self.height()
        left, right, top = 0.5, w - 0.5, 0.5
        base = h - WAVE_PAD - 0.5
        r = max(1.0, min((base - top) / 2, 34.0))
        active = R.level > 0.004 or R.beat > 0.01

        x0, x1 = left + r, right - r         # ровный участок между скруглёнными углами
        span = max(x1 - x0, 1.0)

        fm, am = self.T.get("wave", (1.0, 1.0))   # тема меняет частоту и размах волны

        def wave(x):
            if not active:
                return 0.0
            # огибающая: ровно 0 и нулевой наклон у углов, поэтому стыка с дугой не видно
            s = min(1.0, min((x - x0) / span, (x1 - x) / span) / 0.22)
            s = max(0.0, s)
            env = s * s * (3 - 2 * s)
            pat = (0.5 + 0.5 * math.sin(x * 0.05 * fm + now * 5.5)) \
                * (0.62 + 0.38 * math.sin(x * 0.018 * fm - now * 2.4 + 1.7))
            bump = R.beat * 0.3 * (0.5 + 0.5 * math.sin(x * 0.09 * fm + now * 9))
            return amp * am * env * min(1.0, R.level * (0.25 + 0.85 * pat) + bump)

        path = QPainterPath()
        path.moveTo(left + r, top)
        path.lineTo(right - r, top)
        path.arcTo(QRectF(right - 2 * r, top, 2 * r, 2 * r), 90, -90)
        path.lineTo(right, base - r)
        path.arcTo(QRectF(right - 2 * r, base - 2 * r, 2 * r, 2 * r), 0, -90)
        n = max(2, int(span // 2.5))
        for i in range(n + 1):
            x = x1 - span * i / n
            path.lineTo(x, base + wave(x))
        path.arcTo(QRectF(left, base - 2 * r, 2 * r, 2 * r), 270, -90)
        path.lineTo(left, top + r)
        path.arcTo(QRectF(left, top, 2 * r, 2 * r), 180, -90)
        path.closeSubpath()
        return path

    # ---------- события ----------
    def enterEvent(self, e):
        if self._hiding:
            self.reveal(True)
        elif self.peek_hover and not self.expanded:
            pass  # пилюлю по наведению к краю раскрывает только курсор у самого верха или клик
        else:
            self.expand()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.expanded:
            self.expand()
        else:
            super().mousePressEvent(e)

    def leaveEvent(self, e):
        self.collapse_timer.start()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            self.expand()
            self.set_page(6)
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.shelf.add_paths([u.toLocalFile() for u in e.mimeData().urls()])
        e.acceptProposedAction()

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.addAction("Выход", QApplication.quit)
        menu.exec(e.globalPos())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m, T = self.bg_mix, self.T
        fill = lerp_c(QColor(*T.get("pill", (0, 0, 0))), QColor(*T["panel"]), m)
        border = lerp_c(QColor(255, 255, 255, 40), QColor(*T["border"]), m)
        path = self.shape_path(5.5 + 6.5 * m, time.time())
        p.setBrush(fill)
        p.setPen(QPen(border, 1))
        p.drawPath(path)
        if self.accent and m > 0:  # мягкое свечение цвета обложки
            g = QLinearGradient(0, 0, self.width(), self.height() - WAVE_PAD)
            c1, c2 = QColor(self.accent), QColor(self.accent)
            c1.setAlpha(int(55 * m))
            c2.setAlpha(0)
            g.setColorAt(0, c1)
            g.setColorAt(0.7, c2)
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawPath(path)

    # ---------- табло в свёрнутом виде ----------
    def flash(self, text, secs=5):
        self.flash_text = text
        self.flash_until = time.time() + secs
        if self.autohide and (self.hidden_state or self._hiding):
            self.reveal(False)  # событие: на время показываем пилюлю

    def update_pill(self):
        music = idle = False
        if time.time() < self.flash_until:
            text = self.flash_text
        elif self.update_frac is not None:
            text = ("↓ Обновление…" if self.update_frac < 0
                    else f"↓ Обновление {int(self.update_frac * 100)}%")
        elif self.recorder.active:
            m, s = divmod(int(time.time() - self.rec_start), 60)
            text = f"● REC {m:02d}:{s:02d}"
        elif self.timer_running:
            m, s = divmod(self.remaining, 60)
            text = f"{m:02d}:{s:02d}"
        elif self.downloads_active:
            text = f"↓ {fmt_size(self.dl_speed)}/с"
        elif self.music_playing and self.title:
            text = QTime.currentTime().toString("HH:mm")   # название не пишем: обложка и время
            music = True
        else:
            text = QTime.currentTime().toString("HH:mm")
            idle = True
            if self.weather_temp:
                text += "  " + self.weather_temp
        self.pill.setText(text)
        show_w = idle and bool(self.weather_kind)
        self.pill_wicon.setVisible(show_w)
        if show_w:
            self.pill_wicon.set_kind(self.weather_kind)
        self.mini_art.setVisible(music)
        width = MUSIC_PILL_W if music else 200
        # надпись занимает ровно столько места, сколько ей нужно: тогда значок погоды
        # стоит вплотную к градусам, а вся группа по центру пилюли
        fnt = QFont(self.font())
        fnt.setPixelSize(13)
        fnt.setWeight(QFont.DemiBold)
        art_w = 0 if self.mini_art.isHidden() else self.mini_art.width()
        pet_w = 0 if self.resident_pill.isHidden() else self.resident_pill.width()
        ico_w = 0 if self.pill_wicon.isHidden() else self.pill_wicon.width() + 5
        items = 3 + (art_w > 0) + (pet_w > 0)      # растяжка, надпись, растяжка + обложка, питомец
        avail = width - 28 - art_w - pet_w - ico_w - 8 * (items - 1)
        self.pill.setFixedWidth(int(max(20, min(
            QFontMetrics(fnt).horizontalAdvance(text) + 10, avail))))
        if width != self.collapsed_w:
            self.collapsed_w = width
            if (not self.expanded and not self.hidden_state and not self._hiding
                    and not self.toast_active):
                self.animate_to(self.rect_for(width, COLLAPSED_H),
                                QEasingCurve(QEasingCurve.OutCubic), 300)

    # ---------- музыка ----------
    def current_pos(self):
        p = self.pos + ((time.monotonic() - self.pos_stamp) if self.music_playing else 0)
        return min(p, self.dur) if self.dur > 0 else p

    def on_media(self, title, artist, playing, available, pos, dur, source):
        self.title, self.artist, self.music_playing = title, artist, playing
        key = (title, artist) if (available and title) else None
        if key is None:
            self.track_key = None
        elif key != self.track_key and playing:
            self.track_key = key
            self.queue_toast()
        self.pos, self.dur, self.pos_stamp = pos, dur, time.monotonic()
        if not available:
            self.music_title.setText("Музыка недоступна")
            self.music_artist.setText("Нужен Windows 10/11 и пакеты winrt-* (см. README)")
            self.music_src.setText("")
        else:
            self.music_title.setText(title or "Ничего не играет")
            self.music_artist.setText(artist)
            self.music_src.setText(source if title else "")
        self.play_btn.set_kind("pause" if playing else "play")
        self.card_eq.set_active(playing)
        self.update_progress()
        self.update_pill()

    def on_thumb(self, data):
        pix = None
        if data:
            pm = QPixmap()
            if pm.loadFromData(data):
                pix = pm
        self.art.set_pixmap(pix)
        self.mini_art.set_pixmap(pix)
        self.toast_art.set_pixmap(pix)
        if self._toast_wait:       # ждали обложку нового трека
            self.start_toast()
        self.accent = None
        if pix:
            c = pix.toImage().scaled(1, 1, Qt.IgnoreAspectRatio,
                                     Qt.SmoothTransformation).pixelColor(0, 0)
            h, s, v, _ = c.getHsv()
            if h >= 0 and s > 40:
                a = QColor()
                a.setHsv(h, min(255, max(s, 140)), 230)
                self.accent = a
        self.update_accent()
        self.update()

    # ---------- показ нового трека в компактном режиме ----------
    def queue_toast(self):
        self._toast_wait = True
        QTimer.singleShot(650, self.start_toast)   # даём время подгрузиться обложке

    def start_toast(self):
        if not self._toast_wait:
            return
        self._toast_wait = False
        if self.expanded or not self.title:
            return                                  # шторка открыта: плеер и так виден
        self.toast_title.setText(self.title)
        self.toast_artist.setText(self.artist)
        self.toast_artist.setVisible(bool(self.artist))
        f1, f2 = QFont(self.font()), QFont(self.font())
        f1.setPixelSize(15)
        f1.setBold(True)
        f2.setPixelSize(12)
        need = max(QFontMetrics(f1).horizontalAdvance(self.title),
                   QFontMetrics(f2).horizontalAdvance(self.artist or ""))
        scr_w = QApplication.primaryScreen().geometry().width()
        self.toast_w = int(max(300, min(need + 14 + 56 + 12 + 14 + 18 + 18, 480, scr_w - 40)))
        self._toast_gen += 1
        self.toast_eq.set_active(self.music_playing)
        if self.hidden_state or self._hiding:
            self.reveal(False)                      # остров был спрятан: показываем его
        curve = QEasingCurve(QEasingCurve.OutBack)
        curve.setOvershoot(0.6)
        if not self.toast_active:
            self.toast_active = True
            self.pill_box.hide()
            self.root.setContentsMargins(*TOAST_MARGINS)
            self.toast_box.show()
            self.toast_fade.stop()
            self.toast_fade.setStartValue(self.toast_fx.opacity())
            self.toast_fade.setEndValue(1.0)
            self.toast_fade.setDuration(380)
            self.toast_fade.setEasingCurve(QEasingCurve(QEasingCurve.InOutCubic))
            self.toast_fade.start()
            self.animate_to(self.rect_for(self.toast_w, TOAST_H), curve, 440)
        else:                                        # трек сменился, пока показ ещё идёт
            self.toast_fade.stop()
            self.toast_fx.setOpacity(1.0)
            self.animate_to(self.rect_for(self.toast_w, TOAST_H), curve, 300)
        self.toast_timer.start(int(TOAST_SECS * 1000))

    def end_toast(self):
        """Гасим содержимое и плавно возвращаем компактный размер."""
        if not self.toast_active:
            return
        gen = self._toast_gen
        self.toast_fade.stop()
        self.toast_fade.setStartValue(self.toast_fx.opacity())
        self.toast_fade.setEndValue(0.0)
        self.toast_fade.setDuration(170)
        self.toast_fade.setEasingCurve(QEasingCurve(QEasingCurve.InCubic))
        self.toast_fade.start()
        QTimer.singleShot(180, lambda: self._finish_toast(gen))

    def _finish_toast(self, gen):
        if gen != self._toast_gen or not self.toast_active or self.expanded:
            return                                  # за это время показ обновили или отменили
        self.toast_active = False
        self.toast_box.hide()
        self.pill_box.show()
        self.root.setContentsMargins(*MARGIN_COLLAPSED)
        self.pill_since = time.time()
        self.update_pill()
        self.animate_to(self.rect_for(self.collapsed_w, COLLAPSED_H),
                        QEasingCurve(QEasingCurve.OutCubic), 360)

    def cancel_toast(self):
        """Мгновенно убирает показ трека (например, когда шторка раскрывается)."""
        self._toast_wait = False
        self._toast_gen += 1
        self.toast_timer.stop()
        self.toast_fade.stop()
        self.toast_fx.setOpacity(0.0)
        self.toast_active = False
        self.toast_box.hide()

    def on_seek(self, frac):
        if self.dur > 0:
            self.pos, self.pos_stamp = frac * self.dur, time.monotonic()
            self.media.seek(frac * self.dur)

    def update_progress(self):
        if not self.expanded or self.progress.dragging:
            return
        p, d = self.current_pos(), self.dur
        self.progress.set_fraction(p / d if d > 0 else 0)
        self.time_l.setText(fmt_time(p))
        self.time_r.setText("-" + fmt_time(d - p) if d > 0 else "--:--")

    # ---------- громкость ----------
    def sync_volume(self):
        if not self.volume.ok:
            self.vol_slider.setEnabled(False)
            self.vol_slider.setToolTip("Громкость недоступна: " + (
                self.volume.error or "нет доступа к звуку Windows") + " (подробности в .island_log.txt)")
            return
        if not self.vol_slider.isEnabled():
            self.vol_slider.setEnabled(True)
            self.vol_slider.setToolTip("")
        if self.vol_slider.isSliderDown():
            return
        v = self.volume.get()
        if v is not None:
            self._vol_sync = True
            self.vol_slider.setValue(v)
            self.vol_label.setText(str(v))
            self._vol_sync = False
        self.spk.setIcon(self._spk_icons["mute" if self.volume.muted() else "speaker"])

    def on_vol_changed(self, v):
        self.vol_label.setText(str(v))
        if not self._vol_sync:
            self.volume.set(v)

    def mute_clicked(self):
        self.volume.toggle_mute()
        self.sync_volume()

    # ---------- док ----------
    def rebuild_dock(self):
        while self.dock_layout.count():
            it = self.dock_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for path in self.dock_paths:
            b = QPushButton()
            b.setObjectName("dockbtn")
            try:
                icon = self.icons.icon(QFileInfo(path))
            except Exception as ex:
                log(f"dock icon: {ex}", once=True)
                icon = QIcon()
            if icon.isNull():
                icon = self.style().standardIcon(QStyle.SP_FileIcon)
            b.setIcon(icon)
            b.setIconSize(QSize(28, 28))
            b.setFixedSize(44, 44)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setToolTip(os.path.splitext(os.path.basename(path))[0])
            b.clicked.connect(lambda _=False, p=path: self.launch(p))
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(
                lambda pos, p=path, btn=b: self.dock_menu(p, btn, pos))
            self.dock_layout.addWidget(b)
        add = QPushButton("+")
        add.setObjectName("dockadd")
        add.setFixedSize(44, 44)
        add.setCursor(Qt.PointingHandCursor)
        add.setFocusPolicy(Qt.NoFocus)
        add.setToolTip("Добавить программу")
        add.clicked.connect(self.dock_add)
        self.dock_layout.addWidget(add)
        self.dock_layout.addStretch(1)

    def launch(self, path):
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception:
            self.flash("⚠ Не удалось запустить", 4)

    def dock_add(self):
        # Диалог Qt без системного окна Windows: родное окно выбора файла падало
        # из-за конфликта COM-режимов (winrt/pycaw). Родителя нет, чтобы стили острова
        # не перекрашивали диалог.
        path = ""
        self.busy += 1
        try:
            dlg = QFileDialog(None, "Добавить программу")
            dlg.setOption(QFileDialog.DontUseNativeDialog, True)
            dlg.setFileMode(QFileDialog.ExistingFile)
            dlg.setNameFilter("Программы (*.exe *.lnk);;Все файлы (*)")
            dlg.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            if dlg.exec() and dlg.selectedFiles():
                path = dlg.selectedFiles()[0]
        except Exception as ex:
            log(f"dock_add dialog: {ex}", once=True)
        finally:
            self.busy = max(0, self.busy - 1)
        path = os.path.normpath(path) if path else ""
        if path and path not in self.dock_paths:
            self.dock_paths.append(path)
            set_cfg(dock=self.dock_paths)
            try:
                self.rebuild_dock()
            except Exception as ex:   # не роняем остров из-за одного значка
                log(f"rebuild_dock: {ex}", once=True)
                self.dock_paths.remove(path)
                set_cfg(dock=self.dock_paths)
                self.rebuild_dock()
                self.flash("⚠ Не удалось добавить", 4)
        self.collapse_timer.start()

    def dock_menu(self, path, btn, pos):
        menu = QMenu(self)
        menu.addAction("Убрать из дока")
        self.busy += 1
        chosen = menu.exec(btn.mapToGlobal(pos))
        self.busy -= 1
        if chosen:
            self.dock_paths.remove(path)
            set_cfg(dock=self.dock_paths)
            self.rebuild_dock()

    # ---------- инструменты: скриншоты, OCR, QR, пипетка ----------
    def snap(self, callback):
        """Прячет остров, снимает экран и отдаёт QPixmap в callback."""
        self.busy += 1
        self.hide()

        def go():
            pix = QApplication.primaryScreen().grabWindow(0)
            self.show()
            self.busy -= 1
            self.collapse_timer.start()
            callback(pix)

        QTimer.singleShot(250, go)

    def open_overlay(self, pix, mode, slot):
        self.ov = ScreenOverlay(pix, mode)
        self.ov.done.connect(slot)
        self.ov.show_full()

    def save_shot(self, img):
        if img is None or img.isNull():
            return
        QApplication.clipboard().setImage(img)
        folder = os.path.join(HOME, "Pictures", "Island")
        try:
            os.makedirs(folder, exist_ok=True)
            img.save(os.path.join(folder, datetime.now().strftime("shot-%Y%m%d-%H%M%S.png")))
            self.flash("✓ Скриншот скопирован и сохранён")
        except OSError:
            self.flash("✓ Скриншот скопирован")

    def act_area(self):
        self.snap(lambda pix: self.open_overlay(pix, "region", self.save_shot))

    def act_full(self):
        self.snap(lambda pix: self.save_shot(pix.toImage()))

    def act_ocr(self):
        self.snap(lambda pix: self.open_overlay(pix, "region", self.run_ocr))

    def run_ocr(self, img):
        if img is None:
            return
        self.flash("Распознаю текст…", 30)
        self.ocr.run(img)

    def on_ocr(self, text, err):
        if err:
            self.flash("⚠ OCR: " + err[:40], 8)
        elif text.strip():
            QApplication.clipboard().setText(text.strip())
            self.flash("✓ Текст скопирован")
        else:
            self.flash("Текст не найден")

    def act_qr(self):
        self.snap(lambda pix: self.open_overlay(pix, "region", self.read_qr))

    def read_qr(self, img):
        if img is None:
            return
        try:
            import cv2
            import numpy as np
            img = img.convertToFormat(QImage.Format_RGB888)
            w, h, bpl = img.width(), img.height(), img.bytesPerLine()
            arr = np.frombuffer(bytes(img.constBits()), np.uint8)[:bpl * h].reshape(h, bpl)
            arr = np.ascontiguousarray(arr[:, :w * 3].reshape(h, w, 3)[:, :, ::-1])
            det, text = cv2.QRCodeDetector(), ""
            for scale in (1, 2):
                frame = arr if scale == 1 else cv2.resize(arr, None, fx=2, fy=2)
                text, _, _ = det.detectAndDecode(frame)
                if text:
                    break
        except ImportError:
            self.flash("⚠ Нужен opencv (см. README)", 6)
            return
        except Exception:
            text = ""
        if text:
            QApplication.clipboard().setText(text)
            self.flash("✓ QR: " + text, 6)
        else:
            self.flash("QR-код не найден")

    def act_pick(self):
        self.snap(lambda pix: self.open_overlay(pix, "pick", self.on_color))

    def on_color(self, c):
        if c is not None:
            QApplication.clipboard().setText(c.name().upper())
            self.flash("✓ " + c.name().upper())

    def act_clean(self):
        cb = QApplication.clipboard()
        t = cb.text()
        if not t:
            self.flash("Буфер пуст")
            return
        self._own_clip = True
        cb.setText(t)  # остаётся только простой текст, без форматирования
        QTimer.singleShot(300, lambda: setattr(self, "_own_clip", False))
        self.flash("✓ Форматирование убрано")

    def act_rec(self):
        if self.recorder.active:
            self.recorder.stop()
            self.refresh_rec_icon()
            self.flash("✓ Запись сохранена в Видео\\Island", 6)
            return
        folder = os.path.join(HOME, "Videos", "Island")
        try:
            os.makedirs(folder, exist_ok=True)
            self.recorder.start(os.path.join(
                folder, datetime.now().strftime("record-%Y%m%d-%H%M%S.mp4")))
        except Exception:
            self.flash("⚠ Нужны mss и opencv (см. README)", 8)
            return
        self.rec_start = time.time()
        self.refresh_rec_icon()

    def act_cmd(self):
        self.cmdbar.popup()

    # ---------- командная строка ----------
    def run_command(self, text):
        t = text.strip()
        low = t.lower()
        m = re.match(r"^(?:таймер|timer)\s+(\d+(?:[.,]\d+)?)\s*(сек|с|s|мин|м|m|час|ч|h)?", low)
        if m:
            n = float(m.group(1).replace(",", "."))
            unit = (m.group(2) or "мин")[0]
            secs = n * {"с": 1, "s": 1, "м": 60, "m": 60, "ч": 3600, "h": 3600}[unit]
            self.remaining, self.timer_running = int(secs), True
            self.btn_timer.setText("Стоп")
            self.update_pill()
            return
        r = calc_text(t)
        if r:
            QApplication.clipboard().setText(r)
            self.flash(f"= {r}  (скопировано)", 6)
            return
        if os.path.exists(t):
            self.launch(t)
            return
        if re.match(r"^(https?://|www\.)\S+$", t, re.I) or (
                re.match(r"^[\w-]+(\.[\w-]+)+(/\S*)?$", t)
                and not re.search(r"\.(txt|exe|pdf|docx?|xlsx?|png|jpe?g|zip|lnk)$", low)):
            QDesktopServices.openUrl(QUrl(t if "://" in t else "https://" + t))
            return
        m = re.match(r"^(?:найти|поиск|search|g)\s+(.+)$", t, re.I)
        if m:
            QDesktopServices.openUrl(QUrl("https://www.google.com/search?q=" + quote(m.group(1))))
            return
        try:
            os.startfile(t)  # программа по имени: notepad, calc, chrome...
        except Exception:
            QDesktopServices.openUrl(QUrl("https://www.google.com/search?q=" + quote(t)))

    # ---------- погода ----------
    def change_city(self):
        name = self.city_edit.text().strip()
        if name:
            self.w_cond.setText("Ищу…")
            self.weather.refresh(name)
        self.city_edit.clearFocus()

    def on_weather(self, data):
        if "error" in data:
            self.w_cond.setText(data["error"])
            self.w_sub.setText("")
            return
        self.last_weather = data
        cur, hr, dl = data["current"], data["hourly"], data["daily"]
        kind, text = wmo(cur["weather_code"], cur["is_day"])
        temp = round(cur["temperature_2m"])
        self.weather_kind, self.weather_temp = kind, f"{temp}°"
        self.w_card.set_colors(*weather_gradient(kind))
        self.w_icon.set_kind(kind)
        self.w_temp.setText(f"{temp}°")
        self.w_cond.setText(text)
        self.w_sub.setText(f"Ощущается как {round(cur['apparent_temperature'])}° · "
                           f"{round(dl['temperature_2m_min'][0])}°…"
                           f"{round(dl['temperature_2m_max'][0])}°")
        if not self.city_edit.hasFocus():
            self.city_edit.setText(data.get("city", ""))
        wind = cur.get("wind_speed_10m")
        self.c_wind[1].setText(
            f"{wind:.0f} м/с {compass(cur.get('wind_direction_10m'))}".strip()
            if wind is not None else "--")
        hum = cur.get("relative_humidity_2m")
        self.c_hum[1].setText(f"{hum:.0f}%" if hum is not None else "--")
        self.c_rain[1].setText(fmt_mm(dl["precipitation_sum"][0] or 0))
        self.w_rise.setText(dl["sunrise"][0][11:16])
        self.w_set.setText(dl["sunset"][0][11:16])

        prefix = cur["time"][:13]
        times = hr["time"]
        idx = next((i for i, t in enumerate(times) if t.startswith(prefix)), 0)
        for k, (t, ic, tmp) in enumerate(self.hour_cols):
            j = idx + k
            if j >= len(times):
                t.setText("")
                ic.set_kind("")
                tmp.setText("")
                continue
            kk, _ = wmo(hr["weather_code"][j], hr["is_day"][j])
            t.setText("Сейчас" if k == 0 else f"{int(times[j][11:13])}:00")
            ic.set_kind(kk)
            tmp.setText(f"{round(hr['temperature_2m'][j])}°")

        n = min(7, len(dl["time"]))
        lows, highs = dl["temperature_2m_min"][:n], dl["temperature_2m_max"][:n]
        gmin, gmax = min(lows), max(highs)
        for k, (d, ic, lo, bar, hi, mm) in enumerate(self.day_rows):
            if k >= n:
                d.setText("")
                ic.set_kind("")
                lo.setText("")
                hi.setText("")
                mm.setText("")
                bar.set_range(0, 0, 0, 1)
                continue
            kk, _ = wmo(dl["weather_code"][k], 1)
            wd = DAYS[datetime.strptime(dl["time"][k], "%Y-%m-%d").weekday()]
            d.setText("Сегодня" if k == 0 else wd)
            ic.set_kind(kk)
            lo.setText(f"{round(lows[k])}°")
            hi.setText(f"{round(highs[k])}°")
            bar.set_range(lows[k], highs[k], gmin, gmax)
            rain = dl["precipitation_sum"][k] or 0
            mm.setText(fmt_mm(rain) if rain >= 0.1 else "")

        if cur["weather_code"] not in RAIN_CODES and self.rain_warned != prefix:
            for j in range(idx + 1, min(idx + 3, len(times))):
                if (hr["precipitation_probability"][j] or 0) >= 60 \
                        and hr["weather_code"][j] in RAIN_CODES:
                    self.rain_warned = prefix
                    self.flash("Скоро дождь", 10)
                    break
        self.update_pill()

    # ---------- загрузки ----------
    def scan_downloads(self):
        now = time.time()
        current, recent = {}, []
        try:
            for name in os.listdir(DL_DIR):
                path = os.path.join(DL_DIR, name)
                try:
                    if name.lower().endswith(PARTIAL_EXT):
                        current[path] = os.path.getsize(path)
                    elif now - os.path.getmtime(path) < 6 and os.path.isfile(path):
                        recent.append((os.path.getmtime(path), name, path))
                except OSError:
                    continue
        except OSError:
            return
        for path, size in current.items():
            prev = self.dl_state.get(path)
            speed = 0.0
            if prev:
                inst = max(0.0, (size - prev["size"]) / max(now - prev["t"], 0.001))
                speed = 0.6 * inst + 0.4 * prev["speed"]
            self.dl_state[path] = {"size": size, "t": now, "speed": speed}
        for path in [p for p in self.dl_state if p not in current]:
            self.dl_state.pop(path)
            if recent:
                recent.sort(reverse=True)
                mt, name, full = recent[0]
                try:
                    size = os.path.getsize(full)
                except OSError:
                    size = 0
                self.dl_done = [d for d in self.dl_done if d["path"] != full]
                self.dl_done.insert(0, {"name": name, "path": full, "size": size, "t": mt})
                self.dl_done = self.dl_done[:60]
                self.flash("✓ " + name)
        self.dl_speed = sum(s["speed"] for s in self.dl_state.values())
        self.downloads_active = any(s["speed"] > 1 for s in self.dl_state.values())
        self.refresh_dl_list()

    def refresh_dl_list(self):
        key = (tuple(self.dl_state), tuple((d["path"], d["t"]) for d in self.dl_done))
        if key == self._dl_key:
            # состав списка не изменился: обновляем только размер и скорость у активных
            for i in range(self.dl_list.count()):
                it = self.dl_list.item(i)
                if it.data(KIND_ROLE) == "active":
                    path = next((q for q in self.dl_state
                                 if it.data(TITLE_ROLE) == self._dl_name(q)), None)
                    if path:
                        st = self.dl_state[path]
                        it.setData(SUB_ROLE, f"{fmt_size(st['size'])} · {fmt_size(st['speed'])}/с")
            self.dl_list.viewport().update()
            return
        self._dl_key = key
        bar = self.dl_list.verticalScrollBar()
        pos = bar.value()
        self.dl_list.clear()
        for path, st in self.dl_state.items():
            name = self._dl_name(path)
            it = QListWidgetItem()
            it.setData(KIND_ROLE, "active")
            it.setData(TITLE_ROLE, name)
            it.setData(SUB_ROLE, f"{fmt_size(st['size'])} · {fmt_size(st['speed'])}/с")
            it.setData(FIND_ROLE, (name + " загружается идёт").lower())
            it.setData(TIME_ROLE, time.time())
            self.dl_list.addItem(it)
        for d in self.dl_done:
            color, label, ext = dl_kind(d["name"])
            it = QListWidgetItem()
            it.setData(Qt.UserRole, d["path"])
            it.setData(KIND_ROLE, "done")
            it.setData(THUMB_ROLE, color)       # цвет значка
            it.setData(TITLE_ROLE, d["name"])
            it.setData(SUB_ROLE, f"{fmt_size(d['size'])} · {label}")
            # первая строка FIND_ROLE: подпись на значке, дальше то, по чему ищем
            it.setData(FIND_ROLE, f"{ext}\n{d['name']} {label} {ext}".lower())
            it.setData(TIME_ROLE, d["t"])
            self.dl_list.addItem(it)
        self.apply_dl_filter()
        bar.setValue(pos)

    @staticmethod
    def _dl_name(path):
        name = os.path.basename(path)
        for ext in PARTIAL_EXT:
            if name.lower().endswith(ext):
                name = name[:-len(ext)]
        return name

    def apply_dl_filter(self, *_):
        q = self.dl_search.text().strip().lower()
        shown = 0
        for i in range(self.dl_list.count()):
            it = self.dl_list.item(i)
            hay = (it.data(FIND_ROLE) or "").split("\n")[-1]
            ok = not q or q in hay
            it.setHidden(not ok)
            shown += ok
        if shown:
            self.dl_list.hint = ""
        elif self.dl_list.count():
            self.dl_list.hint = "Ничего не найдено"
        else:
            self.dl_list.hint = "Загрузок пока нет\nСкачанные файлы появятся здесь"
        self.dl_list.viewport().update()

    def _dl_path(self, item):
        path = item.data(Qt.UserRole) if item is not None else None
        if path and not os.path.exists(path):
            self.flash("⚠ Файл не найден", 4)
            self.remove_download(item)
            return None
        return path

    def open_download(self, item):
        path = self._dl_path(item)
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_first_download(self):
        for i in range(self.dl_list.count()):
            if not self.dl_list.item(i).isHidden():
                self.open_download(self.dl_list.item(i))
                return

    def reveal_download(self, item):
        path = self._dl_path(item)
        if not path:
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
        except Exception as ex:
            log(f"reveal: {ex}", once=True)

    def remove_download(self, item):
        path = item.data(Qt.UserRole)
        self.dl_done = [d for d in self.dl_done if d["path"] != path]
        self.refresh_dl_list()

    # ---------- буфер обмена ----------
    def on_clipboard(self):
        if self._own_clip:
            return
        cb = QApplication.clipboard()
        text = cb.text()
        it = QListWidgetItem()
        if text.strip():
            for i in range(self.clip_list.count()):
                if self.clip_list.item(i).data(Qt.UserRole) == text:
                    self.drop_clip_row(i)
                    break
            kind, title, sub = classify_clip(text)
            it.setData(Qt.UserRole, text)
            it.setData(KIND_ROLE, kind)
            it.setData(TITLE_ROLE, title)
            it.setData(SUB_ROLE, sub)
            it.setData(FIND_ROLE, (text + " " + CLIP_KINDS[kind][2]).lower())
        elif cb.mimeData().hasImage():
            img = cb.image()
            if img.isNull():
                return
            top = self.clip_list.item(0)
            if top is not None and top.data(IMG_ROLE) in self.clip_images \
                    and self.clip_images[top.data(IMG_ROLE)] == img:
                return
            self.img_seq += 1
            self.clip_images[self.img_seq] = img
            thumb = QPixmap.fromImage(img).scaled(152, 136, Qt.KeepAspectRatioByExpanding,
                                                  Qt.SmoothTransformation)
            thumb = thumb.copy((thumb.width() - 152) // 2, (thumb.height() - 136) // 2, 152, 136)
            size = f"{img.width()}×{img.height()}"
            it.setData(IMG_ROLE, self.img_seq)
            it.setData(KIND_ROLE, "image")
            it.setData(THUMB_ROLE, thumb)
            it.setData(TITLE_ROLE, "Изображение")
            it.setData(SUB_ROLE, size)
            it.setData(FIND_ROLE, f"изображение картинка фото image {size}")
        else:
            return
        it.setData(TIME_ROLE, time.time())
        self.clip_list.insertItem(0, it)
        imgs = [i for i in range(self.clip_list.count())
                if self.clip_list.item(i).data(IMG_ROLE)]
        for i in reversed(imgs[10:]):  # храним не больше 10 картинок
            self.drop_clip_row(i)
        while self.clip_list.count() > 50:
            self.drop_clip_row(self.clip_list.count() - 1)
        self.apply_clip_filter()

    def drop_clip_row(self, row):
        it = self.clip_list.takeItem(row)
        if it is not None and it.data(IMG_ROLE):
            self.clip_images.pop(it.data(IMG_ROLE), None)

    def apply_clip_filter(self, *_):
        q = self.clip_search.text().strip().lower()
        shown = 0
        for i in range(self.clip_list.count()):
            it = self.clip_list.item(i)
            ok = not q or q in (it.data(FIND_ROLE) or "")
            it.setHidden(not ok)
            shown += ok
        if shown:
            self.clip_list.hint = ""
        elif self.clip_list.count():
            self.clip_list.hint = "Ничего не найдено"
        else:
            self.clip_list.hint = "Буфер пуст\nСкопируй что-нибудь, и оно появится здесь"
        self.clip_list.viewport().update()

    def remove_clip(self, item):
        self.drop_clip_row(self.clip_list.row(item))
        self.apply_clip_filter()

    def clear_clips(self):
        while self.clip_list.count():
            self.drop_clip_row(0)
        self.apply_clip_filter()

    def copy_first_clip(self):
        for i in range(self.clip_list.count()):
            if not self.clip_list.item(i).isHidden():
                self.restore_clip(self.clip_list.item(i))
                return

    def restore_clip(self, item):
        self._own_clip = True
        iid = item.data(IMG_ROLE)
        if iid and iid in self.clip_images:
            QApplication.clipboard().setImage(self.clip_images[iid])
        elif item.data(Qt.UserRole):
            QApplication.clipboard().setText(item.data(Qt.UserRole))
        item.setData(COPIED_ROLE, time.time())
        self.clip_list.viewport().update()
        QTimer.singleShot(1500, self.clip_list.viewport().update)
        QTimer.singleShot(300, lambda: setattr(self, "_own_clip", False))

    # ---------- таймер ----------
    def toggle_timer(self):
        if self.timer_running:
            self.timer_running = False
            self.btn_timer.setText("Старт")
            self.remaining = 0
        else:
            self.remaining = self.spin.value() * 60
            self.timer_running = True
            self.btn_timer.setText("Стоп")
        self.refresh_timer_label()
        self.update_pill()

    def refresh_timer_label(self):
        m, s = divmod(max(self.remaining, 0), 60)
        self.timer_label.setText(f"{m:02d}:{s:02d}")

    def tick(self):
        if self.timer_running:
            self.remaining -= 1
            if self.remaining <= 0:
                self.timer_running = False
                self.btn_timer.setText("Старт")
                QApplication.beep()
                self.flash("Таймер: готово!", 8)
        if self.recorder.error:
            self.flash("⚠ Запись: " + self.recorder.error[:40], 8)
            self.recorder.error = None
            self.refresh_rec_icon()
        self.refresh_timer_label()
        self.scan_downloads()
        if self.expanded:
            self.sync_volume()
        if self.expanded:
            self.desk_state.setText("сейчас: рабочий стол" if self.desktop_now
                                    else "сейчас: окно программы")
        self.update_pill()
        self.autohide_check()

    # ---------- заметка ----------
    def save_note(self):
        try:
            with open(NOTE_FILE, "w", encoding="utf-8") as f:
                f.write(self.note.toPlainText())
        except OSError:
            pass


def install_crash_log():
    """Пишет в ~/.island_log.txt Python-ошибки и аварийный дамп при падении Qt/DLL."""
    import traceback

    def hook(t, v, tb):
        log("UNCAUGHT " + "".join(traceback.format_exception(t, v, tb)))

    sys.excepthook = hook
    threading.excepthook = lambda a: hook(a.exc_type, a.exc_value, a.exc_traceback)
    try:
        import faulthandler
        global _fault_file
        _fault_file = open(LOG_FILE, "a", buffering=1, encoding="utf-8")
        faulthandler.enable(_fault_file)
    except Exception:
        pass


def main():
    install_crash_log()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # закрытие диалога не должно завершать остров
    # один экземпляр: после обновления старый может ещё закрываться, поэтому ждём до 8 с
    app.lock = QLockFile(os.path.join(tempfile.gettempdir(), "MiniIsland.lock"))
    if not app.lock.tryLock(8000):
        log("another instance is running, exit", once=True)
        sys.exit(0)
    w = Island()
    w.show()
    if sys.platform == "win32":  # Alt+Space -> командная строка
        try:
            import ctypes
            if ctypes.windll.user32.RegisterHotKey(None, 1, 0x0001, 0x20):
                app.hk = HotkeyFilter(w.act_cmd)
                app.installNativeEventFilter(app.hk)
        except Exception:
            pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

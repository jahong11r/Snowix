# -*- coding: utf-8 -*-
"""
❄ Yangi yil qori — realistik qor simulyatsiyasi (Windows)

  * Mayda, shakli notekis qor zarralari (uzoq/yaqin qatlamlar, shamol).
  * Qor yerda, ochiq oynalar tepasida va ish stoli ikonkalari ustida to'planadi.
    Ikonkadagi qor ikonka shakliga moslashadi.
  * Oyna yoki ikonka siljitilsa, ustidagi qor sirpanib tushadi va pastdagi qorga
    sakramasdan qo'shiladi.
  * Chap tugma: qorni sudrab sharcha yasash, ko'tarish, otish.
  * Sharcha qattiq urilsa bo'laklarga ajraladi. 3 ta sharcha = qorbobo.
  * O'ng tugma: qorbobo, sharcha yoki qor uyumini parchalaydi.
  * Tepada realistik Yangi yil chiroqlari.

Ishga tushirish:  python qor.py
Xato yoki ma'lumot:  foydalanuvchi papkasidagi qor_xato.txt va qor_log.txt
"""
import ctypes
import math
import os
import random
import sys
import tkinter as tk

KEY = "#010203"          # shaffof qilinadigan rang
WHITE = "#ffffff"
EDGE = "#b7d1ec"
PILE_BODY = "#e4eef9"
GRAVITY = 0.6
MAX_BALL = 56
GAIN = 4.2               # qor parchasi maydoni -> qatlam maydoni
BALL_GAIN = 4.0          # sharcha maydoni = olingan qor maydoni * BALL_GAIN
MAX_CHUNKS = 420
APP_NAME = "YangiYilQori"
FLAKE_FILL = ["#c3d4e7", "#dae7f4", "#eef5fb", "#ffffff"]
BULBS = [("#ff2a2a", "#3d0c0c"), ("#ffb02e", "#3d2a0c"), ("#3dff6e", "#0c3d1a"),
         ("#38b6ff", "#0c2a3d"), ("#ff5fd2", "#3d0c31"), ("#ffe94a", "#3d390c")]
SKIP_CLASSES = ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                "Windows.UI.Core.CoreWindow", "NotifyIconOverflowWindow")

_errs = 0
_logs = 0


def _write(name, text):
    try:
        p = os.path.join(os.path.expanduser("~"), name)
        with open(p, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass


def log_error():
    global _errs
    _errs += 1
    if _errs <= 5:
        import traceback
        _write("qor_xato.txt", traceback.format_exc())


def log_info(msg):
    global _logs
    _logs += 1
    if _logs <= 25:
        _write("qor_log.txt", msg)


def blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# =====================================================================
#  Windows bilan ishlash
# =====================================================================
def dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                ("r", ctypes.c_long), ("b", ctypes.c_long)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32)]


def cursor_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def button_down(vk):
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


def work_area():
    try:
        r = RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(r), 0)
        return r.l, r.t, r.r, r.b
    except Exception:
        return None


def autostart_get():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Run")
        winreg.QueryValueEx(k, APP_NAME)
        return True
    except Exception:
        return False


def autostart_set(on):
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Run",
                           0, winreg.KEY_SET_VALUE)
        if on:
            if getattr(sys, "frozen", False):
                cmd = '"%s"' % sys.executable
            else:
                cmd = '"%s" "%s"' % (sys.executable, os.path.abspath(sys.argv[0]))
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except FileNotFoundError:
                pass
    except Exception:
        pass


_api_ready = False


def setup_api():
    """ctypes funksiyalari uchun to'g'ri turlarni o'rnatadi (64-bit uchun muhim)."""
    global _api_ready
    from ctypes import wintypes
    u = ctypes.windll.user32
    d = ctypes.windll.dwmapi
    if _api_ready:
        return u, d
    u.IsWindowVisible.argtypes = [wintypes.HWND]
    u.IsIconic.argtypes = [wintypes.HWND]
    u.IsZoomed.argtypes = [wintypes.HWND]
    u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    u.GetWindowLongW.restype = ctypes.c_long
    u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    u.SetWindowLongW.restype = ctypes.c_long
    u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
    u.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
    u.GetAncestor.restype = wintypes.HWND
    u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    u.FindWindowW.restype = wintypes.HWND
    u.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR,
                                wintypes.LPCWSTR]
    u.FindWindowExW.restype = wintypes.HWND
    u.SendMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_size_t,
                               ctypes.c_ssize_t]
    u.SendMessageW.restype = ctypes.c_ssize_t
    u.ClientToScreen.argtypes = [wintypes.HWND, ctypes.c_void_p]
    u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
    u.GetDC.argtypes = [wintypes.HWND]
    u.GetDC.restype = ctypes.c_void_p
    u.ReleaseDC.argtypes = [wintypes.HWND, ctypes.c_void_p]
    d.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                        ctypes.c_void_p, wintypes.DWORD]
    g = ctypes.windll.gdi32
    g.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
    g.CreateCompatibleDC.restype = ctypes.c_void_p
    g.CreateCompatibleBitmap.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    g.CreateCompatibleBitmap.restype = ctypes.c_void_p
    g.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    g.SelectObject.restype = ctypes.c_void_p
    g.BitBlt.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                         wintypes.DWORD]
    g.GetDIBits.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
                            ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
                            ctypes.c_uint]
    g.DeleteObject.argtypes = [ctypes.c_void_p]
    g.DeleteDC.argtypes = [ctypes.c_void_p]
    _api_ready = True
    return u, d


def grab_screen(x, y, w, h):
    """Ekranning (x,y,w,h) qismini BGRA baytlar sifatida oladi (qor oynasisiz)."""
    u = ctypes.windll.user32
    g = ctypes.windll.gdi32
    hdc = u.GetDC(None)
    if not hdc:
        return None
    try:
        mdc = g.CreateCompatibleDC(hdc)
        bmp = g.CreateCompatibleBitmap(hdc, w, h)
        old = g.SelectObject(mdc, bmp)
        ok = g.BitBlt(mdc, 0, 0, w, h, hdc, x, y, 0x00CC0020)   # SRCCOPY
        bi = BITMAPINFOHEADER()
        bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bi.biWidth, bi.biHeight = w, -h
        bi.biPlanes, bi.biBitCount = 1, 32
        buf = ctypes.create_string_buffer(w * h * 4)
        g.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
        g.SelectObject(mdc, old)
        g.DeleteObject(bmp)
        g.DeleteDC(mdc)
        return buf.raw if ok else None
    finally:
        u.ReleaseDC(None, hdc)


def compute_profile(buf, w, h_total, margin, thresh=42):
    """Ikonka siluetining yuqori chegarasi.
    buf — BGRA baytlar (yuqoridan pastga), tepada `margin` qator ikonkadan tashqarida.
    Har bir ustunda keskin rang sakrashi (ikonka cheti) qidiriladi; fon gradienti
    sekin o'zgargani uchun xalaqit bermaydi.
    Qaytaradi: har bir ustun uchun ikonka tepasidan masofa (px) yoki None."""
    rows = h_total - margin
    limit = int(rows * 0.75)
    prof = []
    for x in range(w):
        found = None
        streak = 0
        for r in range(limit):
            i = ((margin + r) * w + x) * 4
            j = ((margin + r - 2) * w + x) * 4
            d = abs(buf[i] - buf[j]) + abs(buf[i + 1] - buf[j + 1]) + abs(buf[i + 2] - buf[j + 2])
            if d > thresh:
                streak += 1
                if streak >= 2:
                    found = max(0, r - 1)
                    break
            else:
                streak = 0
        prof.append(found)
    out = []
    for x in range(w):
        win = [prof[j] for j in range(max(0, x - 2), min(w, x + 3))]
        vals = sorted(v for v in win if v is not None)
        if len(vals) * 2 <= len(win):
            out.append(None)
        else:
            out.append(vals[len(vals) // 2])
    return out


def profile_ok(prof):
    solid = [p for p in prof if p is not None]
    if len(solid) < 0.25 * len(prof):
        return False
    flat = sum(1 for p in solid if p <= 1)
    if flat >= 0.85 * len(solid) and len(solid) > 0.9 * len(prof):
        return False          # tanlangan (ko'k fon) ikonka — to'g'ri chegara emas
    return True


class WinScanner:
    """Ochiq oynalarning joylashuvini (z-tartibda, tepadan pastga) o'qiydi."""

    def __init__(self, own_hwnd, S):
        self.own = own_hwnd
        self.S = S
        self.ok = True
        try:
            self.u, self.dwm = setup_api()
        except Exception:
            self.ok = False

    def scan(self, W, H, ground):
        if not self.ok:
            return []
        from ctypes import wintypes
        u, dwm, S = self.u, self.dwm, self.S
        res = []
        buf = ctypes.create_unicode_buffer(80)
        own = int(self.own) if self.own else -1

        def cb(hwnd, lp):
            try:
                if hwnd is None or int(hwnd) == own:
                    return True
                if not u.IsWindowVisible(hwnd) or u.IsIconic(hwnd):
                    return True
                ex = u.GetWindowLongW(hwnd, -20)
                if ex & 0x80 or ex & 0x08000000:      # TOOLWINDOW | NOACTIVATE
                    return True
                cloaked = wintypes.DWORD(0)
                dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4)
                if cloaked.value:
                    return True
                u.GetClassNameW(hwnd, buf, 80)
                if buf.value in SKIP_CLASSES:
                    return True
                if u.GetWindowTextLengthW(hwnd) == 0:
                    return True
                r = RECT()
                if dwm.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r),
                                             ctypes.sizeof(r)) != 0:
                    u.GetWindowRect(hwnd, ctypes.byref(r))
                w, h = r.r - r.l, r.b - r.t
                if w < 100 * S or h < 50 * S:
                    return True
                ok = (r.t >= 8 * S and r.t < ground - 40 * S and not u.IsZoomed(hwnd)
                      and r.r > 0 and r.l < W)
                res.append((int(hwnd), r.l, r.t, r.r, r.b, ok))
            except Exception:
                pass
            return True

        try:
            proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb)
            u.EnumWindows(proc, 0)
        except Exception:
            return []
        return res


class DesktopIcons:
    """Ish stoli ikonkalari joylashuvi va siluetini o'qiydi."""

    def __init__(self, S, W, H):
        self.S, self.W, self.H = S, W, H
        self.ok = False
        self.lv = None
        self.why = ""
        self.cache = {}
        self.nq = 0
        self.logged = False
        try:
            self.u, _ = setup_api()
            from ctypes import wintypes
            k = ctypes.windll.kernel32
            k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            k.OpenProcess.restype = ctypes.c_void_p
            k.VirtualAllocEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
            k.VirtualAllocEx.restype = ctypes.c_void_p
            k.WriteProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                             ctypes.c_void_p, ctypes.c_size_t,
                                             ctypes.c_void_p]
            k.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                            ctypes.c_void_p, ctypes.c_size_t,
                                            ctypes.c_void_p]
            self.k = k
            self.find()
        except Exception as e:
            self.ok = False
            self.why = "boshlash xatosi: %r" % (e,)
        if not self.ok:
            log_info("Ikonkalar: o'qib bo'lmadi (%s)" % self.why)

    def find(self):
        u = self.u
        defview = None
        prog = u.FindWindowW("Progman", None)
        if prog:
            defview = u.FindWindowExW(prog, None, "SHELLDLL_DefView", None)
        if not defview:
            ww = None
            while True:
                ww = u.FindWindowExW(None, ww, "WorkerW", None)
                if not ww:
                    break
                defview = u.FindWindowExW(ww, None, "SHELLDLL_DefView", None)
                if defview:
                    break
        if not defview:
            self.why = "SHELLDLL_DefView topilmadi"
            return
        lv = u.FindWindowExW(defview, None, "SysListView32", None)
        if not lv:
            self.why = "SysListView32 topilmadi"
            return
        pid = ctypes.c_ulong(0)
        u.GetWindowThreadProcessId(lv, ctypes.byref(pid))
        proc = self.k.OpenProcess(0x38, False, pid.value)   # VM_OPERATION|READ|WRITE
        if not proc:
            self.why = "explorer jarayoniga kirib bo'lmadi"
            return
        remote = self.k.VirtualAllocEx(proc, None, 64, 0x3000, 0x04)
        if not remote:
            self.why = "explorer xotirasini ajratib bo'lmadi"
            return
        self.lv, self.proc, self.remote = lv, proc, remote
        self.ok = True

    def capture(self, l, t, r, b):
        S = self.S
        m = 4
        w, h = int(r - l), int(b - t)
        if w < 8 or h < 8 or w > 400 or h > 400:
            return None
        if l < 0 or t - m < 0 or r > self.W or b > self.H:
            return None
        buf = grab_screen(int(l), int(t - m), w, h + m)
        if buf is None:
            return None
        prof = compute_profile(buf, w, h + m, m)
        return prof if profile_ok(prof) else None

    def query(self, covered, mouse):
        """[(indeks, l, t, r, b, profil)] — ikonka rasmi to'rtburchagi va silueti."""
        if not self.ok:
            self.nq += 1
            if self.nq % 25 == 1:
                try:
                    self.find()
                except Exception:
                    pass
            if not self.ok:
                return []
        u, k, S = self.u, self.k, self.S
        mx, my, down = mouse
        try:
            if not u.IsWindowVisible(self.lv):
                return []
            count = u.SendMessageW(self.lv, 0x1004, 0, 0)       # LVM_GETITEMCOUNT
            if count <= 0 or count > 300:
                return []
            org = POINT(0, 0)
            u.ClientToScreen(self.lv, ctypes.byref(org))
            out = []
            captures = 0
            self.nq += 1
            for i in range(count):
                r = RECT(1, 0, 0, 0)                            # LVIR_ICON
                k.WriteProcessMemory(self.proc, self.remote, ctypes.byref(r), 16, None)
                if not u.SendMessageW(self.lv, 0x100E, i, self.remote):
                    continue
                k.ReadProcessMemory(self.proc, self.remote, ctypes.byref(r), 16, None)
                l, t = org.x + r.l, org.y + r.t
                rr, bb = org.x + r.r, org.y + r.b
                if rr - l < 10 * S or rr < 0 or l > self.W:
                    continue
                key = (l, t, rr, bb)
                ent = self.cache.get(i)
                if ent is None or ent[0] != key:
                    ent = [key, None, 0, self.nq]
                    self.cache[i] = ent
                want = ent[1] is None and ent[2] < 4 and self.nq >= ent[3]
                if want and captures < 3 and not down:
                    pts = ((l + 2, t + 2), (rr - 2, t + 2), ((l + rr) / 2, (t + bb) / 2),
                           (l + 2, bb - 2), (rr - 2, bb - 2))
                    near = (l - 12 * S <= mx <= rr + 12 * S and t - 12 * S <= my <= bb + 12 * S)
                    state = u.SendMessageW(self.lv, 0x102C, i, 0x000B)   # SELECTED|FOCUSED|DROP
                    if not near and not state and not any(covered(x, y) for x, y in pts):
                        captures += 1
                        prof = self.capture(l, t, rr, bb)
                        if prof is not None:
                            ent[1] = prof
                        else:
                            ent[2] += 1
                            ent[3] = self.nq + 25
                out.append((i, l, t, rr, bb, ent[1]))
            if not self.logged and out:
                self.logged = True
                log_info("Ikonkalar topildi: %d ta" % len(out))
            return out
        except Exception:
            self.ok = False
            self.why = "so'rov xatosi"
            log_error()
            return []


# =====================================================================
#  O'yin dunyosi (tkinter'siz — faqat hisob-kitob)
# =====================================================================
def rot(pts, ang, cx, cy, k=1.0):
    ca, sa = math.cos(ang), math.sin(ang)
    out = []
    for px, py in pts:
        out.append(cx + (px * ca - py * sa) * k)
        out.append(cy + (px * sa + py * ca) * k)
    return out


def rough_shape(n_lo, n_hi, lo, hi, stretch=1.0):
    n = random.randint(n_lo, n_hi)
    pts = []
    for k in range(n):
        a = 6.283 * k / n + random.uniform(-0.45, 0.45)
        rr = random.uniform(lo, hi)
        pts.append((math.cos(a) * rr, math.sin(a) * rr * stretch))
    return pts


class Flake:
    __slots__ = ("x", "y", "z", "tier", "r", "v", "ph", "fr", "wob", "ang", "spin",
                 "shape", "item")

    def __init__(self, W, H, S, anywhere=False):
        self.item = None
        self.respawn(W, H, S, anywhere)

    def respawn(self, W, H, S, anywhere=False):
        z = random.random() ** 1.6          # ko'pchilik — mayda va uzoq
        self.z = z
        self.tier = int(z * 3.999)
        self.r = (0.55 + 1.9 * z ** 1.3) * S
        self.v = (1.0 + 2.4 * z) * S * random.uniform(0.9, 1.1)
        self.fr = random.uniform(0.02, 0.05)
        self.wob = random.uniform(0.25, 0.8)
        self.ang = random.uniform(0, 6.28)
        self.spin = random.uniform(-0.06, 0.06)
        self.shape = rough_shape(4, 6, 0.6, 1.25, 1.0 + z * random.uniform(0.2, 1.2))
        self.x = random.uniform(0, W)
        self.y = random.uniform(0, H) if anywhere else random.uniform(-0.25 * H, -4)
        self.ph = random.uniform(0, 6.28)


class Chunk:
    """Qor bo'lagi (sharcha parchasi, to'kilgan qor yoki chang)."""
    __slots__ = ("x", "y", "vx", "vy", "r", "dust", "item", "shape")

    def __init__(self, x, y, vx, vy, r, dust):
        self.x, self.y, self.vx, self.vy, self.r = x, y, vx, vy, r
        self.dust = dust
        self.item = None
        self.shape = None if dust else rough_shape(5, 7, 0.65, 1.2)


class Part:
    """Qorbobo qismlari (qalpoq, burun, shox, ko'mir, sharf)."""

    def __init__(self, kind, x, y, vx, vy, s, w=0.0):
        self.kind, self.x, self.y, self.vx, self.vy = kind, x, y, vx, vy
        self.s, self.w = s, w
        self.ang = random.uniform(-0.5, 0.5)
        self.vang = random.uniform(-0.35, 0.35)
        self.rest = 0
        self.k = 1.0
        self.ext = {"hat": 0.45, "nose": 0.1, "stick": 0.08, "scarf": 0.1,
                    "coal": 1.0}[kind] * (w if kind == "coal" else s)


class Pile:
    """Bir sirtda (yer, oyna tepasi, ikonka) to'planadigan qor qatlami."""
    WEIGHTS = [6 - abs(d) for d in range(-5, 6)]

    def __init__(self, x0, x1, y, col, maxh, slope, open_edges, S, noise_k=1.0):
        self.col, self.maxh, self.slope = col, maxh, slope
        self.open, self.S, self.noise_k = open_edges, S, noise_k
        self.active = True
        self.h = []
        self.noise = []
        self.vis = None
        self.base = None          # ikonka silueti (har ustun uchun tepadan masofa yoki None)
        self.prof_id = -1
        self.item = self.item2 = None
        self.shown = True
        self.dirty = True
        self.x0 = self.x1 = self.y = None
        self.move(x0, x1, y)

    def move(self, x0, x1, y):
        n = max(3, int((x1 - x0) // self.col) + 1)
        if n > len(self.h):
            add = n - len(self.h)
            self.h += [0.0] * add
            for _ in range(add):
                prev = self.noise[-1] if self.noise else 0.0
                self.noise.append(0.55 * prev + 0.45 * random.uniform(-1, 1) * 1.6 * self.S)
        elif n < len(self.h):
            del self.h[n:]
            del self.noise[n:]
        if (x0, x1, y) != (self.x0, self.x1, self.y):
            self.dirty = True
        self.x0, self.x1, self.y = x0, x1, y

    def set_profile(self, profile, wpx):
        S = self.S
        if profile is None:        # standart: yumaloq ikonka shakli
            hw = max(1.0, wpx / 2.0)
            profile = []
            for k in range(int(wpx) + 1):
                u = max(-1.0, min(1.0, (k + 0.5 - hw) / hw))
                profile.append(3 * S + (1 - math.sqrt(max(0.0, 1 - u * u))) * hw * 0.45)
        base = []
        for i in range(len(self.h)):
            k = min(len(profile) - 1, int(i * self.col + self.col / 2.0))
            p = profile[k]
            base.append(None if p is None else float(p))
        self.base = base
        self.dirty = True

    def solid(self, i):
        return self.base is None or self.base[i] is not None

    def surf_y(self, i):
        if self.base is None or self.base[i] is None:
            return self.y
        return self.y + self.base[i]

    def top_at(self, i):
        return self.surf_y(i) - self.h[i]

    def idx(self, x):
        i = int((x - self.x0) // self.col)
        if i < 0:
            return 0
        if i >= len(self.h):
            return len(self.h) - 1
        return i

    def height_at(self, x):
        return self.h[self.idx(x)]

    def top_y_at(self, x):
        return self.top_at(self.idx(x))

    def area(self):
        return sum(self.h) * self.col

    def add(self, x, r):
        total = math.pi * r * r * GAIN / self.col
        sw = float(sum(self.WEIGHTS))
        i = self.idx(x)
        h = self.h
        n = len(h)
        for k, w in enumerate(self.WEIGHTS):
            j = i + k - 5
            if 0 <= j < n and self.solid(j):
                v = h[j] + total * w / sw
                h[j] = v if v < self.maxh else self.maxh
        self.dirty = True

    def take(self, x, r, want_area):
        i = self.idx(x)
        k = max(3, int(r / self.col) + 2)
        per = want_area / ((2 * k + 1) * self.col)
        got = 0.0
        for j in range(i - k, i + k + 1):
            if 0 <= j < len(self.h):
                t = min(self.h[j], per)
                self.h[j] -= t
                got += t * self.col
        if got > 0:
            self.dirty = True
        return got

    def relax(self):
        h = self.h
        n = len(h)
        lim = self.slope
        base = self.base
        moved = False

        def e(i):
            b = base[i] if base is not None and base[i] is not None else 0.0
            return h[i] - b

        for i in range(n - 1):
            si = self.solid(i)
            sj = self.solid(i + 1)
            if si and sj:
                d = e(i) - e(i + 1)
                if d > lim and h[i] > 0:
                    m = min((d - lim) * 0.35, h[i])
                    h[i] -= m
                    h[i + 1] += m
                    moved = True
                elif d < -lim and h[i + 1] > 0:
                    m = min((-d - lim) * 0.35, h[i + 1])
                    h[i] += m
                    h[i + 1] -= m
                    moved = True
                if h[i + 1] > self.maxh:
                    h[i + 1] = self.maxh
            elif si and h[i] > 0:          # qo'shni yo'q: qor sirpanib to'kiladi
                h[i] *= 0.8
                moved = True
            elif sj and h[i + 1] > 0:
                h[i + 1] *= 0.8
                moved = True
        if self.open and base is None:
            if h[0] > lim:
                h[0] -= (h[0] - lim) * 0.3
                moved = True
            if h[-1] > lim:
                h[-1] -= (h[-1] - lim) * 0.3
                moved = True
        if moved:
            self.dirty = True

    def _tops(self):
        """Har ustun uchun (x, qor yuzasi y, tayanch y)."""
        y, col, S = self.y, self.col, self.S
        h, nz, vis, base = self.h, self.noise, self.vis, self.base
        n = len(h)
        # tayanch chiziq: silueta bo'sh ustunlarda qo'shnidan olinadi
        bb = []
        last = None
        if base is not None:
            for b in base:
                if b is not None:
                    last = b
                bb.append(last)
            nxt = None
            for i in range(n - 1, -1, -1):
                if bb[i] is None:
                    bb[i] = nxt if nxt is not None else 0.0
                else:
                    nxt = bb[i]
        out = []
        x = self.x0
        for i in range(n):
            by = y + (bb[i] if base is not None else 0.0)
            if (vis is not None and not vis[i]) or (base is not None and base[i] is None):
                v = 0.0
            else:
                v = h[i] + nz[i] * self.noise_k * min(1.0, h[i] / (5 * S))
            out.append((x, by - v, by))
            x += col
        return out

    def points(self):
        y, col, S = self.y, self.col, self.S
        t = self._tops()
        if self.base is not None:
            return ([c for (x, ty, by) in t for c in (x, ty)]
                    + [c for (x, ty, by) in reversed(t) for c in (x, by)])
        pts = []
        if self.open:
            h0 = y - t[0][1]
            pts += [self.x0 - 2 * col, y + 5 * S, self.x0 - 2 * col, y - h0 * 0.25,
                    self.x0 - col, y - h0 * 0.6]
        else:
            pts += [self.x0, y + 3]
        for (x, ty, by) in t:
            pts += [x, ty]
        last = t[-1][0]
        if self.open:
            hl = y - t[-1][1]
            pts += [last + col, y - hl * 0.6, last + 2 * col, y - hl * 0.25,
                    last + 2 * col, y + 5 * S]
        else:
            pts += [last, y + 3]
        return pts

    def crust(self):
        """Qorning ustki oq qatlami (hajm ko'rinishi uchun)."""
        S = self.S
        t = self._tops()
        top = [c for (x, ty, by) in t for c in (x, ty)]
        low = []
        for (x, ty, by) in reversed(t):
            low += [x, ty + min((by - ty) * 0.55, 2.6 * S) + 0.5]
        return top + low

    def clear(self):
        self.h = [0.0] * len(self.h)
        self.dirty = True


class Ball:
    __slots__ = ("x", "y", "r", "vx", "vy", "state", "under", "over")

    def __init__(self, x, y, r):
        self.x, self.y, self.r = x, y, r
        self.vx = self.vy = 0.0
        self.state = "free"      # free | rest | held | roll
        self.under = None
        self.over = None


class Snowman:
    def __init__(self, x, radii):
        self.x = x
        self.radii = radii
        self.age = 0
        self.dying = False
        self.gone = set()


class World:
    def __init__(self, W, H, ground, S):
        self.W, self.H, self.ground, self.S = W, H, ground, S
        self.col = max(2, int(round(4 * S)))
        self.slope = 1.4 * S
        self.ground_pile = Pile(0, W, ground, self.col, 22 * S, self.slope, False, S)
        self.surfaces = {}
        self.surf_list = []
        self.n_flakes = 260
        self.snowing = True
        self.wind = 0.0
        self.flakes = [Flake(W, H, S, True) for _ in range(self.n_flakes)]
        self.chunks = []
        self.parts = []
        self.events = []
        self.dead = []           # o'chirilishi kerak bo'lgan canvas id lari
        self.balls = []
        self.snowmen = []
        self.held = None
        self.grab = (0.0, 0.0)
        self.roll_x = 0.0
        self.prev_down = False
        self.prev_rdown = False
        self.hist = []
        self.t = 0

    # ---------------- asosiy qadam ----------------
    def step(self, mx, my, down, rdown=False):
        self.t += 1
        t = self.t
        self.wind = 0.5 * math.sin(t * 0.004) + 0.35 * math.sin(t * 0.0113 + 1.7)
        self.update_flakes()
        self.update_mouse(mx, my, down, rdown)
        self.update_balls()
        self.update_chunks()
        self.update_parts()
        for sm in self.snowmen:
            sm.age += 1
        for ev in list(self.events):
            if t >= ev[0]:
                self.events.remove(ev)
                ev[1]()
        if t % 2 == 0:
            gp = self.ground_pile
            gp.relax()
            gp.h = [v * 0.9991 for v in gp.h]     # juda sekin erish: qor haddan oshmaydi
            for s in self.surf_list:
                if max(s.h) > 0.05:
                    s.relax()
        if t % 15 == 0:      # to'lib ketgan qor ba'zan o'zi sirpanib tushadi
            for s in self.surf_list:
                if s.maxh >= 12 * self.S and max(s.h) >= 0.85 * s.maxh \
                        and random.random() < 0.12:
                    self.shed(s, 0.25, maxn=5)

    def clear(self):
        self.ground_pile.clear()
        for s in self.surfaces.values():
            s.clear()
        for c in self.chunks:
            if c.item is not None:
                self.dead.append(c.item)
        self.chunks.clear()
        self.parts.clear()
        self.events.clear()
        self.balls.clear()
        self.snowmen.clear()
        self.held = None

    # ---------------- qor parchalari ----------------
    def update_flakes(self):
        S, W, H = self.S, self.W, self.H
        gp = self.ground_pile
        surfs = self.surf_list
        target = self.n_flakes if self.snowing else 0
        extra = len(self.flakes) - target
        alive = []
        wind = self.wind
        t = self.t
        for f in self.flakes:
            oy = f.y
            f.y += f.v
            f.x += (wind * (0.4 + 0.8 * f.z) + math.sin(f.ph + t * f.fr) * f.wob) * S
            f.ang += f.spin
            if f.x < 0:
                f.x += W
            elif f.x >= W:
                f.x -= W
            landed = None
            besttop = None
            for s in surfs:
                if s.x0 <= f.x <= s.x1:
                    i = s.idx(f.x)
                    if (s.vis is not None and not s.vis[i]) or not s.solid(i):
                        continue
                    top = s.top_at(i)
                    if oy < top <= f.y and (besttop is None or top < besttop):
                        landed, besttop = s, top
            if landed is None and f.y >= gp.y - gp.height_at(f.x):
                landed = gp
            if landed is not None:
                landed.add(f.x, f.r)
                if extra > 0:
                    extra -= 1
                    if f.item is not None:
                        self.dead.append(f.item)
                    continue
                f.respawn(W, H, S)
            alive.append(f)
        while len(alive) < target:
            alive.append(Flake(W, H, S, False))
        if len(alive) > target and target > 0:
            for f in alive[target:]:
                if f.item is not None:
                    self.dead.append(f.item)
            alive = alive[:target]
        self.flakes = alive

    # ---------------- bo'laklar (chunk) ----------------
    def spawn_chunk(self, x, y, vx, vy, r, dust=False):
        x = min(max(x, 1.0), self.W - 1.0)
        if len(self.chunks) >= MAX_CHUNKS:
            self.ground_pile.add(x, r)
            return
        self.chunks.append(Chunk(x, y, vx, vy, r, dust))

    def update_chunks(self):
        S, W = self.S, self.W
        gp = self.ground_pile
        alive = []
        for c in self.chunks:
            if c.dust:
                c.vy += 0.18 * S
                c.vx *= 0.96
                c.vy *= 0.97
            else:
                c.vy += GRAVITY * S * 0.9
                c.vx *= 0.99
            c.x += c.vx
            c.y += c.vy
            if c.x < 0:
                c.x, c.vx = 0.0, abs(c.vx) * 0.3
            elif c.x > W:
                c.x, c.vx = float(W), -abs(c.vx) * 0.3
            if c.y + c.r * 0.5 >= gp.y - gp.height_at(c.x):
                gp.add(c.x, c.r)               # sakramasdan qatlamga qo'shiladi
                if c.item is not None:
                    self.dead.append(c.item)
                continue
            alive.append(c)
        self.chunks = alive

    def sphere_burst(self, cx, cy, R, bias, vscale, ndir, gain=BALL_GAIN):
        S = self.S
        n = max(8, min(34, int(R / S * 0.7) + 8))
        a = math.pi * R * R / gain * 0.85 / n
        rc = math.sqrt(a / (math.pi * GAIN))
        for _ in range(n):
            ang = random.uniform(0, 6.283)
            rad = R * math.sqrt(random.random()) * 0.8
            px, py = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad
            if ndir is None:
                dx, dy = math.cos(ang), math.sin(ang)
            else:
                dx = ndir[0] + random.uniform(-1, 1) * 1.1
                dy = ndir[1] + random.uniform(-1, 1) * 1.1
                ln = math.hypot(dx, dy) or 1.0
                dx, dy = dx / ln, dy / ln
            sp = random.uniform(0.25, 1.0) * vscale
            self.spawn_chunk(px, py, bias[0] + dx * sp,
                             bias[1] + dy * sp - random.uniform(0, 2.4) * S,
                             rc * random.uniform(0.7, 1.3))
        for _ in range(n * 2):    # mayda qor changi
            ang = random.uniform(0, 6.283)
            rad = R * math.sqrt(random.random()) * 0.9
            px, py = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad
            if ndir is None:
                dx, dy = math.cos(ang), math.sin(ang)
            else:
                dx = ndir[0] + random.uniform(-1, 1) * 1.4
                dy = ndir[1] + random.uniform(-1, 1) * 1.4
                ln = math.hypot(dx, dy) or 1.0
                dx, dy = dx / ln, dy / ln
            sp = random.uniform(0.3, 1.2) * vscale * 1.1
            self.spawn_chunk(px, py, bias[0] + dx * sp, bias[1] + dy * sp - S,
                             random.uniform(0.6, 1.3) * S, dust=True)

    def shatter_ball(self, b, normal, speed):
        S = self.S
        if b in self.balls:
            self.balls.remove(b)
        if b.under is not None:
            b.under.over = None
            b.under = None
        if b.over is not None:
            o = b.over
            o.under = None
            o.state = "free"
            b.over = None
        if self.held is b:
            self.held = None
        if normal is None:
            self.sphere_burst(b.x, b.y, b.r, (0.0, 0.0), 8 * S, None)
        else:
            nx, ny = normal
            vn = b.vx * nx + b.vy * ny
            rx, ry = b.vx - 2 * vn * nx, b.vy - 2 * vn * ny   # qaytgan tezlik
            self.sphere_burst(b.x, b.y, b.r, (rx * 0.3, ry * 0.3),
                              min(speed * 0.55, 15 * S), normal)

    def shed(self, p, frac, vx0=0.0, vy0=0.0, edge=None, maxn=10):
        """Qatlamning frac ulushini bo'laklar sifatida to'kib yuboradi."""
        S = self.S
        total = p.area()
        if total <= 1 or frac <= 0:
            return
        area = total * min(1.0, frac)
        n = max(1, min(maxn, int(area / 60) + 1))
        cols = len(p.h)
        for _ in range(n):
            if edge == "L":
                i = random.randint(0, min(cols - 1, 6))
            elif edge == "R":
                i = random.randint(max(0, cols - 7), cols - 1)
            else:
                i = random.choices(range(cols), weights=[v + 0.001 for v in p.h])[0]
            x = p.x0 + i * p.col
            got = p.take(x, 2 * p.col, area / n)
            if got < 2:
                continue
            r = math.sqrt(got / (math.pi * GAIN))
            self.spawn_chunk(x, p.top_y_at(x) - r,
                             vx0 + random.uniform(-1.5, 1.5) * S,
                             vy0 + random.uniform(-0.5, 1.0) * S, r)

    def slide_off(self, p, vx0, vy0):
        """Sirt siljiganda butun qor sirpanib tushadi va sirt tozalanadi."""
        S = self.S
        cols = len(p.h)
        g = 4
        for j in range(0, cols, g):
            area = sum(p.h[j:j + g]) * p.col
            if area >= 3:
                xc = p.x0 + (j + g / 2.0) * p.col
                pieces = int(area / (math.pi * GAIN * (5 * S) ** 2)) + 1
                r = math.sqrt(area / pieces / (math.pi * GAIN))
                ty = p.top_y_at(xc)
                for _ in range(pieces):
                    self.spawn_chunk(xc + random.uniform(-g, g) * p.col * 0.5, ty - r,
                                     vx0 + random.uniform(-1, 1) * S,
                                     vy0 + random.uniform(0, 1.2) * S, r)
            for k in range(j, min(j + g, cols)):
                p.h[k] = 0.0
        p.dirty = True

    def burst_pile(self, p, mx):
        S = self.S
        R = (55 if p is self.ground_pile else 38) * S
        j0 = p.idx(mx - R)
        j1 = p.idx(mx + R)
        j = j0
        while j <= j1:
            area = 0.0
            for jj in range(j, min(j + 3, j1 + 1)):
                x = p.x0 + jj * p.col
                dx = abs(x - mx)
                if dx > R:
                    continue
                frac = 0.45 * (1 + math.cos(math.pi * dx / R)) * 0.95
                area += p.h[jj] * frac * p.col
                p.h[jj] -= p.h[jj] * frac
            if area >= 2:
                xc = p.x0 + (j + 1) * p.col
                pieces = int(area / (math.pi * GAIN * (6 * S) ** 2)) + 1
                r = math.sqrt(area / pieces / (math.pi * GAIN))
                ty = p.top_y_at(xc)
                for _ in range(pieces):
                    self.spawn_chunk(
                        xc + random.uniform(-p.col, p.col), ty - r,
                        (xc - mx) / R * 6 * S + random.uniform(-1.5, 1.5) * S,
                        -random.uniform(2.5, 8.5) * S, r)
                for _ in range(2):
                    self.spawn_chunk(xc, ty - S,
                                     (xc - mx) / R * 5 * S + random.uniform(-2, 2) * S,
                                     -random.uniform(2, 7) * S,
                                     random.uniform(0.6, 1.2) * S, dust=True)
            j += 3
        p.dirty = True

    # ---------------- qorbobo qismlari ----------------
    def spawn_part(self, kind, x, y, vx, vy, s, w=0.0):
        if len(self.parts) < 80:
            self.parts.append(Part(kind, x, y, vx, vy, s, w))

    def update_parts(self):
        S = self.S
        gp = self.ground_pile
        alive = []
        for p in self.parts:
            p.vy += GRAVITY * S
            p.x += p.vx
            p.y += p.vy
            p.ang += p.vang
            if p.x < 0 or p.x > self.W:
                p.vx = -p.vx * 0.5
                p.x = min(max(p.x, 0.0), float(self.W))
            gy = gp.y - gp.height_at(p.x)
            if p.y + p.ext >= gy:
                p.y = gy - p.ext
                if p.vy > 3 * S:
                    p.vy = -p.vy * 0.35
                    p.vx *= 0.7
                    p.vang *= 0.6
                else:
                    p.vy = 0.0
                    p.vx *= 0.8
                    p.vang *= 0.7
                    p.rest += 1
            if p.rest > 100:
                p.k -= 0.05
                if p.k <= 0:
                    continue
            alive.append(p)
        self.parts = alive

    def snowman_circles(self, sm):
        r0, r1, r2 = sm.radii
        y0 = self.ground - r0
        y1 = y0 - (r0 + r1) * 0.82
        y2 = y1 - (r1 + r2) * 0.82
        return [(sm.x, y0, r0), (sm.x, y1, r1), (sm.x, y2, r2)]

    def destroy_snowman(self, sm, power=1.0):
        if sm.dying:
            return
        sm.dying = True
        circles = self.snowman_circles(sm)
        for idx, delay in ((2, 0), (1, 5), (0, 10)):
            self.events.append([self.t + delay,
                                lambda i=idx: self.burst_snowman_part(sm, i, circles, power)])

    def burst_snowman_part(self, sm, idx, circles, power):
        S = self.S
        cx, cy, cr = circles[idx]
        self.sphere_burst(cx, cy, cr, (0.0, 0.0), 8 * S * power, None)
        r0, r1, r2 = sm.radii
        rnd = random.uniform
        if idx == 2:
            hx, hy = circles[2][0], circles[2][1]
            self.spawn_part("hat", hx + 0.2 * r2, hy - 0.9 * r2, rnd(-3, 5) * S * power,
                            -rnd(6, 11) * S * power, r2)
            self.spawn_part("nose", hx + 0.5 * r2, hy + 0.1 * r2, rnd(2, 8) * S * power,
                            -rnd(3, 8) * S * power, r2 * 0.95)
            self.spawn_part("scarf", hx, hy + 0.82 * r2, rnd(-5, 5) * S * power,
                            -rnd(2, 6) * S * power, r2 * 1.6, max(4 * S, 0.28 * r2))
            for sx in (-0.33, 0.33):
                self.spawn_part("coal", hx + sx * r2, hy - 0.22 * r2, rnd(-6, 6) * S * power,
                                -rnd(3, 9) * S * power, 0, max(1.6 * S, 0.09 * r2))
            for k in range(-2, 3):
                self.spawn_part("coal", hx + k * 0.15 * r2, hy + 0.5 * r2,
                                rnd(-6, 6) * S * power, -rnd(2, 8) * S * power, 0,
                                max(1.3 * S, 0.045 * r2))
        elif idx == 1:
            for sign in (-1, 1):
                self.spawn_part("stick", cx + sign * r1 * 1.3, cy - r1 * 0.5,
                                sign * rnd(3, 9) * S * power, -rnd(3, 9) * S * power,
                                r1 * 1.2, max(3 * S, 0.1 * r1))
            for t in (-0.4, 0.0, 0.4):
                self.spawn_part("coal", cx, cy + t * r1, rnd(-6, 6) * S * power,
                                -rnd(2, 7) * S * power, 0, max(2 * S, 0.08 * r1))
        sm.gone.add(idx)
        if len(sm.gone) >= 3 and sm in self.snowmen:
            self.snowmen.remove(sm)

    # ---------------- sichqoncha ----------------
    def hit_test(self, mx, my):
        S = self.S
        for b in reversed(self.balls):
            if b.state in ("rest", "free") and b.over is None:
                if (mx - b.x) ** 2 + (my - b.y) ** 2 <= (b.r + 3 * S) ** 2:
                    return ("ball", b)
        for sm in reversed(self.snowmen):
            if sm.dying:
                continue
            for cx, cy, cr in self.snowman_circles(sm):
                if (mx - cx) ** 2 + (my - cy) ** 2 <= (cr + 3 * S) ** 2:
                    return ("snowman", sm)
        for s in self.surf_list:
            if s.x0 <= mx <= s.x1:
                i = s.idx(mx)
                if (s.vis is not None and not s.vis[i]) or not s.solid(i):
                    continue
                if s.h[i] >= 2.5 * S and s.top_at(i) - 4 * S <= my <= s.surf_y(i) + 2 * S:
                    return ("pile", s)
        gp = self.ground_pile
        if 0 <= mx < self.W and my <= gp.y:
            h = gp.height_at(mx)
            if h >= 3 * S and my >= gp.y - h - 4 * S:
                return ("pile", gp)
        return None

    def update_mouse(self, mx, my, down, rdown):
        S = self.S
        pressed = down and not self.prev_down
        rpressed = rdown and not self.prev_rdown
        self.prev_down, self.prev_rdown = down, rdown
        self.hist.append((mx, my))
        if len(self.hist) > 4:
            self.hist.pop(0)
        b = self.held
        if b is None:
            if pressed or rpressed:
                hit = self.hit_test(mx, my)
                if hit is not None:
                    kind, obj = hit
                    if rpressed:
                        if kind == "ball":
                            self.shatter_ball(obj, None, 10 * S)
                        elif kind == "snowman":
                            self.destroy_snowman(obj)
                        else:
                            self.burst_pile(obj, mx)
                    elif kind == "ball":
                        self.grab_ball(obj, mx, my)
                    elif kind == "pile" and obj is self.ground_pile:
                        r0 = 6 * S
                        nb = Ball(mx, self.ground - r0, r0)
                        nb.state = "roll"
                        self.balls.append(nb)
                        self.held = nb
                        self.roll_x = mx
            return
        if not down:
            self.release()
            return
        if b.state == "roll":
            dist = abs(mx - self.roll_x)
            self.roll_x = mx
            if dist > 0 and b.r < MAX_BALL * S:
                need = 2 * math.pi * b.r * (dist * 0.1) / BALL_GAIN
                got = self.ground_pile.take(mx, b.r, need)
                if got > 0:
                    b.r = min(MAX_BALL * S,
                              b.r + got * BALL_GAIN / (2 * math.pi * b.r))
            b.x = min(max(mx, b.r), self.W - b.r)
            b.y = self.ground - b.r
            if my < b.y - b.r - 25 * S:
                b.state = "held"
                self.grab = (b.x - mx, b.y - my)
        else:
            b.x = min(max(mx + self.grab[0], b.r), self.W - b.r)
            b.y = min(max(my + self.grab[1], b.r), self.ground - b.r)

    def grab_ball(self, b, mx, my):
        if b.under is not None:
            b.under.over = None
            b.under = None
        b.state = "held"
        b.vx = b.vy = 0.0
        self.held = b
        self.grab = (b.x - mx, b.y - my)
        self.hist = [(mx, my)]

    def release(self):
        b = self.held
        self.held = None
        S = self.S
        if b.state == "roll":
            if b.r < 9 * S:
                self.balls.remove(b)
                return
            b.state = "free"
            b.vx = b.vy = 0.0
            return
        n = len(self.hist) - 1
        vx = vy = 0.0
        if n >= 1:
            vx = (self.hist[-1][0] - self.hist[0][0]) / n
            vy = (self.hist[-1][1] - self.hist[0][1]) / n
        sp = math.hypot(vx, vy)
        if sp < 4 * S:
            vx = vy = 0.0
        elif sp > 45 * S:
            k = 45 * S / sp
            vx *= k
            vy *= k
        b.vx, b.vy = vx, vy
        b.state = "free"

    # ---------------- sharchalar fizikasi ----------------
    def update_balls(self):
        S = self.S
        for b in list(self.balls):
            if b.state != "free" or b not in self.balls:
                continue
            b.vy += GRAVITY * S
            b.x += b.vx
            b.y += b.vy
            r = b.r
            thr = max(14 * S, 21 * S - 0.15 * r)    # shu tezlikdan oshsa — parchalanadi
            sp = math.hypot(b.vx, b.vy)
            if b.x < r or b.x > self.W - r:
                sign = 1.0 if b.x < r else -1.0
                if abs(b.vx) > thr:
                    self.shatter_ball(b, (sign, 0.0), sp)
                    continue
                b.x = r if sign > 0 else self.W - r
                b.vx = sign * abs(b.vx) * 0.5
            if b.y < r:
                b.y = r
                b.vy = abs(b.vy) * 0.3
            gy = self.ground - r
            if b.y >= gy:
                b.y = gy
                if b.vy > thr:
                    self.shatter_ball(b, (0.0, -1.0), sp)
                    continue
                b.vy = -b.vy * 0.25 if b.vy > 2.5 * S else 0.0
                b.vx *= 0.93
            done = False
            for o in list(self.balls):
                if o is b or o.state not in ("rest", "free"):
                    continue
                dx, dy = b.x - o.x, b.y - o.y
                mind = b.r + o.r
                d2 = dx * dx + dy * dy
                if d2 >= mind * mind:
                    continue
                if (o.state == "rest" and o.over is None and b.y < o.y
                        and abs(dx) < o.r * 0.85 and b.r <= o.r * 1.1
                        and 0 <= b.vy < thr):
                    self.snap(b, o)
                    done = True
                    break
                d = math.sqrt(d2)
                if d < 0.5:
                    nx, ny = random.choice((-0.3, 0.3)), -1.0
                    nl = math.hypot(nx, ny)
                    nx, ny = nx / nl, ny / nl
                    d = 1.0
                else:
                    nx, ny = dx / d, dy / d
                if abs(dx) < 1.0 and ny < 0:
                    nx += random.choice((-0.15, 0.15))
                vn = (b.vx - o.vx) * nx + (b.vy - o.vy) * ny
                if vn < -thr:
                    self.shatter_ball(b, (nx, ny), sp)
                    done = True
                    break
                pen = mind - d
                b.x += nx * pen
                b.y += ny * pen
                vn = b.vx * nx + b.vy * ny
                if vn < 0:
                    b.vx -= 1.2 * vn * nx
                    b.vy -= 1.2 * vn * ny
            if done:
                continue
            for sm in list(self.snowmen):
                if sm.dying:
                    continue
                for cx, cy, cr in self.snowman_circles(sm):
                    dx, dy = b.x - cx, b.y - cy
                    mind = b.r + cr
                    d2 = dx * dx + dy * dy
                    if d2 >= mind * mind:
                        continue
                    d = math.sqrt(d2) or 1.0
                    nx, ny = dx / d, dy / d
                    vn = b.vx * nx + b.vy * ny
                    if vn < -thr:
                        if vn < -thr * 1.9:
                            self.destroy_snowman(sm, 1.3)
                        self.shatter_ball(b, (nx, ny), sp)
                        done = True
                        break
                    pen = mind - d
                    b.x += nx * pen
                    b.y += ny * pen
                    if vn < 0:
                        b.vx -= 1.3 * vn * nx
                        b.vy -= 1.3 * vn * ny
                if done:
                    break
            if done:
                continue
            if b.y > gy:
                b.y = gy
                b.vy = min(b.vy, 0.0)
            if b.y >= gy - 0.01 and abs(b.vx) < 0.12 * S and abs(b.vy) < 0.01:
                b.state = "rest"
                b.vx = b.vy = 0.0

    def snap(self, b, o):
        b.under = o
        o.over = b
        b.x = o.x
        b.y = o.y - (o.r + b.r) * 0.92
        b.vx = b.vy = 0.0
        b.state = "rest"
        self.check_snowman(o)

    def check_snowman(self, ball):
        base = ball
        while base.under is not None:
            base = base.under
        chain = [base]
        while chain[-1].over is not None:
            chain.append(chain[-1].over)
        if len(chain) >= 3:
            radii = sorted([c.r for c in chain[:3]], reverse=True)
            x = base.x
            for c in chain:
                if c in self.balls:
                    self.balls.remove(c)
            self.snowmen.append(Snowman(x, radii))
            if len(self.snowmen) > 8:
                self.destroy_snowman(self.snowmen[0], 0.7)

    # ---------------- oyna va ikonkalar ustidagi qor ----------------
    def set_surfaces(self, wins, icons):
        """wins: [(key,x0,y0,x1,y1,pile_ok)] z-tartibda (tepadan pastga).
        icons: [(indeks,x0,y0,x1,y1,profil)] — y0 ikonka rasmining tepasi."""
        seen = set()
        higher = []
        for key, x0, y0, x1, y1, ok in wins:
            if ok:
                k = ("w", key)
                seen.add(k)
                self._upd_surface(k, "win", x0, x1, y0, higher, None)
            higher.append((x0, y0, x1, y1))
        for key, x0, y0, x1, y1, prof in icons:
            k = ("i", key)
            seen.add(k)
            self._upd_surface(k, "icon", x0, x1, y0, higher, prof)
        for k in list(self.surfaces):
            if k not in seen:
                s = self.surfaces.pop(k)
                self.slide_off(s, 0.0, 0.0)      # qor bo'shashib to'kiladi
                for it in (s.item, s.item2):
                    if it is not None:
                        self.dead.append(it)
        self.surf_list = [s for s in self.surfaces.values() if s.active]

    def _upd_surface(self, key, kind, x0, x1, y, higher, profile):
        S = self.S
        s = self.surfaces.get(key)
        if s is None:
            if kind == "win":
                s = Pile(x0, x1, y, self.col, 24 * S, self.slope, True, S)
            else:
                s = Pile(x0, x1, y, max(2, int(round(2 * S))), 7 * S, 1.4 * S, True, S, 0.35)
            self.surfaces[key] = s
        else:
            dx, dy = x0 - s.x0, y - s.y
            if abs(dx) > 3 * S or abs(dy) > 3 * S:     # siljitildi: qor sirpanib tushadi
                self.slide_off(s, max(-6 * S, min(6 * S, dx * 0.3)),
                               max(0.0, min(8 * S, dy * 0.3)))
            s.move(x0, x1, y)
        if kind == "icon":
            if s.prof_id != id(profile) or s.base is None or len(s.base) != len(s.h):
                s.set_profile(profile, x1 - x0)
                s.prof_id = id(profile)
        s.vis = self._vis(s, higher)
        s.active = s.vis is None or any(s.vis)

    @staticmethod
    def _vis(s, higher):
        yy = s.y - 1
        cov = [(a0, a1) for (a0, b0, a1, b1) in higher
               if b0 <= yy < b1 and a1 > s.x0 and a0 < s.x1]
        if not cov:
            return None
        n = len(s.h)
        mask = [True] * n
        for a0, a1 in cov:
            i0 = max(0, int((a0 - s.x0) // s.col))
            i1 = min(n - 1, int((a1 - s.x0) // s.col))
            for i in range(i0, i1 + 1):
                mask[i] = False
        return mask


# =====================================================================
#  Ilova: oynalar va chizish
# =====================================================================
class Bulb:
    __slots__ = ("body", "neck", "hl", "g1", "g2", "col", "ph", "s1", "s2")


class App:
    def __init__(self):
        dpi_aware()
        self.root = tk.Tk()
        root = self.root
        self.S = max(1.0, root.winfo_fpixels("1i") / 96.0)
        S = self.S
        self.W = root.winfo_screenwidth()
        self.H = root.winfo_screenheight()
        wa = work_area()
        self.ground = wa[3] if wa else self.H

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.geometry("%dx%d+0+0" % (self.W, self.H))
        root.config(bg=KEY)
        try:
            root.attributes("-transparentcolor", KEY)
        except tk.TclError:
            print("Bu dastur Windows uchun mo'ljallangan.")
            sys.exit(1)

        self.canvas = tk.Canvas(root, width=self.W, height=self.H,
                                bg=KEY, highlightthickness=0)
        self.canvas.pack()
        root.update()

        self.world = World(self.W, self.H, self.ground, S)
        gp = self.world.ground_pile
        gp.item = self.canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=PILE_BODY,
                                             outline="", tags="pile")
        gp.item2 = self.canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=WHITE,
                                              outline="", tags="pile")
        self.sm_sig = None
        self.lights_on = tk.BooleanVar(value=True)
        self.snow_var = tk.BooleanVar(value=True)
        self.auto_var = tk.BooleanVar(value=autostart_get())
        self.win_snow = tk.BooleanVar(value=True)
        self.icon_snow = tk.BooleanVar(value=True)
        self.bulbs = []
        self.lights_built = False

        self.hwnd = None
        self.click_through = False
        self.init_window_styles()
        self.set_click_through(True)

        self.scanner = WinScanner(self.hwnd, S)
        self.icon_reader = DesktopIcons(S, self.W, self.H)
        self.icons = []
        self.last_wins = []
        self.mouse = (-1, -1, False)
        self.refresh_n = 0

        self.panel = self.build_panel()
        self.root.after(30, self.tick)

    # ---------- Windows oyna uslublari ----------
    def init_window_styles(self):
        try:
            u, _ = setup_api()
            self.hwnd = u.GetAncestor(self.root.winfo_id(), 2) or \
                u.GetParent(self.root.winfo_id())
        except Exception:
            self.hwnd = None

    def set_click_through(self, on):
        try:
            u = ctypes.windll.user32
            st = u.GetWindowLongW(self.hwnd, -20)
            st |= 0x08000000 | 0x80 | 0x80000    # NOACTIVATE | TOOLWINDOW | LAYERED
            if on:
                st |= 0x20                        # TRANSPARENT
            else:
                st &= ~0x20
            u.SetWindowLongW(self.hwnd, -20, st)
        except Exception:
            pass
        self.click_through = on

    # ---------- Boshqaruv oynasi ----------
    def build_panel(self):
        S = self.S
        bg, fg = "#0f2742", "#e8f2ff"
        p = tk.Toplevel(self.root)
        p.title("Yangi yil qori")
        p.geometry("%dx%d+%d+%d" % (int(350 * S), int(640 * S), int(70 * S), int(90 * S)))
        p.resizable(False, False)
        p.configure(bg=bg)
        p.protocol("WM_DELETE_WINDOW", self.quit)

        tk.Label(p, text="❄  Yangi yil bilan!  ❄", font=("Segoe UI", 15, "bold"),
                 bg=bg, fg="white").pack(pady=(14, 4))
        help_text = (
            "Chap tugma:\n"
            "• Pastdagi qorni bosib o'ngga-chapga sudrang — sharcha dumalab "
            "kattalashadi. Yuqoriga sudrasangiz ko'tariladi, siltab qo'yib "
            "yuborsangiz otiladi.\n"
            "• Qattiq urilgan sharcha bo'laklarga ajraladi.\n"
            "• Katta sharcha ustiga kichiklarini qo'ying: 3 ta bo'lsa — qorbobo!\n\n"
            "O'ng tugma: qorbobo, sharcha yoki qor uyumi ustida bosing — "
            "parchalanadi.\n\n"
            "Qor shu oynaning tepasida, boshqa oynalar va ish stoli "
            "ikonkalari ustida ham to'planadi. Oyna yoki ikonkani siljitsangiz "
            "qor sirpanib tushadi."
        )
        tk.Label(p, text=help_text, justify="left", wraplength=int(315 * S),
                 bg=bg, fg="#cfe3ff", font=("Segoe UI", 9)).pack(padx=14, pady=6)

        def on_scale(v):
            self.world.n_flakes = int(float(v))

        sc = tk.Scale(p, from_=20, to=500, orient="horizontal", label="Qor miqdori",
                      command=on_scale, bg=bg, fg=fg, troughcolor="#1d4e89",
                      highlightthickness=0, length=int(290 * S))
        sc.set(260)
        sc.pack(pady=4)

        def chk(text, var, cmd=None):
            tk.Checkbutton(p, text=text, variable=var, command=cmd, bg=bg, fg=fg,
                           selectcolor="#1d4e89", activebackground=bg,
                           activeforeground="white", font=("Segoe UI", 10)
                           ).pack(anchor="w", padx=28)

        chk("Qor yog'sin", self.snow_var,
            lambda: setattr(self.world, "snowing", self.snow_var.get()))
        chk("Oynalar tepasida qor to'plansin", self.win_snow)
        chk("Ish stoli ikonkalari ustida qor", self.icon_snow)
        chk("Yangi yil chiroqlari (tepada)", self.lights_on)
        chk("Kompyuter yonganda o'zi ishga tushsin", self.auto_var,
            lambda: autostart_set(self.auto_var.get()))

        row = tk.Frame(p, bg=bg)
        row.pack(pady=14)
        tk.Button(row, text="Tozalash", width=11, command=self.world.clear,
                  bg="#2a6fb0", fg="white", relief="flat").pack(side="left", padx=6)
        tk.Button(row, text="Chiqish", width=11, command=self.quit,
                  bg="#b03a3a", fg="white", relief="flat").pack(side="left", padx=6)
        return p

    def quit(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    # ---------- Asosiy sikl ----------
    def covered(self, x, y):
        for (k, a, b, c, d, ok) in self.last_wins:
            if a <= x < c and b <= y < d:
                return True
        return False

    def refresh_surfaces(self):
        wins = self.scanner.scan(self.W, self.H, self.ground)
        self.last_wins = wins
        if not self.win_snow.get():
            wins = [(k, a, b, c, d, False) for (k, a, b, c, d, ok) in wins]
        if self.refresh_n % 3 == 0:
            self.icons = (self.icon_reader.query(self.covered, self.mouse)
                          if self.icon_snow.get() else [])
        self.refresh_n += 1
        self.world.set_surfaces(wins, self.icons)

    def tick(self):
        try:
            try:
                mx, my = cursor_pos()
                down = button_down(0x01)
                rdown = button_down(0x02)
            except Exception:
                mx, my, down, rdown = -1, -1, False, False
            self.mouse = (mx, my, down)
            w = self.world
            if w.t % 2 == 0:
                self.refresh_surfaces()
            w.step(mx, my, down, rdown)
            want = (w.held is not None) or (w.hit_test(mx, my) is not None)
            if want == self.click_through:
                self.set_click_through(not want)
            self.draw()
        except Exception:
            log_error()
        finally:
            try:
                self.root.after(30, self.tick)
            except Exception:
                pass

    # ---------- Chizish ----------
    def draw_sphere(self, x, y, r, tag):
        c = self.canvas
        c.create_oval(x - r, y - r, x + r, y + r, fill="#cddcec", outline="", tags=tag)
        k = 0.95 * r
        c.create_oval(x - 0.07 * r - k, y - 0.07 * r - k, x - 0.07 * r + k,
                      y - 0.07 * r + k, fill="#e8f0f9", outline="", tags=tag)
        k = 0.78 * r
        c.create_oval(x - 0.15 * r - k, y - 0.17 * r - k, x - 0.15 * r + k,
                      y - 0.17 * r + k, fill=WHITE, outline="", tags=tag)

    def draw(self):
        c, w = self.canvas, self.world
        for it in w.dead:
            c.delete(it)
        w.dead.clear()

        for f in w.flakes:
            pts = rot(f.shape, f.ang, f.x, f.y, f.r)
            if f.item is None:
                f.item = c.create_polygon(*pts, fill=FLAKE_FILL[f.tier], outline="")
            else:
                c.coords(f.item, *pts)

        for ch in w.chunks:
            r = ch.r
            if ch.dust:
                if ch.item is None:
                    ch.item = c.create_oval(0, 0, 0, 0, fill="#f4f9ff", outline="")
                c.coords(ch.item, ch.x - r, ch.y - r, ch.x + r, ch.y + r)
            else:
                pts = rot(ch.shape, 0.0, ch.x, ch.y, r)
                if ch.item is None:
                    ch.item = c.create_polygon(*pts, fill=WHITE, outline="")
                else:
                    c.coords(ch.item, *pts)

        gp = w.ground_pile
        for p in [gp] + list(w.surfaces.values()):
            is_g = p is gp
            show = True if is_g else (p.active and max(p.h) > 0.4)
            if p.item is None:
                p.item = c.create_polygon(0, 0, 0, 0, 0, 0, fill=PILE_BODY, outline="",
                                          tags="pile", state="hidden")
                p.item2 = c.create_polygon(0, 0, 0, 0, 0, 0, fill=WHITE, outline="",
                                           tags="pile", state="hidden")
                p.shown = False
                p.dirty = True
            if show != p.shown:
                st = "normal" if show else "hidden"
                c.itemconfigure(p.item, state=st)
                c.itemconfigure(p.item2, state=st)
                p.shown = show
                p.dirty = True
            if show and p.dirty and (not is_g or w.t % 3 == 0):
                c.coords(p.item, *p.points())
                c.coords(p.item2, *p.crust())
                p.dirty = False

        c.delete("ball")
        for b in w.balls:
            self.draw_sphere(b.x, b.y, b.r, "ball")

        c.delete("part")
        for p in w.parts:
            self.draw_part(p)

        sig = (len(w.snowmen), sum(len(s.gone) for s in w.snowmen))
        if sig != self.sm_sig or any(s.age < 44 for s in w.snowmen):
            c.delete("snowman")
            for s in w.snowmen:
                self.draw_snowman(s)
            self.sm_sig = sig

        if self.lights_on.get():
            if not self.lights_built:
                self.build_lights()
            if w.t % 3 == 0:
                self.update_lights()
        elif self.lights_built:
            c.delete("lights")
            self.bulbs = []
            self.lights_built = False

        c.tag_lower("ball")
        c.tag_lower("part")
        c.tag_lower("snowman")
        c.tag_lower("pile")

    def draw_part(self, p):
        c, S = self.canvas, self.S
        k, x, y, a = p.k, p.x, p.y, p.ang
        s, w = p.s, p.w
        if p.kind == "hat":
            c.create_polygon(rot([(-0.88 * s, 0.45 * s), (0.88 * s, 0.45 * s),
                                  (0.75 * s, -0.85 * s)], a, x, y, k),
                             fill="#d62828", outline="", tags="part")
            c.create_polygon(rot([(-0.95 * s, 0.28 * s), (0.95 * s, 0.28 * s),
                                  (0.95 * s, 0.62 * s), (-0.95 * s, 0.62 * s)],
                                 a, x, y, k), fill=WHITE, outline="", tags="part")
            px, py = rot([(0.75 * s, -0.85 * s)], a, x, y, k)
            rr = 0.22 * s * k
            c.create_oval(px - rr, py - rr, px + rr, py + rr, fill=WHITE,
                          outline="", tags="part")
        elif p.kind == "nose":
            c.create_polygon(rot([(-0.5 * s, -0.09 * s), (-0.5 * s, 0.09 * s),
                                  (0.5 * s, 0)], a, x, y, k),
                             fill="#ff8a1f", outline="", tags="part")
        elif p.kind == "stick":
            c.create_line(*rot([(-0.5 * s, 0), (0.5 * s, 0)], a, x, y, k), width=w * k,
                          fill="#6b4423", capstyle="round", tags="part")
            c.create_line(*rot([(0.1 * s, 0), (0.35 * s, -0.3 * s)], a, x, y, k),
                          width=max(1.5 * S, w * 0.6 * k), fill="#6b4423",
                          capstyle="round", tags="part")
        elif p.kind == "scarf":
            c.create_polygon(rot([(-0.5 * s, -w / 2), (0.5 * s, -w / 2),
                                  (0.5 * s, w / 2), (-0.5 * s, w / 2)], a, x, y, k),
                             fill="#2e9e4f", outline="", tags="part")
        else:
            rr = max(1.0, w * k)
            c.create_oval(x - rr, y - rr, x + rr, y + rr, fill="#222222",
                          outline="", tags="part")

    def draw_snowman(self, sm):
        c, S = self.canvas, self.S
        age = sm.age
        gone = sm.gone
        sc = 1.0 + (0.18 * math.sin(age / 16.0 * math.pi) if age < 16 else 0.0)
        r0, r1, r2 = [r * sc for r in sm.radii]
        x = sm.x
        y0 = self.world.ground - r0
        y1 = y0 - (r0 + r1) * 0.82
        y2 = y1 - (r1 + r2) * 0.82
        for k, (yy, rr) in enumerate(((y0, r0), (y1, r1), (y2, r2))):
            if k not in gone:
                self.draw_sphere(x, yy, rr, "snowman")

        def dot(px, py, rad, color):
            c.create_oval(px - rad, py - rad, px + rad, py + rad, fill=color,
                          outline="", tags="snowman")

        head = 2 not in gone
        mid = 1 not in gone
        if head and age >= 6:
            er = max(1.6 * S, 0.09 * r2)
            dot(x - 0.33 * r2, y2 - 0.22 * r2, er, "#222222")
            dot(x + 0.33 * r2, y2 - 0.22 * r2, er, "#222222")
        if head and age >= 12:
            c.create_polygon(x, y2 - 0.05 * r2, x, y2 + 0.17 * r2,
                             x + 0.95 * r2, y2 + 0.09 * r2, fill="#ff8a1f",
                             outline="", tags="snowman")
        if head and age >= 16:
            for k in range(-2, 3):
                dot(x + k * 0.15 * r2, y2 + (0.40 + 0.06 * (2 - abs(k))) * r2,
                    max(1.3 * S, 0.045 * r2), "#333333")
        if mid and age >= 20:
            for t in (-0.4, 0.0, 0.4):
                dot(x, y1 + t * r1, max(2 * S, 0.08 * r1), "#333333")
        if head and age >= 26:
            ny = y2 + r2 * 0.82
            wd = max(4 * S, 0.28 * r2)
            c.create_line(x - 0.8 * r2, ny, x + 0.8 * r2, ny, width=wd, fill="#2e9e4f",
                          capstyle="round", tags="snowman")
            c.create_rectangle(x + 0.25 * r2, ny, x + 0.25 * r2 + wd, ny + 0.9 * r1,
                               fill="#2e9e4f", outline="", tags="snowman")
        if mid and age >= 32:
            aw = max(3 * S, 0.1 * r1)
            for sign in (-1, 1):
                bx, by = x + sign * r1 * 0.88, y1 - r1 * 0.15
                ex, ey = bx + sign * r1 * 1.0, by - r1 * 0.8
                c.create_line(bx, by, ex, ey, width=aw, fill="#6b4423",
                              capstyle="round", tags="snowman")
                mx_, my_ = bx + (ex - bx) * 0.65, by + (ey - by) * 0.65
                for dy_ in (-0.35, 0.25):
                    c.create_line(mx_, my_, ex + sign * 0.1 * r1, ey + dy_ * r1,
                                  width=max(2 * S, aw * 0.6), fill="#6b4423",
                                  capstyle="round", tags="snowman")
        if head and age >= 40:
            hb = y2 - r2 * 0.62
            tipx, tipy = x + 0.75 * r2, hb - 1.3 * r2
            c.create_polygon(x - 0.88 * r2, hb, x + 0.88 * r2, hb, tipx, tipy,
                             fill="#d62828", outline="", tags="snowman")
            c.create_rectangle(x - 0.95 * r2, hb - 0.2 * r2, x + 0.95 * r2,
                               hb + 0.12 * r2, fill=WHITE, outline="", tags="snowman")
            c.create_oval(tipx - 0.22 * r2, tipy - 0.22 * r2, tipx + 0.22 * r2,
                          tipy + 0.22 * r2, fill=WHITE, outline="", tags="snowman")

    # ---------- Yangi yil chiroqlari ----------
    def wire_y(self, x):
        S = self.S
        seg = 210 * S
        return 2 * S + 16 * S * math.sin(math.pi * ((x % seg) / seg))

    def build_lights(self):
        c, S, W = self.canvas, self.S, self.W
        c.delete("lights")
        self.bulbs = []
        pts, hi = [], []
        x = 0.0
        while x <= W + 10 * S:
            y = self.wire_y(x)
            pts += [x, y]
            hi += [x, y - 1]
            x += 8 * S
        c.create_line(*pts, fill="#0b2415", width=max(3, int(3 * S)), tags="lights")
        c.create_line(*hi, fill="#2c5e3e", width=1, tags="lights")
        px = 0.0
        while px <= W + 5:
            py = self.wire_y(px)
            c.create_oval(px - 3 * S, py - 3 * S, px + 3 * S, py + 3 * S,
                          fill="#8a8f96", outline="#4a4f55", tags="lights")
            px += 210 * S
        sp = 30 * S
        i = 0
        x = sp * 0.6
        while x < W - 10 * S:
            y = self.wire_y(x)
            col = BULBS[i % len(BULBS)]
            c.create_line(x, y, x, y + 3 * S, fill="#0b2415", width=2, tags="lights")
            c.create_polygon(x - 2.6 * S, y + 3 * S, x + 2.6 * S, y + 3 * S,
                             x + 2.2 * S, y + 7.5 * S, x - 2.2 * S, y + 7.5 * S,
                             fill="#16241a", outline="", tags="lights")
            cy = y + 7 * S + 6.2 * S
            bl = Bulb()
            bl.g1 = bl.g2 = None
            try:
                bl.g2 = c.create_oval(x - 15 * S, cy - 15 * S, x + 15 * S, cy + 15 * S,
                                      fill=col[0], outline="", stipple="gray12",
                                      state="hidden", tags="lights")
                bl.g1 = c.create_oval(x - 9 * S, cy - 9 * S, x + 9 * S, cy + 9 * S,
                                      fill=col[0], outline="", stipple="gray25",
                                      state="hidden", tags="lights")
            except tk.TclError:
                bl.g1 = bl.g2 = None
            bl.neck = c.create_oval(x - 3 * S, y + 6 * S, x + 3 * S, y + 11 * S,
                                    fill=col[1], outline="", tags="lights")
            bl.body = c.create_oval(x - 4.4 * S, cy - 6.2 * S, x + 4.4 * S, cy + 6.2 * S,
                                    fill=col[1], outline="", tags="lights")
            bl.hl = c.create_oval(x - 2.7 * S, cy - 4.6 * S, x - 0.9 * S, cy - 1.2 * S,
                                  fill=col[1], outline="", tags="lights")
            bl.col = col
            bl.ph = i * 0.85 + random.uniform(0, 0.5)
            bl.s1 = bl.s2 = False
            self.bulbs.append(bl)
            x += sp
            i += 1
        self.lights_built = True

    def update_lights(self):
        c, t = self.canvas, self.world.t
        for bl in self.bulbs:
            b = (0.5 + 0.5 * math.sin(t * 0.07 + bl.ph)) ** 0.8
            fill = blend(bl.col[1], bl.col[0], b)
            c.itemconfigure(bl.body, fill=fill)
            c.itemconfigure(bl.neck, fill=fill)
            c.itemconfigure(bl.hl, fill=blend(blend(bl.col[1], WHITE, 0.3),
                                              blend(bl.col[0], WHITE, 0.8), b))
            if bl.g1 is not None:
                s1, s2 = b > 0.35, b > 0.62
                if s1 != bl.s1:
                    c.itemconfigure(bl.g1, state="normal" if s1 else "hidden")
                    bl.s1 = s1
                if s2 != bl.s2:
                    c.itemconfigure(bl.g2, state="normal" if s2 else "hidden")
                    bl.s2 = s2

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()

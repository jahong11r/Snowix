# -*- coding: utf-8 -*-
"""
❄ Yangi yil qori — realistik qor simulyatsiyasi (Windows)

  * Turli o'lchamdagi yumshoq qor zarrachalari, shamol va chuqurlik (uzoq/yaqin).
  * Qor yerda, ochiq oynalarning tepasida va ish stoli ikonkalari ustida to'planadi.
  * Oyna siljitilsa qor u bilan birga ketadi; pastga tushirilsa yoki yopilsa
    qor bo'shashib to'kiladi.
  * Chap tugma: qorni sudrab sharcha yasash, ko'tarish, otish.
  * Sharcha qattiq urilsa mayda bo'laklarga ajraladi.
  * 3 ta sharcha ustma-ust = qorbobo.
  * O'ng tugma: qorbobo, sharcha yoki qor uyumi ustida bosilsa parchalanadi.

Ishga tushirish:  python qor.py
Xato bo'lsa:  Foydalanuvchi papkasidagi qor_xato.txt faylga yoziladi.
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
GRAVITY = 0.6
MAX_BALL = 56
GAIN = 1.8               # qor parchasi maydoni -> qatlam maydoni
BALL_GAIN = 4.0          # sharcha maydoni = olingan qor maydoni * BALL_GAIN
MAX_CHUNKS = 420
APP_NAME = "YangiYilQori"
LIGHT_ON = ["#ff3b3b", "#ffd23b", "#3bff6b", "#3bb6ff", "#ff6bd6"]
LIGHT_OFF = ["#7a1d1d", "#7a6a1d", "#1d7a33", "#1d587a", "#7a1d66"]
FLAKE_FILL = ["#d7e5f5", "#e4eef9", "#f2f7fc", "#ffffff"]
FLAKE_EDGE = ["#d7e5f5", "#cfdff1", "#c6d9ee", "#c0d4ec"]
HALO = "#f0f6fc"
SKIP_CLASSES = ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                "Windows.UI.Core.CoreWindow", "NotifyIconOverflowWindow")

_errs = 0


def log_error():
    global _errs
    _errs += 1
    if _errs > 5:
        return
    try:
        import traceback
        p = os.path.join(os.path.expanduser("~"), "qor_xato.txt")
        with open(p, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
    except Exception:
        pass


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


def setup_api():
    """ctypes funksiyalari uchun to'g'ri turlarni o'rnatadi (64-bit uchun muhim)."""
    from ctypes import wintypes
    u = ctypes.windll.user32
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
    d = ctypes.windll.dwmapi
    d.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                        ctypes.c_void_p, wintypes.DWORD]
    return u, d


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
    """Ish stoli ikonkalari joylashuvini explorer.exe dan o'qiydi."""

    def __init__(self, S):
        self.S = S
        self.ok = False
        self.lv = None
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
            k.CloseHandle.argtypes = [ctypes.c_void_p]
            self.k = k
            self.find()
        except Exception:
            self.ok = False

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
            return
        lv = u.FindWindowExW(defview, None, "SysListView32", None)
        if not lv:
            return
        pid = ctypes.c_ulong(0)
        u.GetWindowThreadProcessId(lv, ctypes.byref(pid))
        proc = self.k.OpenProcess(0x38, False, pid.value)   # VM_OPERATION|READ|WRITE
        if not proc:
            return
        remote = self.k.VirtualAllocEx(proc, None, 64, 0x3000, 0x04)
        if not remote:
            return
        self.lv, self.proc, self.remote = lv, proc, remote
        self.ok = True

    def query(self):
        """[(indeks, x0, y0, x1, y1)] — ikonka rasmi to'rtburchagi (ekran koordinatalarida)."""
        if not self.ok:
            self.find()
            if not self.ok:
                return []
        u, k, S = self.u, self.k, self.S
        try:
            if not u.IsWindowVisible(self.lv):
                return []
            count = u.SendMessageW(self.lv, 0x1004, 0, 0)       # LVM_GETITEMCOUNT
            if count <= 0 or count > 300:
                return []
            org = POINT(0, 0)
            u.ClientToScreen(self.lv, ctypes.byref(org))
            out = []
            for i in range(count):
                r = RECT(1, 0, 0, 0)                            # LVIR_ICON
                k.WriteProcessMemory(self.proc, self.remote, ctypes.byref(r), 16, None)
                if not u.SendMessageW(self.lv, 0x100E, i, self.remote):  # GETITEMRECT
                    continue
                k.ReadProcessMemory(self.proc, self.remote, ctypes.byref(r), 16, None)
                x0 = org.x + r.l + 6 * S
                x1 = org.x + r.r - 6 * S
                y0 = org.y + r.t + 3 * S
                if x1 - x0 > 10 * S:
                    out.append((i, x0, y0, x1, org.y + r.b))
            return out
        except Exception:
            self.ok = False
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


class Flake:
    __slots__ = ("x", "y", "z", "tier", "r", "v", "ph", "fr", "wob", "halo",
                 "item", "hitem")

    def __init__(self, W, H, S, anywhere=False):
        self.item = self.hitem = None
        self.respawn(W, H, S, anywhere)

    def respawn(self, W, H, S, anywhere=False):
        z = random.random() ** 1.6          # ko'pchilik — mayda va uzoq
        self.z = z
        self.tier = int(z * 3.999)
        self.r = (0.9 + 3.4 * z ** 1.3) * S
        self.v = (1.0 + 2.4 * z) * S * random.uniform(0.9, 1.1)
        self.fr = random.uniform(0.02, 0.05)
        self.wob = random.uniform(0.25, 0.8)
        self.halo = z > 0.72
        self.x = random.uniform(0, W)
        self.y = random.uniform(0, H) if anywhere else random.uniform(-0.25 * H, -4)
        self.ph = random.uniform(0, 6.28)


class Chunk:
    """Qor bo'lagi (sharcha parchasi, to'kilgan qor yoki chang)."""
    __slots__ = ("x", "y", "vx", "vy", "r", "dust", "bounces", "item")

    def __init__(self, x, y, vx, vy, r, dust):
        self.x, self.y, self.vx, self.vy, self.r = x, y, vx, vy, r
        self.dust = dust
        self.bounces = 0
        self.item = None


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

    def __init__(self, x0, x1, y, col, maxh, slope, open_edges, S):
        self.col, self.maxh, self.slope = col, maxh, slope
        self.open, self.S = open_edges, S
        self.active = True
        self.h = []
        self.noise = []
        self.vis = None
        self.item = None
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

    def idx(self, x):
        i = int((x - self.x0) // self.col)
        if i < 0:
            return 0
        if i >= len(self.h):
            return len(self.h) - 1
        return i

    def height_at(self, x):
        return self.h[self.idx(x)]

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
            if 0 <= j < n:
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
        lim = self.slope
        moved = False
        for i in range(len(h) - 1):
            d = h[i] - h[i + 1]
            if d > lim:
                m = (d - lim) * 0.35
                h[i] -= m
                h[i + 1] += m
                moved = True
            elif d < -lim:
                m = (-d - lim) * 0.35
                h[i] += m
                h[i + 1] -= m
                moved = True
        if self.open:
            if h[0] > lim:
                h[0] -= (h[0] - lim) * 0.3
                moved = True
            if h[-1] > lim:
                h[-1] -= (h[-1] - lim) * 0.3
                moved = True
        if moved:
            self.dirty = True

    def points(self):
        y, col, S = self.y, self.col, self.S
        h, nz, vis = self.h, self.noise, self.vis
        n = len(h)

        def hh(i):
            if vis is not None and not vis[i]:
                return 0.0
            v = h[i]
            return v + nz[i] * min(1.0, v / (5 * S))

        pts = []
        if self.open:      # oyna chetiga yopishib turgan qor
            h0 = hh(0)
            pts += [self.x0 - 2 * col, y + 5 * S, self.x0 - 2 * col, y - h0 * 0.25,
                    self.x0 - col, y - h0 * 0.6]
        else:
            pts += [self.x0, y + 3]
        x = self.x0
        for i in range(n):
            pts += [x, y - hh(i)]
            x += col
        last = x - col
        if self.open:
            hl = hh(n - 1)
            pts += [last + col, y - hl * 0.6, last + 2 * col, y - hl * 0.25,
                    last + 2 * col, y + 5 * S]
        else:
            pts += [last, y + 3]
        return pts

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
                if max(s.h) >= 0.85 * s.maxh and random.random() < 0.12:
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
            if f.x < 0:
                f.x += W
            elif f.x >= W:
                f.x -= W
            landed = None
            besttop = None
            for s in surfs:
                if s.x0 <= f.x <= s.x1:
                    i = s.idx(f.x)
                    if s.vis is not None and not s.vis[i]:
                        continue
                    top = s.y - s.h[i]
                    if oy < top <= f.y and (besttop is None or top < besttop):
                        landed, besttop = s, top
            if landed is None and f.y >= gp.y - gp.height_at(f.x):
                landed = gp
            if landed is not None:
                landed.add(f.x, f.r)
                if extra > 0:
                    extra -= 1
                    self.kill_flake(f)
                    continue
                f.respawn(W, H, S)
            alive.append(f)
        while len(alive) < target:
            alive.append(Flake(W, H, S, False))
        if len(alive) > target and target > 0:
            for f in alive[target:]:
                self.kill_flake(f)
            alive = alive[:target]
        self.flakes = alive

    def kill_flake(self, f):
        if f.item is not None:
            self.dead.append(f.item)
        if f.hitem is not None:
            self.dead.append(f.hitem)

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
                c.vx *= 0.995
            c.x += c.vx
            c.y += c.vy
            if c.x < 0:
                c.x, c.vx = 0.0, abs(c.vx) * 0.4
            elif c.x > W:
                c.x, c.vx = float(W), -abs(c.vx) * 0.4
            surf = gp.y - gp.height_at(c.x)
            if c.y + c.r >= surf:
                if (not c.dust) and c.vy > 3 * S and c.bounces < 2:
                    c.y = surf - c.r
                    c.vy = -c.vy * 0.3
                    c.vx *= 0.65
                    c.bounces += 1
                else:
                    gp.add(c.x, c.r)
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
                             random.uniform(0.7, 1.5) * S, dust=True)

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
            self.spawn_chunk(x, p.y - p.height_at(x) - r,
                             vx0 + random.uniform(-1.5, 1.5) * S,
                             vy0 + random.uniform(-0.5, 1.0) * S, r)

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
                for _ in range(pieces):
                    self.spawn_chunk(
                        xc + random.uniform(-p.col, p.col),
                        p.y - p.height_at(xc) - r,
                        (xc - mx) / R * 6 * S + random.uniform(-1.5, 1.5) * S,
                        -random.uniform(2.5, 8.5) * S, r)
                for _ in range(2):
                    self.spawn_chunk(xc, p.y - p.height_at(xc) - S,
                                     (xc - mx) / R * 5 * S + random.uniform(-2, 2) * S,
                                     -random.uniform(2, 7) * S,
                                     random.uniform(0.7, 1.4) * S, dust=True)
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
                if s.vis is not None and not s.vis[i]:
                    continue
                h = s.h[i]
                if h >= 2.5 * S and s.y - h - 4 * S <= my <= s.y + 2 * S:
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
        icons: [(indeks,x0,y0,x1,y1)] (y0 — qor yotadigan chiziq)."""
        S = self.S
        seen = set()
        higher = []
        for key, x0, y0, x1, y1, ok in wins:
            if ok:
                k = ("w", key)
                seen.add(k)
                self._upd_surface(k, "win", x0, x1, y0, higher)
            higher.append((x0, y0, x1, y1))
        for key, x0, y0, x1, y1 in icons:
            k = ("i", key)
            seen.add(k)
            self._upd_surface(k, "icon", x0, x1, y0, higher)
        for k in list(self.surfaces):
            if k not in seen:
                s = self.surfaces.pop(k)
                self.shed(s, 1.0, maxn=40)      # qor bo'shashib to'kiladi
                if s.item is not None:
                    self.dead.append(s.item)
        self.surf_list = [s for s in self.surfaces.values() if s.active]

    def _upd_surface(self, key, kind, x0, x1, y, higher):
        S = self.S
        s = self.surfaces.get(key)
        if s is None:
            if kind == "win":
                s = Pile(x0, x1, y, self.col, 24 * S, self.slope, True, S)
            else:
                s = Pile(x0, x1, y, max(2, int(round(2 * S))), 7 * S, 1.4 * S, True, S)
            self.surfaces[key] = s
        else:
            dx, dy = x0 - s.x0, y - s.y
            if dy > 4 * S:                      # pastga tushirildi — qor to'kiladi
                self.shed(s, min(0.6, dy / (70 * S)), vx0=dx * 0.15, vy0=dy * 0.5)
            elif dy < -45 * S:                  # keskin yuqoriga otildi
                self.shed(s, 0.3, vx0=dx * 0.15, vy0=dy * 0.5)
            if abs(dx) > 8 * S:                 # yon tomonga tez siljidi
                self.shed(s, min(0.35, abs(dx) / (160 * S)), vx0=-dx * 0.25,
                          edge="L" if dx > 0 else "R", maxn=6)
            s.move(x0, x1, y)
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
        self.gp_item = self.canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=WHITE,
                                                  outline=EDGE, width=2, tags="pile")
        self.sm_sig = None
        self.lights_on = tk.BooleanVar(value=True)
        self.snow_var = tk.BooleanVar(value=True)
        self.auto_var = tk.BooleanVar(value=autostart_get())
        self.win_snow = tk.BooleanVar(value=True)
        self.icon_snow = tk.BooleanVar(value=True)

        self.hwnd = None
        self.click_through = False
        self.init_window_styles()
        self.set_click_through(True)

        self.scanner = WinScanner(self.hwnd, S)
        self.icon_reader = DesktopIcons(S)
        self.icons = []
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
            "ikonkalari ustida ham to'planadi. Oynani pastga tushirsangiz "
            "qor to'kiladi."
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
    def refresh_surfaces(self):
        wins = self.scanner.scan(self.W, self.H, self.ground)
        if not self.win_snow.get():
            wins = [(k, a, b, c, d, False) for (k, a, b, c, d, ok) in wins]
        if self.refresh_n % 3 == 0:
            self.icons = self.icon_reader.query() if self.icon_snow.get() else []
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
    def draw(self):
        c, w = self.canvas, self.world
        for it in w.dead:
            c.delete(it)
        w.dead.clear()

        for f in w.flakes:
            r = f.r
            if f.item is None:
                if f.halo:
                    f.hitem = c.create_oval(0, 0, 0, 0, fill=HALO, outline="")
                f.item = c.create_oval(0, 0, 0, 0, fill=FLAKE_FILL[f.tier],
                                       outline=FLAKE_EDGE[f.tier])
            if f.hitem is not None:
                hr = r * 1.9
                c.coords(f.hitem, f.x - hr, f.y - hr, f.x + hr, f.y + hr)
            c.coords(f.item, f.x - r, f.y - r, f.x + r, f.y + r)

        for ch in w.chunks:
            r = ch.r
            if ch.item is None:
                if ch.dust:
                    ch.item = c.create_oval(0, 0, 0, 0, fill="#f4f9ff", outline="#d3e4f6")
                else:
                    ch.item = c.create_oval(0, 0, 0, 0, fill=WHITE, outline=EDGE)
            c.coords(ch.item, ch.x - r, ch.y - r, ch.x + r, ch.y + r)

        gp = w.ground_pile
        if gp.dirty and w.t % 3 == 0:
            c.coords(self.gp_item, *gp.points())
            gp.dirty = False
        for s in w.surfaces.values():
            show = s.active and max(s.h) > 0.4
            if s.item is None:
                s.item = c.create_polygon(0, 0, 0, 0, 0, 0, fill=WHITE, outline=EDGE,
                                          width=1 if s.maxh < 12 * self.S else 2,
                                          tags="pile", state="hidden")
                s.shown = False
            if show != s.shown:
                c.itemconfigure(s.item, state="normal" if show else "hidden")
                s.shown = show
                s.dirty = True
            if show and s.dirty:
                c.coords(s.item, *s.points())
                s.dirty = False

        c.delete("ball")
        for b in w.balls:
            r = b.r
            c.create_oval(b.x - r, b.y - r, b.x + r, b.y + r, fill=WHITE,
                          outline=EDGE, width=2, tags="ball")
            c.create_arc(b.x - r + 3, b.y - r + 3, b.x + r - 3, b.y + r - 3,
                         start=-70, extent=110, style="arc", outline="#dbe9f8",
                         width=max(2, int(r * 0.18)), tags="ball")

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
            if w.t % 6 == 0:
                self.draw_lights()
        else:
            c.delete("lights")

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
                             fill="#d62828", outline="#9d1c1c", width=2, tags="part")
            c.create_polygon(rot([(-0.95 * s, 0.28 * s), (0.95 * s, 0.28 * s),
                                  (0.95 * s, 0.62 * s), (-0.95 * s, 0.62 * s)],
                                 a, x, y, k), fill=WHITE, outline=EDGE, tags="part")
            px, py = rot([(0.75 * s, -0.85 * s)], a, x, y, k)
            rr = 0.22 * s * k
            c.create_oval(px - rr, py - rr, px + rr, py + rr, fill=WHITE,
                          outline=EDGE, tags="part")
        elif p.kind == "nose":
            c.create_polygon(rot([(-0.5 * s, -0.09 * s), (-0.5 * s, 0.09 * s),
                                  (0.5 * s, 0)], a, x, y, k),
                             fill="#ff8a1f", outline="#c85f00", tags="part")
        elif p.kind == "stick":
            c.create_line(*rot([(-0.5 * s, 0), (0.5 * s, 0)], a, x, y, k), width=w * k,
                          fill="#6b4423", capstyle="round", tags="part")
            c.create_line(*rot([(0.1 * s, 0), (0.35 * s, -0.3 * s)], a, x, y, k),
                          width=max(1.5 * S, w * 0.6 * k), fill="#6b4423",
                          capstyle="round", tags="part")
        elif p.kind == "scarf":
            c.create_polygon(rot([(-0.5 * s, -w / 2), (0.5 * s, -w / 2),
                                  (0.5 * s, w / 2), (-0.5 * s, w / 2)], a, x, y, k),
                             fill="#2e9e4f", outline="#1f7a3a", tags="part")
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
                c.create_oval(x - rr, yy - rr, x + rr, yy + rr, fill=WHITE,
                              outline=EDGE, width=2, tags="snowman")

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
                             outline="#c85f00", tags="snowman")
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
                               fill="#2e9e4f", outline="#1f7a3a", tags="snowman")
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
                             fill="#d62828", outline="#9d1c1c", width=2, tags="snowman")
            c.create_rectangle(x - 0.95 * r2, hb - 0.2 * r2, x + 0.95 * r2,
                               hb + 0.12 * r2, fill=WHITE, outline=EDGE, tags="snowman")
            c.create_oval(tipx - 0.22 * r2, tipy - 0.22 * r2, tipx + 0.22 * r2,
                          tipy + 0.22 * r2, fill=WHITE, outline=EDGE, tags="snowman")

    def wire_y(self, x):
        S = self.S
        seg = 190 * S
        return 3 * S + 15 * S * math.sin(math.pi * ((x % seg) / seg))

    def draw_lights(self):
        c, S, w = self.canvas, self.S, self.world
        c.delete("lights")
        pts = []
        x = 0.0
        while x <= self.W + 10 * S:
            pts += [x, self.wire_y(x)]
            x += 10 * S
        c.create_line(*pts, fill="#14532d", width=2, tags="lights")
        sp = 34 * S
        i = 0
        x = sp / 2
        while x < self.W:
            y = self.wire_y(x)
            col = i % len(LIGHT_ON)
            on = ((w.t // 12) + i) % 3 != 0
            c.create_line(x, y, x, y + 4 * S, fill="#14532d", width=2, tags="lights")
            c.create_oval(x - 4 * S, y + 4 * S, x + 4 * S, y + 15 * S,
                          fill=LIGHT_ON[col] if on else LIGHT_OFF[col],
                          outline="", tags="lights")
            x += sp
            i += 1

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()

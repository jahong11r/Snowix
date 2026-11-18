# -*- coding: utf-8 -*-
"""
❄ Yangi yil qori — kompyuter ish stoli uchun (Windows)

Nimalar qila oladi:
  * Ish stoli ustida qor yog'adi va pastda to'planadi.
  * To'plangan qorni sichqoncha bilan bosib sudrasangiz — qor sharchasi
    dumalab kattalashadi. Tepaga sudrasangiz sharcha ko'tariladi.
  * Sharchani ushlab, otib yuborish mumkin.
  * 3 ta sharchani (kattasi pastda) ustma-ust qo'ysangiz — qorbobo paydo bo'ladi:
    burni sabzi, boshida qalpoq, qo'llari va sharfi bor.
  * Kichik boshqaruv oynasi ochiladi; qor uning tepasida ham to'planadi.
  * Tepada Yangi yil chiroqlari (girlyanda) yonib-o'chib turadi.

Ishga tushirish:  python qor.py
"""
import ctypes
import math
import os
import random
import sys
import tkinter as tk

KEY = "#010203"          # shaffof qilinadigan rang (boshqa joyda ishlatilmaydi)
WHITE = "#ffffff"
EDGE = "#b7d1ec"
GRAVITY = 0.6            # sharchalar uchun og'irlik kuchi
MAX_BALL = 56            # sharchaning maksimal radiusi
APP_NAME = "YangiYilQori"
LIGHT_ON = ["#ff3b3b", "#ffd23b", "#3bff6b", "#3bb6ff", "#ff6bd6"]
LIGHT_OFF = ["#7a1d1d", "#7a6a1d", "#1d7a33", "#1d587a", "#7a1d66"]


# =====================================================================
#  Windows bilan ishlash (DPI, sichqoncha, oyna uslublari)
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


def cursor_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def left_down():
    return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)


def work_area():
    """Taskbar hisobga olingan ish maydoni: (chap, tepa, o'ng, past)."""
    try:
        class RECT(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                        ("r", ctypes.c_long), ("b", ctypes.c_long)]
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


# =====================================================================
#  O'yin dunyosi (tkinter'siz — faqat hisob-kitob)
# =====================================================================
class Flake:
    __slots__ = ("x", "y", "r", "v", "ph", "item")

    def __init__(self, W, H, S, anywhere=False):
        self.item = None
        self.respawn(W, H, S, anywhere)

    def respawn(self, W, H, S, anywhere=False):
        self.r = random.uniform(1.8, 4.2) * S
        self.v = random.uniform(1.3, 2.8) * S * (0.75 + self.r / (S * 8))
        self.x = random.uniform(0, W)
        self.y = random.uniform(0, H) if anywhere else random.uniform(-0.25 * H, -4)
        self.ph = random.uniform(0, 6.28)


class Pile:
    """Bir sirtda (yer yoki oyna tepasi) to'planadigan qor qatlami."""
    WEIGHTS = [6 - abs(d) for d in range(-5, 6)]

    def __init__(self, x0, x1, y, col, maxh, slope, open_edges):
        self.col = col
        self.maxh = maxh
        self.slope = slope
        self.open = open_edges
        self.active = True
        self.h = []
        self.dirty = True
        self.x0 = self.x1 = self.y = None
        self.move(x0, x1, y)

    def move(self, x0, x1, y):
        n = max(3, int((x1 - x0) // self.col) + 1)
        if n > len(self.h):
            self.h += [0.0] * (n - len(self.h))
        elif n < len(self.h):
            del self.h[n:]
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

    def add(self, x, r):
        total = math.pi * r * r * 2.6 / self.col
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
        """Qatlamdan taxminan want_area (px^2) qor olib, haqiqatda olinganini qaytaradi."""
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
        """Qor tepalik bo'lib qolmasligi uchun silliqlash."""
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
        if self.open:  # oyna chetidan qor to'kilib ketadi
            if h[0] > lim:
                h[0] -= (h[0] - lim) * 0.3
                moved = True
            if h[-1] > lim:
                h[-1] -= (h[-1] - lim) * 0.3
                moved = True
        if moved:
            self.dirty = True

    def points(self):
        pts = [self.x0, self.y + 3]
        x = self.x0
        for v in self.h:
            pts.append(x)
            pts.append(self.y - v)
            x += self.col
        pts.append(x - self.col)
        pts.append(self.y + 3)
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
        self.under = None        # shu sharcha ustida turgan sharcha
        self.over = None         # shu sharcha ustiga qo'yilgan sharcha


class Snowman:
    def __init__(self, x, radii):
        self.x = x
        self.radii = radii
        self.age = 0


class World:
    def __init__(self, W, H, ground, S):
        self.W, self.H, self.ground, self.S = W, H, ground, S
        self.col = max(2, int(round(4 * S)))
        slope = 1.4 * S
        self.ground_pile = Pile(0, W, ground, self.col, 90 * S, slope, False)
        self.win_pile = Pile(0, 100, 100, self.col, 26 * S, slope, True)
        self.win_pile.active = False
        self.n_flakes = 220
        self.snowing = True
        self.flakes = [Flake(W, H, S, True) for _ in range(self.n_flakes)]
        self.dead = []           # o'chirilgan qor parchalarining canvas id lari
        self.balls = []
        self.snowmen = []
        self.held = None
        self.grab = (0.0, 0.0)
        self.roll_x = 0.0
        self.prev_down = False
        self.hist = []
        self.t = 0

    # ---------------- asosiy qadam ----------------
    def step(self, mx, my, down, win_rect):
        self.t += 1
        wp = self.win_pile
        if win_rect is None:
            wp.active = False
        else:
            wp.active = True
            wp.move(*win_rect)
        self.update_flakes()
        self.update_mouse(mx, my, down)
        self.update_balls()
        for sm in self.snowmen:
            sm.age += 1
        if self.t % 2 == 0:
            self.ground_pile.relax()
            wp.relax()

    def clear(self):
        self.ground_pile.clear()
        self.win_pile.clear()
        self.balls.clear()
        self.snowmen.clear()
        self.held = None

    # ---------------- qor parchalari ----------------
    def update_flakes(self):
        S, W, H = self.S, self.W, self.H
        gp, wp = self.ground_pile, self.win_pile
        target = self.n_flakes if self.snowing else 0
        extra = len(self.flakes) - target
        alive = []
        for f in self.flakes:
            oy = f.y
            f.y += f.v
            f.x += math.sin(f.ph + self.t * 0.03) * 0.7 * S
            if f.x < 0:
                f.x += W
            elif f.x >= W:
                f.x -= W
            landed = None
            if wp.active and wp.x0 <= f.x <= wp.x1:
                if oy < wp.y - wp.height_at(f.x) <= f.y:
                    landed = wp
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

    # ---------------- sichqoncha ----------------
    def hit_test(self, mx, my):
        S = self.S
        for b in reversed(self.balls):
            if b.state in ("rest", "free") and b.over is None:
                if (mx - b.x) ** 2 + (my - b.y) ** 2 <= (b.r + 3 * S) ** 2:
                    return b
        gp = self.ground_pile
        if 0 <= mx < self.W and my <= gp.y:
            h = gp.height_at(mx)
            if h >= 3 * S and my >= gp.y - h - 4 * S:
                return "pile"
        return None

    def update_mouse(self, mx, my, down):
        S = self.S
        pressed = down and not self.prev_down
        self.prev_down = down
        self.hist.append((mx, my))
        if len(self.hist) > 4:
            self.hist.pop(0)
        b = self.held
        if b is None:
            if pressed:
                hit = self.hit_test(mx, my)
                if isinstance(hit, Ball):
                    self.grab_ball(hit, mx, my)
                elif hit == "pile":
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
                need = 2 * math.pi * b.r * (dist * 0.09) / 3.0
                got = self.ground_pile.take(mx, b.r, need)
                if got > 0:
                    b.r = min(MAX_BALL * S, b.r + got * 3.0 / (2 * math.pi * b.r))
            b.x = min(max(mx, b.r), self.W - b.r)
            b.y = self.ground - b.r
            if my < b.y - b.r - 25 * S:      # tepaga tortildi -> ko'tariladi
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
            if b.state != "free":
                continue
            b.vy += GRAVITY * S
            b.x += b.vx
            b.y += b.vy
            r = b.r
            if b.x < r:
                b.x = r
                b.vx = abs(b.vx) * 0.5
            elif b.x > self.W - r:
                b.x = self.W - r
                b.vx = -abs(b.vx) * 0.5
            if b.y < r:
                b.y = r
                b.vy = abs(b.vy) * 0.3
            gy = self.ground - r
            if b.y >= gy:
                b.y = gy
                b.vy = -b.vy * 0.25 if b.vy > 2.5 * S else 0.0
                b.vx *= 0.85
            snapped = False
            for o in self.balls:
                if o is b or o.state not in ("rest", "free"):
                    continue
                dx, dy = b.x - o.x, b.y - o.y
                mind = b.r + o.r
                d2 = dx * dx + dy * dy
                if d2 >= mind * mind:
                    continue
                if (o.state == "rest" and o.over is None and b.y < o.y
                        and abs(dx) < o.r * 0.85 and b.r <= o.r * 1.1
                        and b.vy >= 0):
                    self.snap(b, o)
                    snapped = True
                    break
                d = math.sqrt(d2)
                if d < 0.5:
                    nx, ny, d = random.choice((-0.3, 0.3)), -1.0, 1.0
                    nl = math.hypot(nx, ny)
                    nx, ny = nx / nl, ny / nl
                else:
                    nx, ny = dx / d, dy / d
                if abs(dx) < 1.0 and ny < 0:      # aniq tepada muvozanat bo'lmasin
                    nx += random.choice((-0.15, 0.15))
                pen = mind - d
                b.x += nx * pen
                b.y += ny * pen
                vn = b.vx * nx + b.vy * ny
                if vn < 0:
                    b.vx -= 1.2 * vn * nx
                    b.vy -= 1.2 * vn * ny
            if snapped:
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
                self.snowmen.pop(0)


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
        ground = wa[3] if wa else self.H

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

        self.world = World(self.W, self.H, ground, S)
        self.gp_item = self.canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=WHITE,
                                                  outline=EDGE, width=2, tags="pile")
        self.wp_item = self.canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=WHITE,
                                                  outline=EDGE, width=2, tags="pile",
                                                  state="hidden")
        self.wp_visible = False
        self.sm_count = -1
        self.lights_on = tk.BooleanVar(value=True)
        self.snow_var = tk.BooleanVar(value=True)
        self.auto_var = tk.BooleanVar(value=autostart_get())

        self.hwnd = None
        self.click_through = False
        self.init_window_styles()
        self.set_click_through(True)

        self.panel = self.build_panel()
        self.root.after(30, self.tick)

    # ---------- Windows oyna uslublari ----------
    def init_window_styles(self):
        try:
            from ctypes import wintypes
            u = ctypes.windll.user32
            u.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
            u.GetAncestor.restype = wintypes.HWND
            u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            u.GetWindowLongW.restype = ctypes.c_long
            u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
            u.SetWindowLongW.restype = ctypes.c_long
            self.hwnd = u.GetAncestor(self.root.winfo_id(), 2) or \
                u.GetParent(self.root.winfo_id())
        except Exception:
            self.hwnd = None

    def set_click_through(self, on):
        """on=True: sichqoncha qor orqali ostidagi oynalarga o'tib ketadi."""
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
        p.geometry("%dx%d+%d+%d" % (int(340 * S), int(470 * S), int(70 * S), int(90 * S)))
        p.resizable(False, False)
        p.configure(bg=bg)
        p.protocol("WM_DELETE_WINDOW", self.quit)

        tk.Label(p, text="❄  Yangi yil bilan!  ❄", font=("Segoe UI", 15, "bold"),
                 bg=bg, fg="white").pack(pady=(14, 4))
        help_text = (
            "Qanday o'ynaladi:\n"
            "• Pastda yig'ilgan qorni sichqoncha bilan bosib o'ngga-chapga "
            "sudrang — qor sharchasi dumalab kattalashadi.\n"
            "• Sharchani yuqoriga sudrasangiz ko'tariladi. Qo'yib yuborsangiz "
            "tushadi, tez siltasangiz otilib ketadi.\n"
            "• Katta sharcha ustiga kichikroqlarini qo'ying. 3 ta bo'lsa — "
            "qorbobo paydo bo'ladi!\n"
            "• Qor shu oynaning tepasida ham to'planadi."
        )
        tk.Label(p, text=help_text, justify="left", wraplength=int(305 * S),
                 bg=bg, fg="#cfe3ff", font=("Segoe UI", 9)).pack(padx=14, pady=6)

        def on_scale(v):
            self.world.n_flakes = int(float(v))

        sc = tk.Scale(p, from_=20, to=500, orient="horizontal", label="Qor miqdori",
                      command=on_scale, bg=bg, fg=fg, troughcolor="#1d4e89",
                      highlightthickness=0, length=int(280 * S))
        sc.set(220)
        sc.pack(pady=4)

        def chk(text, var, cmd=None):
            tk.Checkbutton(p, text=text, variable=var, command=cmd, bg=bg, fg=fg,
                           selectcolor="#1d4e89", activebackground=bg,
                           activeforeground="white", font=("Segoe UI", 10)
                           ).pack(anchor="w", padx=28)

        chk("Qor yog'sin", self.snow_var,
            lambda: setattr(self.world, "snowing", self.snow_var.get()))
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

    def panel_rect(self):
        p = self.panel
        try:
            if p.state() != "normal":
                return None
            x0 = p.winfo_rootx()
            return (x0, x0 + p.winfo_width(), p.winfo_y())
        except Exception:
            return None

    # ---------- Asosiy sikl ----------
    def tick(self):
        try:
            try:
                mx, my = cursor_pos()
                down = left_down()
            except Exception:
                mx, my, down = -1, -1, False
            w = self.world
            w.step(mx, my, down, self.panel_rect())
            want_capture = (w.held is not None) or (w.hit_test(mx, my) is not None)
            if want_capture == self.click_through:
                self.set_click_through(not want_capture)
            self.draw()
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
                f.item = c.create_oval(0, 0, 0, 0, fill=WHITE, outline="#d3e6fa",
                                       tags="flake")
            c.coords(f.item, f.x - r, f.y - r, f.x + r, f.y + r)

        gp, wp = w.ground_pile, w.win_pile
        if gp.dirty and w.t % 3 == 0:
            c.coords(self.gp_item, *gp.points())
            gp.dirty = False
        show_wp = wp.active and max(wp.h) > 0.5
        if show_wp != self.wp_visible:
            c.itemconfigure(self.wp_item, state="normal" if show_wp else "hidden")
            self.wp_visible = show_wp
            wp.dirty = True
        if show_wp and wp.dirty and w.t % 3 == 0:
            c.coords(self.wp_item, *wp.points())
            wp.dirty = False

        c.delete("ball")
        for b in w.balls:
            r = b.r
            c.create_oval(b.x - r, b.y - r, b.x + r, b.y + r, fill=WHITE,
                          outline=EDGE, width=2, tags="ball")
            c.create_arc(b.x - r + 3, b.y - r + 3, b.x + r - 3, b.y + r - 3,
                         start=-70, extent=110, style="arc", outline="#dbe9f8",
                         width=max(2, int(r * 0.18)), tags="ball")

        if (len(w.snowmen) != self.sm_count
                or any(s.age < 44 for s in w.snowmen)):
            c.delete("snowman")
            for s in w.snowmen:
                self.draw_snowman(s)
            self.sm_count = len(w.snowmen)

        if self.lights_on.get():
            if w.t % 6 == 0:
                self.draw_lights()
        else:
            c.delete("lights")

        c.tag_lower("ball")
        c.tag_lower("snowman")
        c.tag_lower("pile")

    def draw_snowman(self, sm):
        c, S = self.canvas, self.S
        age = sm.age
        sc = 1.0 + (0.18 * math.sin(age / 16.0 * math.pi) if age < 16 else 0.0)
        r0, r1, r2 = [r * sc for r in sm.radii]
        x = sm.x
        y0 = self.world.ground - r0
        y1 = y0 - (r0 + r1) * 0.82
        y2 = y1 - (r1 + r2) * 0.82
        for yy, rr in ((y0, r0), (y1, r1), (y2, r2)):
            c.create_oval(x - rr, yy - rr, x + rr, yy + rr, fill=WHITE,
                          outline=EDGE, width=2, tags="snowman")

        def dot(px, py, rad, color):
            c.create_oval(px - rad, py - rad, px + rad, py + rad, fill=color,
                          outline="", tags="snowman")

        if age >= 6:    # ko'zlar
            er = max(1.6 * S, 0.09 * r2)
            dot(x - 0.33 * r2, y2 - 0.22 * r2, er, "#222222")
            dot(x + 0.33 * r2, y2 - 0.22 * r2, er, "#222222")
        if age >= 12:   # sabzi burun
            c.create_polygon(x, y2 - 0.05 * r2, x, y2 + 0.17 * r2,
                             x + 0.95 * r2, y2 + 0.09 * r2, fill="#ff8a1f",
                             outline="#c85f00", tags="snowman")
        if age >= 16:   # og'iz
            for k in range(-2, 3):
                dot(x + k * 0.15 * r2, y2 + (0.40 + 0.06 * (2 - abs(k))) * r2,
                    max(1.3 * S, 0.045 * r2), "#333333")
        if age >= 20:   # tugmalar
            for t in (-0.4, 0.0, 0.4):
                dot(x, y1 + t * r1, max(2 * S, 0.08 * r1), "#333333")
        if age >= 26:   # sharf
            ny = y2 + r2 * 0.82
            wd = max(4 * S, 0.28 * r2)
            c.create_line(x - 0.8 * r2, ny, x + 0.8 * r2, ny, width=wd, fill="#2e9e4f",
                          capstyle="round", tags="snowman")
            c.create_rectangle(x + 0.25 * r2, ny, x + 0.25 * r2 + wd, ny + 0.9 * r1,
                               fill="#2e9e4f", outline="#1f7a3a", tags="snowman")
        if age >= 32:   # qo'llar (shoxchalar)
            aw = max(3 * S, 0.1 * r1)
            for sign in (-1, 1):
                bx, by = x + sign * r1 * 0.88, y1 - r1 * 0.15
                ex, ey = bx + sign * r1 * 1.0, by - r1 * 0.8
                c.create_line(bx, by, ex, ey, width=aw, fill="#6b4423",
                              capstyle="round", tags="snowman")
                mx_, my_ = bx + (ex - bx) * 0.65, by + (ey - by) * 0.65
                for dy_ in (-0.35, 0.25):
                    c.create_line(mx_, my_, ex + sign * 0.1 * r1,
                                  ey + dy_ * r1, width=max(2 * S, aw * 0.6),
                                  fill="#6b4423", capstyle="round", tags="snowman")
        if age >= 40:   # Yangi yil qalpog'i
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

"""
Ish stolida qor yog'adigan va pastga yig'iladigan dastur (Windows uchun).
Ishga tushirish:  python qor.py
Chiqish: pastki o'ng burchakdagi "Chiqish" tugmasi yoki Esc.
"""
import ctypes
import random
import sys
import tkinter as tk

# ---------- Sozlamalar ----------
QOR_SONI = 150          # bir vaqtda tushayotgan qor parchalari
TEZLIK = (1.0, 3.5)     # tushish tezligi (min, max)
KATTALIK = (2, 5)       # qor parchasi kattaligi
MAX_BALANDLIK = 120     # yig'ilgan qorning maksimal balandligi (piksel)
USTUN = 4               # yig'ilish ustunining kengligi (piksel)
ERISH_TEZLIGI = 0.02    # yig'ilgan qor sekin erishi (0 = erimaydi)
FPS_MS = 25             # kadrlar oralig'i (millisekund)
SHAFFOF = "#010203"     # shaffof qilinadigan rang (ishlatilmaydigan rang)


def ish_maydoni():
    """Taskbar hisobga olingan ish stoli maydoni (Windows)."""
    try:
        class RECT(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                        ("r", ctypes.c_long), ("b", ctypes.c_long)]
        r = RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(r), 0)
        return r.l, r.t, r.r, r.b
    except Exception:
        return None


class QorDasturi:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.W = self.root.winfo_screenwidth()
        self.H = self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+0+0")
        self.root.config(bg=SHAFFOF)

        try:
            self.root.attributes("-transparentcolor", SHAFFOF)
        except tk.TclError:
            print("Bu dastur Windows uchun mo'ljallangan.")
            sys.exit(1)

        self.canvas = tk.Canvas(self.root, width=self.W, height=self.H,
                                bg=SHAFFOF, highlightthickness=0)
        self.canvas.pack()

        # Yer chizig'i (taskbar tepasi)
        wa = ish_maydoni()
        self.yer = wa[3] if wa else self.H

        self.ustunlar = self.W // USTUN + 2
        self.balandlik = [0.0] * self.ustunlar
        self.parchalar = [self.yangi_parcha(random.uniform(0, self.H))
                          for _ in range(QOR_SONI)]
        self.kadr = 0
        self.uyum_id = None

        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.update_idletasks()
        self.bosish_orqali_otkazish()
        self.chiqish_tugmasi()
        self.yangila()

    # --- Sichqoncha qor orqali o'tib ketishi (click-through) ---
    def bosish_orqali_otkazish(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            GWL_EXSTYLE = -20
            stil = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, stil | 0x80000 | 0x20)  # LAYERED | TRANSPARENT
        except Exception:
            pass

    # --- Kichik "Chiqish" tugmasi (alohida oyna) ---
    def chiqish_tugmasi(self):
        self.tugma = tk.Toplevel(self.root)
        self.tugma.overrideredirect(True)
        self.tugma.attributes("-topmost", True)
        x = self.W - 100
        y = self.yer - 40
        self.tugma.geometry(f"90x30+{x}+{y}")
        tk.Button(self.tugma, text="❄ Chiqish", command=self.root.destroy,
                  bg="#1e3a5f", fg="white", relief="flat").pack(fill="both", expand=True)

    def yangi_parcha(self, y=None):
        r = random.uniform(*KATTALIK)
        return {
            "x": random.uniform(0, self.W),
            "y": random.uniform(-self.H * 0.2, 0) if y is None else y,
            "r": r,
            "v": random.uniform(*TEZLIK) * (0.6 + r / 8),
            "faza": random.uniform(0, 6.28),
            "id": None,
        }

    def yigish(self, x, r):
        """Qor parchasi yerga tushganda ustunlarga qo'shiladi."""
        i = int(x // USTUN)
        for d in (-2, -1, 0, 1, 2):
            j = i + d
            if 0 <= j < self.ustunlar:
                qoshim = r * (0.5 if d == 0 else 0.25 if abs(d) == 1 else 0.1)
                self.balandlik[j] = min(MAX_BALANDLIK, self.balandlik[j] + qoshim)

    def silliqlash(self):
        """Yig'ilgan qor tekis tarqalib, chiroyli tepalik hosil qilsin."""
        b = self.balandlik
        yangi = b[:]
        for i in range(1, len(b) - 1):
            ort = (b[i - 1] + b[i] + b[i + 1]) / 3
            yangi[i] = b[i] + (ort - b[i]) * 0.3
        self.balandlik = [max(0.0, h - ERISH_TEZLIGI) for h in yangi]

    def pol_chizish(self):
        if self.uyum_id:
            self.canvas.delete(self.uyum_id)
        pts = [0, self.yer + 2]
        for i, h in enumerate(self.balandlik):
            pts += [i * USTUN, self.yer - h]
        pts += [self.W, self.yer + 2]
        self.uyum_id = self.canvas.create_polygon(
            pts, fill="white", outline="#dfefff", smooth=False)

    def yangila(self):
        self.kadr += 1
        import math
        for p in self.parchalar:
            p["y"] += p["v"]
            p["x"] += math.sin(p["faza"] + self.kadr * 0.03) * 0.6
            p["x"] %= self.W

            i = min(int(p["x"] // USTUN), self.ustunlar - 1)
            yer_balandligi = self.yer - self.balandlik[i]
            if p["y"] >= yer_balandligi:
                self.yigish(p["x"], p["r"])
                p.update(self.yangi_parcha())
                if p["id"]:
                    self.canvas.delete(p["id"])
                    p["id"] = None
                continue

            r = p["r"]
            if p["id"] is None:
                p["id"] = self.canvas.create_oval(0, 0, 0, 0, fill="white", outline="")
            self.canvas.coords(p["id"], p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r)

        if self.kadr % 3 == 0:
            self.silliqlash()
            self.pol_chizish()

        self.root.after(FPS_MS, self.yangila)

    def ishga_tushirish(self):
        self.root.mainloop()


if __name__ == "__main__":
    QorDasturi().ishga_tushirish()

# ================================
# SISTEM JURUKUR PRO (GITHUB VERSION)
# ================================

import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog

import pandas as pd
import numpy as np
import os
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Optional dependency (avoid crash if missing)
try:
    import ezdxf
    DXF_AVAILABLE = True
except:
    DXF_AVAILABLE = False


# ================================
# UTIL FUNCTIONS (UNCHANGED)
# ================================

def dmss_to_decimal(dmss_float):
    val = str(dmss_float)
    if "." not in val:
        return float(val)

    deg = int(float(val))
    frac = round((float(val) - deg) * 100, 4)
    m = int(frac)
    s = round((frac - m) * 100, 2)

    return deg + (m/60) + (s/3600)


def decimal_to_dms_str(dmss_float):
    try:
        if dmss_float == "-" or dmss_float is None:
            return "-"

        val = float(dmss_float)
        deg = int(val)
        frac = round((val - deg) * 60, 6)
        m = int(frac)
        s = int(round((frac - m) * 60, 0))

        if s == 60:
            m += 1
            s = 0
        if m == 60:
            deg += 1
            m = 0

        return f"{deg}° {m:02d}' {s:02d}\""
    except:
        return str(dmss_float)


def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


# ================================
# MAIN APP (LOGIC TAK DIUBAH)
# ================================

class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("📐 SISTEM JURUKUR PRO - GITHUB VERSION")
        self.geometry("1400x900")

        self.df = None
        self.manual_data = []

        self.setup_ui()


    def setup_ui(self):
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.pack(side="left", fill="y", padx=5, pady=5)

        ctk.CTkButton(self.sidebar, text="INPUT DATA", command=self.buka_input).pack(pady=10, fill="x")
        ctk.CTkButton(self.sidebar, text="EXPORT CSV", command=self.export_csv).pack(pady=5, fill="x")
        ctk.CTkButton(self.sidebar, text="EXPORT GEOJSON", command=self.export_geojson).pack(pady=5, fill="x")

        if DXF_AVAILABLE:
            ctk.CTkButton(self.sidebar, text="EXPORT DXF", command=self.export_dxf).pack(pady=5, fill="x")

        self.lbl_luas = ctk.CTkLabel(self, text="Luas: -")
        self.lbl_luas.pack()

        self.frame_plot = ctk.CTkFrame(self)
        self.frame_plot.pack(expand=True, fill="both")


    # ================================
    # VISUALIZE
    # ================================

    def visualize(self):
        if self.df is None:
            return

        for w in self.frame_plot.winfo_children():
            w.destroy()

        x = self.df['E'].values
        y = self.df['N'].values

        luas = kira_luas(x, y)
        self.lbl_luas.configure(text=f"Luas: {luas:.3f} m²")

        fig, ax = plt.subplots()

        ax.plot(list(x)+[x[0]], list(y)+[y[0]], '-o')
        ax.set_aspect('equal')

        canvas = FigureCanvasTkAgg(fig, master=self.frame_plot)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


    # ================================
    # INPUT
    # ================================

    def buka_input(self):
        win = ctk.CTkToplevel(self)
        win.title("Input Data")

        self.e_brg = ctk.CTkEntry(win, placeholder_text="Bearing")
        self.e_brg.pack(pady=5)

        self.e_dist = ctk.CTkEntry(win, placeholder_text="Distance")
        self.e_dist.pack(pady=5)

        ctk.CTkButton(win, text="Tambah", command=self.tambah_data).pack(pady=5)
        ctk.CTkButton(win, text="Proses", command=self.proses).pack(pady=5)


    def tambah_data(self):
        try:
            brg = float(self.e_brg.get())
            dist = float(self.e_dist.get())

            self.manual_data.append((brg, dist))

        except:
            messagebox.showerror("Error", "Input salah")


    def proses(self):
        ce, cn = 0, 0
        rows = [{"STN": 1, "E": ce, "N": cn}]

        for i, (b, d) in enumerate(self.manual_data):
            rad = np.radians(dmss_to_decimal(b))

            ce += d * np.sin(rad)
            cn += d * np.cos(rad)

            rows.append({"STN": i+2, "E": ce, "N": cn})

        self.df = pd.DataFrame(rows)
        self.visualize()


    # ================================
    # EXPORT
    # ================================

    def export_csv(self):
        if self.df is None:
            return

        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            self.df.to_csv(path, index=False)


    def export_geojson(self):
        if self.df is None:
            return

        path = filedialog.asksaveasfilename(defaultextension=".geojson")

        coords = [[float(r.E), float(r.N)] for _, r in self.df.iterrows()]
        coords.append(coords[0])

        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [coords]}
            }]
        }

        with open(path, "w") as f:
            json.dump(geojson, f, indent=4)


    def export_dxf(self):
        if not DXF_AVAILABLE:
            messagebox.showerror("Error", "ezdxf not installed")
            return


# ================================
# ENTRY POINT
# ================================

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    app = App()
    app.mainloop()

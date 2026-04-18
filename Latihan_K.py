import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
import pandas as pd
import numpy as np
import os
import sys
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import ezdxf

# --- FUNGSI UTILITI ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def dmss_to_decimal(dmss_float):
    val = str(dmss_float)
    if "." not in val: return float(val)
    deg = int(float(val))
    frac = round((float(val) - deg) * 100, 4)
    m = int(frac)
    s = round((frac - m) * 100, 2)
    return deg + (m/60) + (s/3600)

def decimal_to_dms_str(dmss_float):
    try:
        if dmss_float == "-" or dmss_float is None: return "-"
        val = float(dmss_float)
        deg = int(val)
        frac = round((val - deg) * 60, 6)
        m = int(frac)
        s = int(round((frac - m) * 60, 0))
        if s == 60: m += 1; s = 0
        if m == 60: deg += 1; m = 0
        return f"{deg}° {m:02d}' {s:02d}\""
    except:
        return str(dmss_float)

def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- APLIKASI UTAMA ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("📐 SISTEM JURUKUR PRO - MODUL LATIT/DIPAT & LUAS")
        self.geometry("1550x950")
        
        self.df = None
        self.manual_data = [] 
        self.tree = None 
        self.show_table = False 
        
        self.setup_main_ui()

    def setup_main_ui(self):
        # SIDEBAR
        self.sidebar = ctk.CTkScrollableFrame(self, width=300, label_text="MENU UTAMA")
        self.sidebar.pack(side="left", fill="y", padx=5, pady=5)
        
        ctk.CTkButton(self.sidebar, text="⌨️ INPUT DATA TRABAS", command=self.buka_input_manual, fg_color="#2c3e50").pack(pady=10, padx=10, fill="x")
        self.btn_toggle_table = ctk.CTkButton(self.sidebar, text="📊 BUKA JADUAL DATA", command=self.toggle_table, fg_color="#34495e")
        self.btn_toggle_table.pack(pady=5, padx=10, fill="x")
        
        ctk.CTkButton(self.sidebar, text="💾 EKSPORT KE DXF (CAD)", command=self.export_dxf, fg_color="#e67e22").pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(self.sidebar, text="🌍 EKSPORT KE QGIS (CSV)", command=self.export_qgis_csv, fg_color="#2980b9").pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(self.sidebar, text="🗺️ EKSPORT KE GEOJSON", command=self.export_geojson, fg_color="#8e44ad").pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(self.sidebar, text="🗑️ RESET SEMUA", command=self.reset_data, fg_color="#c0392b").pack(pady=5, padx=10, fill="x")
        
        ctk.CTkLabel(self.sidebar, text="⚙️ TETAPAN VISUAL", font=("Arial", 12, "bold")).pack(pady=(15, 5))
        self.sw_stn = ctk.CTkSwitch(self.sidebar, text="Tunjuk No Stesen"); self.sw_stn.select(); self.sw_stn.pack(pady=5, padx=10)
        self.sw_label = ctk.CTkSwitch(self.sidebar, text="Tunjuk B & J"); self.sw_label.select(); self.sw_label.pack(pady=5, padx=10)

        ctk.CTkLabel(self.sidebar, text="📏 Saiz Teks Stesen:").pack(padx=10, anchor="w", pady=(10,0))
        self.slider_stn_size = ctk.CTkSlider(self.sidebar, from_=1, to=15, number_of_steps=14); self.slider_stn_size.set(4); self.slider_stn_size.pack(pady=5, padx=10, fill="x")

        ctk.CTkLabel(self.sidebar, text="📏 Saiz Teks B & J:").pack(padx=10, anchor="w", pady=(10,0))
        self.slider_label_size = ctk.CTkSlider(self.sidebar, from_=1, to=10, number_of_steps=10); self.slider_label_size.set(3); self.slider_label_size.pack(pady=5, padx=10, fill="x")
        
        ctk.CTkButton(self.sidebar, text="🔄 KEMASKINI PLOT", command=self.visualize, fg_color="#27ae60").pack(pady=15, padx=10, fill="x")

        # PANEL UTAMA
        self.main_container = ctk.CTkFrame(self); self.main_container.pack(side="right", expand=True, fill="both", padx=5, pady=5)
        self.info_panel = ctk.CTkFrame(self.main_container, height=60); self.info_panel.pack(side="top", fill="x", padx=10, pady=5)
        
        self.lbl_luas = ctk.CTkLabel(self.info_panel, text="Luas: -", font=("Arial", 16, "bold")); self.lbl_luas.pack(side="left", padx=20)
        
        # --- TAMBAH: Label Skala di UI ---
        self.lbl_skala = ctk.CTkLabel(self.info_panel, text="Skala: -", font=("Arial", 16, "bold"), text_color="#e67e22")
        self.lbl_skala.pack(side="left", padx=20)
        
        ctk.CTkLabel(self.info_panel, text="*Klik titik/baris jadual untuk maklumat terperinci stesen", font=("Arial", 11, "italic")).pack(side="right", padx=20)
        
        self.display_frame = ctk.CTkFrame(self.main_container); self.display_frame.pack(expand=True, fill="both", padx=10, pady=10)

    # --- TAMBAH: Fungsi Hitung Skala Piawai ---
    def hitung_skala(self, x_vals, y_vals):
        if len(x_vals) == 0: return 0
        lebar_m = np.max(x_vals) - np.min(x_vals)
        tinggi_m = np.max(y_vals) - np.min(y_vals)
        dimensi_maks = max(lebar_m, tinggi_m)
        
        # Faktor ruang lukisan (anggaran ruang dalam meter pada kertas/skrin)
        ruang_selamat = 0.18 
        skala_mentah = dimensi_maks / ruang_selamat
        
        # Senarai skala piawai ukur
        skala_piawai = [10, 20, 50, 100, 200, 250, 300, 500, 750, 1000, 1250, 1500, 2000, 2500, 5000]
        for s in skala_piawai:
            if s >= skala_mentah: return s
        return int(np.ceil(skala_mentah / 1000.0) * 1000)

    def toggle_table(self):
        self.show_table = not self.show_table
        if self.show_table:
            self.btn_toggle_table.configure(text="📊 TUTUP JADUAL DATA", fg_color="#c0392b")
        else:
            self.btn_toggle_table.configure(text="📊 BUKA JADUAL DATA", fg_color="#34495e")
        self.visualize()

    def tunjuk_info_lot(self, event):
        if self.df is None: return
        x, y = self.df['E'].values, self.df['N'].values
        luas_m2 = kira_luas(x, y)
        skala = self.hitung_skala(x, y)
        msg = (f"📊 MAKLUMAT LOT\n----------------------------\n"
               f"Luas (m²)   : {luas_m2:.3f}\nLuas (Ekar) : {luas_m2 * 0.000247105:.4f}\n"
               f"Skala Anggaran : 1:{skala}\n"
               f"Bil. Stesen : {self.df['STN'].nunique()}")
        messagebox.showinfo("Info Keseluruhan Lot", msg)

    def tunjuk_info_popup(self, index):
        if self.df is None or index >= len(self.df): return
        row = self.df.iloc[index]
        brg = decimal_to_dms_str(row['BRG']) if row['BRG'] != "-" else "-"
        dist = f"{row['DIST']:.3f} m" if row['DIST'] != 0 else "-"
        latit = f"{row['LATIT']:.3f}" if row['LATIT'] != "-" else "-"
        dipat = f"{row['DIPAT']:.3f}" if row['DIPAT'] != "-" else "-"
        info_msg = (f"📍 STESEN: {row['STN']}\n----------------------------\n"
                    f"Latit (dN) : {latit}\nDipat (dE) : {dipat}\n"
                    f"Bearing     : {brg}\nJarak       : {dist}\n"
                    f"----------------------------\n"
                    f"Easting (E): {row['E']:.4f}\nNorthing(N): {row['N']:.4f}")
        messagebox.showinfo(f"Maklumat Stesen {row['STN']}", info_msg)

    def on_click_event(self, event):
        if hasattr(event, 'ind') and event.ind is not None:
            self.tunjuk_info_popup(event.ind[0])
        else:
            self.tunjuk_info_lot(event)

    def visualize(self):
        if self.df is None: return
        for w in self.display_frame.winfo_children(): w.destroy()
        x, y = self.df['E'].values, self.df['N'].values
        n_points = len(self.df)
        luas = kira_luas(x, y)
        
        # --- TAMBAH: Update Label Skala di Visualizer ---
        skala_lot = self.hitung_skala(x, y)
        self.lbl_luas.configure(text=f"Luas: {luas:.3f} m²")
        self.lbl_skala.configure(text=f"Skala: 1:{skala_lot}")
        
        fig, ax = plt.subplots(figsize=(6,6))
        ax.plot(list(x)+[x[0]], list(y)+[y[0]], '-ko', markersize=8, picker=5)
        ax.fill(x, y, color="cyan", alpha=0.1, picker=True)
        ax.set_aspect('equal')

        for i in range(n_points):
            if self.sw_stn.get():
                ax.text(x[i], y[i], f"  {self.df.STN.iloc[i]}", color="blue", fontweight="bold", fontsize=self.slider_stn_size.get() + 8)
            
            if self.sw_label.get():
                p1 = i
                p2 = (i + 1) % n_points 
                x_mid = (x[p1] + x[p2]) / 2
                y_mid = (y[p1] + y[p2]) / 2
                dx, dy = x[p2] - x[p1], y[p2] - y[p1]
                angle = np.degrees(np.arctan2(dy, dx))
                if angle > 90: angle -= 180
                elif angle < -90: angle += 180
                b_val = self.df.BRG.iloc[p2]
                d_val = self.df.DIST.iloc[p2]
                if b_val != "-":
                    ax.text(x_mid, y_mid, f"{decimal_to_dms_str(b_val)}\n{d_val:.3f}m", 
                            fontsize=self.slider_label_size.get() + 6, color="red", ha='center', va='center', rotation=angle,
                            bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7, ec='none'))

        canvas = FigureCanvasTkAgg(fig, master=self.display_frame); canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        fig.canvas.mpl_connect('pick_event', self.on_click_event)

        if self.show_table:
            t_frame = ctk.CTkFrame(self.display_frame, height=250)
            t_frame.pack(side="bottom", fill="x", pady=(10,0))
            cols = ("STN", "BEARING", "DIST", "LATIT", "DIPAT", "E", "N")
            self.tree = ttk.Treeview(t_frame, columns=cols, show="headings", height=8)
            for c in cols: 
                self.tree.heading(c, text=c)
                self.tree.column(c, width=110, anchor="center")
            for idx, r in self.df.iterrows():
                d_brg = decimal_to_dms_str(r.BRG) if r.BRG != "-" else "-"
                lat_str = f"{r.LATIT:.3f}" if r.LATIT != "-" else "-"
                dip_str = f"{r.DIPAT:.3f}" if r.DIPAT != "-" else "-"
                self.tree.insert("", "end", values=(r.STN, d_brg, f"{r.DIST:.3f}", lat_str, dip_str, f"{r.E:.3f}", f"{r.N:.3f}"))
            
            self.tree.bind("<ButtonRelease-1>", lambda e: self.tunjuk_info_popup(self.tree.index(self.tree.selection()[0])) if self.tree.selection() else None)
            sc_y = ttk.Scrollbar(t_frame, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=sc_y.set)
            sc_y.pack(side="right", fill="y")
            self.tree.pack(side="left", fill="both", expand=True)

    def buka_input_manual(self):
        self.win = ctk.CTkToplevel(self); self.win.title("Input Data Ukur"); self.win.geometry("1100x850"); self.win.attributes("-topmost", True)
        left_p = ctk.CTkFrame(self.win, width=420); left_p.pack(side="left", fill="y", padx=10, pady=10)
        ctk.CTkLabel(left_p, text="📍 KOORDINAT RUJUKAN", font=("Arial", 12, "bold")).pack(pady=(10,0))
        ref_f = ctk.CTkFrame(left_p, fg_color="transparent"); ref_f.pack(pady=5, padx=10, fill="x")
        self.e_ref_stn = ctk.CTkEntry(ref_f, placeholder_text="Stn", width=60); self.e_ref_stn.pack(side="left", padx=2)
        self.e_ref_e = ctk.CTkEntry(ref_f, placeholder_text="Easting", width=100); self.e_ref_e.pack(side="left", padx=2, expand=True, fill="x")
        self.e_ref_n = ctk.CTkEntry(ref_f, placeholder_text="Northing", width=100); self.e_ref_n.pack(side="left", padx=2, expand=True, fill="x")
        ref_btn_f = ctk.CTkFrame(left_p, fg_color="transparent"); ref_btn_f.pack(fill="x", padx=10)
        ctk.CTkButton(ref_btn_f, text="➕ Simpan Koord", command=self.tambah_koordinat_rujukan).pack(side="left", padx=5)
        ctk.CTkButton(ref_btn_f, text="🗑️ Padam", fg_color="#7f8c8d", command=lambda: [self.tree_coords.delete(i) for i in self.tree_coords.selection()] or (self.tree_coords.get_children() and self.tree_coords.delete(self.tree_coords.get_children()[-1]))).pack(side="left", padx=5)
        self.tree_coords = ttk.Treeview(left_p, columns=("stn", "e", "n"), show="headings", height=3); self.tree_coords.pack(pady=5, padx=10, fill="x")
        for c in ("stn", "e", "n"): self.tree_coords.heading(c, text=c.upper())
        ctk.CTkLabel(left_p, text="📏 DATA TRABAS", font=("Arial", 12, "bold")).pack(pady=(15,0))
        self.e_stn_range = ctk.CTkEntry(left_p); self.e_stn_range.pack(pady=5, padx=20, fill="x"); self.auto_fill_stn()
        self.e_brg = ctk.CTkEntry(left_p, placeholder_text="Bearing (D.MMSS)"); self.e_brg.pack(pady=5, padx=20, fill="x")
        self.e_dist = ctk.CTkEntry(left_p, placeholder_text="Jarak (m)"); self.e_dist.pack(pady=5, padx=20, fill="x")
        btn_trabas_f = ctk.CTkFrame(left_p, fg_color="transparent"); btn_trabas_f.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(btn_trabas_f, text="➕ TAMBAH DATA", command=self.tambah_data_live).pack(side="left", padx=5)
        ctk.CTkButton(btn_trabas_f, text="🗑️ PADAM BARIS", fg_color="#e74c3c", command=self.padam_data_trabas_terakhir).pack(side="left", padx=5)
        self.tree_in = ttk.Treeview(left_p, columns=("stn", "brg", "dist"), show="headings", height=10); self.tree_in.pack(pady=10, fill="both", expand=True)
        for c in ("stn", "brg", "dist"): self.tree_in.heading(c, text=c.upper())
        ctk.CTkButton(left_p, text="✅ PROSES DATA", fg_color="#27ae60", command=self.proses_manual).pack(pady=10, padx=20, fill="x")
        right_p = ctk.CTkFrame(self.win); right_p.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.fig_live, self.ax_live = plt.subplots(figsize=(4,4))
        self.canvas_live = FigureCanvasTkAgg(self.fig_live, master=right_p); self.canvas_live.get_tk_widget().pack(fill="both", expand=True)

    def tambah_koordinat_rujukan(self):
        s, e, n = self.e_ref_stn.get(), self.e_ref_e.get(), self.e_ref_n.get()
        if s and e and n: self.tree_coords.insert("", "end", values=(s, e, n))

    def tambah_data_live(self):
        try:
            stn, brg, dist = self.e_stn_range.get(), float(self.e_brg.get()), float(self.e_dist.get())
            s_f, s_t = stn.split("-")
            self.manual_data.append({"FROM": s_f, "TO": s_t, "BRG": brg, "DIST": dist})
            self.tree_in.insert("", "end", values=(stn, decimal_to_dms_str(brg), dist))
            self.auto_fill_stn(); self.update_live_plot()
        except: messagebox.showerror("Ralat", "Input tidak sah!")

    def padam_data_trabas_terakhir(self):
        if self.manual_data:
            self.manual_data.pop()
            items = self.tree_in.get_children()
            if items: self.tree_in.delete(items[-1])
            self.auto_fill_stn(); self.update_live_plot()

    def update_live_plot(self):
        self.ax_live.clear()
        if self.manual_data:
            ce, cn = 0.0, 0.0
            pts = [(ce, cn)]
            for d in self.manual_data:
                rad = np.radians(dmss_to_decimal(d['BRG']))
                ce += d['DIST'] * np.sin(rad); cn += d['DIST'] * np.cos(rad)
                pts.append((ce, cn))
            pts = np.array(pts); self.ax_live.plot(pts[:,0], pts[:,1], '-ro'); self.ax_live.set_aspect('equal')
        self.canvas_live.draw()

    def auto_fill_stn(self):
        self.e_stn_range.delete(0, 'end')
        last_to = self.manual_data[-1]["TO"] if self.manual_data else "1"
        try: next_to = str(int(last_to)+1); self.e_stn_range.insert(0, f"{last_to}-{next_to}")
        except: self.e_stn_range.insert(0, f"{last_to}-?")

    def proses_manual(self):
        if not self.manual_data: return
        all_refs = self.tree_coords.get_children()
        r_stn, t_e, t_n = (self.tree_coords.item(all_refs[0])['values']) if all_refs else ("", 0.0, 0.0)
        final_rows = [{"STN": self.manual_data[0]["FROM"], "E": 0.0, "N": 0.0, "BRG": "-", "DIST": 0.0, "LATIT": "-", "DIPAT": "-"}]
        ce, cn = 0.0, 0.0
        for d in self.manual_data:
            rad = np.radians(dmss_to_decimal(d['BRG']))
            latit = d['DIST'] * np.cos(rad)
            dipat = d['DIST'] * np.sin(rad)
            ce += dipat; cn += latit
            final_rows.append({"STN": d["TO"], "E": ce, "N": cn, "BRG": d["BRG"], "DIST": d["DIST"], "LATIT": latit, "DIPAT": dipat})
        
        if str(final_rows[-1]["STN"]) == str(final_rows[0]["STN"]):
            row_penutup = final_rows[-1]
            final_rows[0]["BRG"] = row_penutup["BRG"]
            final_rows[0]["DIST"] = row_penutup["DIST"]
            final_rows[0]["LATIT"] = row_penutup["LATIT"]
            final_rows[0]["DIPAT"] = row_penutup["DIPAT"]
            final_rows.pop() 
            
        if r_stn:
            de, dn = 0, 0
            for r in final_rows:
                if str(r["STN"]) == str(r_stn): 
                    de, dn = float(t_e) - r["E"], float(t_n) - r["N"]
                    break
            for r in final_rows: 
                r["E"] += de; r["N"] += dn
            
        self.df = pd.DataFrame(final_rows)
        if hasattr(self, 'win'): self.win.destroy()
        self.visualize()

    def export_dxf(self):
        if self.df is None: return
        path = filedialog.asksaveasfilename(defaultextension=".dxf", filetypes=[("DXF", "*.dxf")])
        if not path: return
        try:
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            x_vals, y_vals = self.df.E.values, self.df.N.values
            n_pts = len(self.df)
            pts = list(zip(x_vals, y_vals))
            
            min_e, max_e = np.min(x_vals), np.max(x_vals)
            min_n, max_n = np.min(y_vals), np.max(y_vals)
            base_scale = max(0.4, min(max_e - min_e, max_n - min_n) * 0.05)
            
            # Lukis Poligon Sempadan
            msp.add_lwpolyline(pts, dxfattribs={'closed': True, 'layer': 'SEMPADAN', 'color': 7})
            
            for i in range(n_pts):
                r = self.df.iloc[i]
                # Label Stesen
                msp.add_text(str(r.STN), dxfattribs={'height': base_scale*0.6, 'color': 2}).dxf.insert = (r.E + base_scale*0.2, r.N + base_scale*0.2)
                msp.add_circle((r.E, r.N), radius=base_scale*0.08)
                
                # Label Bearing & Jarak
                p1_idx = i
                p2_idx = (i + 1) % n_pts
                r_label = self.df.iloc[p2_idx]
                
                if r_label.BRG != "-":
                    p1 = np.array([x_vals[p1_idx], y_vals[p1_idx]])
                    p2 = np.array([x_vals[p2_idx], y_vals[p2_idx]])
                    mid_p = (p1 + p2) / 2
                    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                    angle = np.degrees(np.arctan2(dy, dx))
                    
                    if 90 < angle <= 270: angle -= 180
                    elif angle <= -90: angle += 180
                    
                    rad_normal = np.radians(angle + 90)
                    off_x = np.cos(rad_normal) * (base_scale * 0.5)
                    off_y = np.sin(rad_normal) * (base_scale * 0.5)
                    
                    pos_brg = mid_p + np.array([off_x, off_y])
                    msp.add_text(f"{decimal_to_dms_str(r_label.BRG)}", 
                                dxfattribs={'height': base_scale*0.45, 'rotation': angle, 'color': 1}
                                ).set_placement(pos_brg, align=ezdxf.enums.TextEntityAlignment.CENTER)
                    
                    pos_dist = mid_p - np.array([off_x, off_y])
                    msp.add_text(f"{r_label.DIST:.3f}m", 
                                dxfattribs={'height': base_scale*0.45, 'rotation': angle, 'color': 1}
                                ).set_placement(pos_dist, align=ezdxf.enums.TextEntityAlignment.CENTER)

            # --- TAMBAH: Label Luas & SKALA Tengah dalam DXF ---
            luas_m2 = kira_luas(x_vals, y_vals)
            skala_dxf = self.hitung_skala(x_vals, y_vals)
            center_pt = (np.mean(x_vals), np.mean(y_vals))
            txt_luas = (f"LUAS: {luas_m2:.2f} m2\\P"
                        f"({(luas_m2 * 0.000247105):.4f} EKAR)\\P"
                        f"SKALA: 1:{skala_dxf}")
            
            msp.add_mtext(txt_luas, dxfattribs={'char_height': base_scale*0.8, 'color': 3}).set_location(center_pt, attachment_point=ezdxf.enums.MTextEntityAlignment.MIDDLE_CENTER)
            
            doc.saveas(path)
            messagebox.showinfo("Berjaya", f"Fail DXF disimpan. (Skala 1:{skala_dxf})")
        except Exception as e: messagebox.showerror("Ralat", f"Gagal DXF: {e}")

    def export_qgis_csv(self):
        if self.df is not None: 
            path = filedialog.asksaveasfilename(defaultextension=".csv")
            if path: self.df.to_csv(path, index=False)

    def export_geojson(self):
        if self.df is None: return
        path = filedialog.asksaveasfilename(defaultextension=".geojson", filetypes=[("GeoJSON", "*.geojson")])
        if not path: return
        try:
            features = []
            coords_poly = [[float(r.E), float(r.N)] for _, r in self.df.iterrows()]
            coords_poly.append(coords_poly[0]) 
            poly_feature = {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [coords_poly]},
                "properties": {
                    "nama": "Lot Sempadan",
                    "luas_m2": round(kira_luas(self.df.E.values, self.df.N.values), 3),
                    "unit": "Meter Persegi"
                }
            }
            features.append(poly_feature)
            for _, r in self.df.iterrows():
                point_feature = {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(r.E), float(r.N)]},
                    "properties": {
                        "STN": str(r.STN),
                        "Easting": round(float(r.E), 4),
                        "Northing": round(float(r.N), 4),
                        "Bearing": decimal_to_dms_str(r.BRG),
                        "Jarak": f"{r.DIST:.3f} m"
                    }
                }
                features.append(point_feature)
            geojson_data = {"type": "FeatureCollection", "features": features}
            with open(path, 'w') as f: json.dump(geojson_data, f, indent=4)
            messagebox.showinfo("Berjaya", "Fail GeoJSON disimpan.")
        except Exception as e: messagebox.showerror("Ralat", f"Gagal GeoJSON: {e}")

    def reset_data(self):
        if messagebox.askyesno("Reset", "Padam semua?"): 
            self.manual_data = []
            self.df = None
            self.lbl_luas.configure(text="Luas: -")
            self.lbl_skala.configure(text="Skala: -")
            for w in self.display_frame.winfo_children(): w.destroy()

if __name__ == "__main__":
    App().mainloop()
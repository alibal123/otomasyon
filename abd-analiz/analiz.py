#!/usr/bin/env python3
"""
ABD günlük analiz PDF'i.

  python3 analiz.py hesapla [klasor]   -> veri/*.csv'den göstergeler, seviyeler, olası aralıklar ve
                                          önceki günün tahmin kontrolü; cikti/hesap.json
  python3 analiz.py pdf [klasor]       -> hesap.json + icerik.json (günün yorumları) -> cikti/ABD-Analiz-<tarih>.pdf
                                          ve tahminler/<tarih>.json (ertesi günün öz-kontrolü için)

Veri biçimi: veri/<SEMBOL>.csv  date,open,high,low,close,volume  (tarih "2026-10-07", "Oct 7, 2026" ya da "Oct 7 2026";
satır sırası önemli değil). Tamamlanmamış (gün içi) mum varsa veri/anlik.json'da {"SEMBOL": fiyat} olarak verilir,
CSV'ye konmaz.

Olası aralıklar tahmin değil, oynaklığa dayalı olasılık bantlarıdır: son 20 günün günlük oynaklığı (σ) ile
1 gün için ±1σ (~%68) ve ±2σ (~%95), 1 hafta için σ·√gün. Merkez çizgisi bugünkü fiyattır (yön varsayımı yok).
"""
import csv, json, math, os, sys
from datetime import datetime, timedelta

KLASOR = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(KLASOR, "veri")
CIKTI = os.path.join(KLASOR, "cikti")
TAHMIN = os.path.join(KLASOR, "tahminler")

DETAY = ["MRVL", "ARKG", "DY"]
PIYASA = ["SPY", "QQQ"]
FONLAR = ["SMH", "SOXX", "AIQ", "CIBR", "ARKQ", "ARKW", "ARKF", "BLOK", "URA", "GLD"]
AD = {"MRVL": "Marvell Technology", "ARKG": "ARK Genomic Revolution ETF", "DY": "Dycom Industries",
      "SPY": "S&P 500 (SPY)", "QQQ": "Nasdaq 100 (QQQ)", "SMH": "Yarı iletken (SMH)", "SOXX": "Yarı iletken (SOXX)",
      "AIQ": "Yapay zekâ (AIQ)", "CIBR": "Siber güvenlik (CIBR)", "ARKQ": "Otonom teknoloji (ARKQ)",
      "ARKW": "İnternet (ARKW)", "ARKF": "Fintek (ARKF)", "BLOK": "Blokzincir (BLOK)", "URA": "Uranyum (URA)",
      "GLD": "Altın (GLD)"}
AYLAR = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10,
         "Nov": 11, "Dec": 12}
TR_AY = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
# ABD borsa tatilleri (2026 sonu - 2027)
TATIL = {"2026-11-26", "2026-12-25", "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31",
         "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24"}


# =============================================================== veri
def tarih_coz(s):
    s = s.strip().replace(",", "")
    if s[:4].isdigit():
        return s[:10]
    p = s.split()
    return f"{int(p[2]):04d}-{AYLAR[p[0][:3]]:02d}-{int(p[1]):02d}"


def oku(sembol):
    rows = []
    with open(os.path.join(VERI, f"{sembol}.csv")) as f:
        for r in csv.DictReader(f):
            try:
                rows.append((tarih_coz(r["date"]), float(r["open"]), float(r["high"]), float(r["low"]),
                             float(r["close"]), float(r.get("volume") or 0)))
            except (ValueError, KeyError):
                continue
    rows = sorted({r[0]: r for r in rows}.values())
    m = {k: [r[i] for r in rows] for i, k in enumerate("tohlcv")}
    # tutarlılık: yüksek/düşük düzeltmesi (elle aktarılan verilerdeki küçük hatalara karşı)
    for i in range(len(m["c"])):
        m["h"][i] = max(m["h"][i], m["o"][i], m["c"][i])
        m["l"][i] = min(m["l"][i], m["o"][i], m["c"][i])
    return m


def is_gunleri(bas, n):
    out, t = [], datetime.strptime(bas, "%Y-%m-%d")
    while len(out) < n:
        t += timedelta(days=1)
        s = t.strftime("%Y-%m-%d")
        if t.weekday() < 5 and s not in TATIL:
            out.append(s)
    return out


# =============================================================== göstergeler
def sma(x, n):
    return [None if i < n - 1 else sum(x[i - n + 1:i + 1]) / n for i in range(len(x))]


def ema(x, n):
    out, k, e = [], 2 / (n + 1), None
    for v in x:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out


def rsi(c, n=14):
    out = [None] * len(c)
    if len(c) <= n:
        return out
    g = [max(0, c[i] - c[i - 1]) for i in range(1, len(c))]
    l = [max(0, c[i - 1] - c[i]) for i in range(1, len(c))]
    ag, al = sum(g[:n]) / n, sum(l[:n]) / n
    out[n] = 100 - 100 / (1 + ag / al) if al else 100
    for i in range(n + 1, len(c)):
        ag = (ag * (n - 1) + g[i - 1]) / n
        al = (al * (n - 1) + l[i - 1]) / n
        out[i] = 100 - 100 / (1 + ag / al) if al else 100
    return out


def atr(m, n=14):
    tr = [m["h"][0] - m["l"][0]] + [max(m["h"][i] - m["l"][i], abs(m["h"][i] - m["c"][i - 1]),
                                        abs(m["l"][i] - m["c"][i - 1])) for i in range(1, len(m["c"]))]
    out, a = [], None
    for i, v in enumerate(tr):
        a = v if a is None else (a * (n - 1) + v) / n
        out.append(a)
    return out


def oynaklik(c, n=20):
    r = [math.log(c[i] / c[i - 1]) for i in range(max(1, len(c) - n), len(c))]
    if len(r) < 5:
        return None
    ort = sum(r) / len(r)
    return math.sqrt(sum((x - ort) ** 2 for x in r) / (len(r) - 1))


def salinim_noktalari(m, pencere=2):
    """Yerel dip ve tepeler (destek/direnç adayları)."""
    h, l = m["h"], m["l"]
    tepe, dip = [], []
    for i in range(pencere, len(h) - pencere):
        if h[i] == max(h[i - pencere:i + pencere + 1]):
            tepe.append((m["t"][i], h[i]))
        if l[i] == min(l[i - pencere:i + pencere + 1]):
            dip.append((m["t"][i], l[i]))
    return tepe, dip


def seviyeler(m):
    c = m["c"][-1]
    H, L, C = m["h"][-1], m["l"][-1], m["c"][-1]
    P = (H + L + C) / 3
    gunluk = {"P": P, "R1": 2 * P - L, "S1": 2 * P - H, "R2": P + (H - L), "S2": P - (H - L)}
    Hw, Lw, Cw = max(m["h"][-5:]), min(m["l"][-5:]), m["c"][-1]
    Pw = (Hw + Lw + Cw) / 3
    haftalik = {"P": Pw, "R1": 2 * Pw - Lw, "S1": 2 * Pw - Hw, "R2": Pw + (Hw - Lw), "S2": Pw - (Hw - Lw)}
    tepe, dip = salinim_noktalari(m)
    ustler = sorted({round(v, 2) for _, v in tepe if v > c * 1.002})
    altlar = sorted({round(v, 2) for _, v in dip if v < c * 0.998}, reverse=True)
    return {"gunluk_pivot": gunluk, "haftalik_pivot": haftalik,
            "direnc": ustler[:3], "destek": altlar[:3],
            "zirve20": max(m["h"][-21:-1]) if len(m["h"]) > 21 else max(m["h"]),
            "dip20": min(m["l"][-21:-1]) if len(m["l"]) > 21 else min(m["l"]),
            "zirve_donem": max(m["h"]), "dip_donem": min(m["l"])}


def sinyaller(m, g):
    c = m["c"]
    i = len(c) - 1
    s = []
    e20, s50 = g["ema20"][i], g["sma50"][i]
    if s50:
        s.append(("Trend (EMA20 / SMA50)", "YUKARI" if e20 > s50 else "AŞAĞI",
                  f"EMA20 {e20:.2f} {'>' if e20 > s50 else '<'} SMA50 {s50:.2f}"))
    else:
        s.append(("Trend (EMA20 eğimi)", "YUKARI" if g["ema20"][i] > g["ema20"][i - 5] else "AŞAĞI",
                  f"EMA20 {e20:.2f}, 5 gün önce {g['ema20'][i-5]:.2f}"))
    z20 = max(m["h"][-21:-1])
    d10 = min(m["l"][-11:-1])
    if c[i] > z20:
        s.append(("Kırılım (20 günlük zirve)", "AL", f"kapanış {c[i]:.2f} > önceki 20 gün zirvesi {z20:.2f}"))
    elif c[i] < d10:
        s.append(("Kırılım (10 günlük dip)", "SAT", f"kapanış {c[i]:.2f} < önceki 10 gün dibi {d10:.2f}"))
    else:
        s.append(("Kırılım", "NÖTR", f"20 gün zirvesi {z20:.2f} · 10 gün dibi {d10:.2f} arasında"))
    r = g["rsi14"][i]
    if r is not None:
        durum = "AŞIRI ALIM" if r >= 70 else ("AŞIRI SATIM" if r <= 30 else "NÖTR")
        s.append(("RSI(14)", durum, f"{r:.0f}"))
    r2 = rsi(c, 2)[i]
    if r2 is not None:
        s.append(("RSI(2) kısa vade", "DÖNÜŞ ALIMI" if r2 < 10 else ("KISA VADE ŞİŞKİN" if r2 > 90 else "NÖTR"), f"{r2:.0f}"))
    m12, m26 = ema(c, 12), ema(c, 26)
    macd = [a - b for a, b in zip(m12, m26)]
    sig = ema(macd, 9)
    s.append(("MACD", "YUKARI" if macd[i] > sig[i] else "AŞAĞI",
              f"MACD {macd[i]:.2f} / sinyal {sig[i]:.2f}" + (" · yeni kesişim" if (macd[i] - sig[i]) * (macd[i-1] - sig[i-1]) < 0 else "")))
    ort_hacim = sum(m["v"][-21:-1]) / 20 if len(m["v"]) > 21 else None
    if ort_hacim:
        oran = m["v"][-1] / ort_hacim if ort_hacim else 0
        s.append(("Hacim", "YÜKSEK" if oran > 1.8 else ("DÜŞÜK" if oran < 0.6 else "NORMAL"), f"ortalamanın {oran:.1f} katı"))
    return s


def analiz_et(sembol, anlik=None):
    m = oku(sembol)
    c = m["c"]
    g = {"ema20": ema(c, 20), "sma20": sma(c, 20), "sma50": sma(c, 50), "rsi14": rsi(c), "atr14": atr(m)}
    s = oynaklik(c)
    son, tarih = c[-1], m["t"][-1]
    hafta = is_gunleri(tarih, 5)
    bant = []
    for k, t in enumerate(hafta, 1):
        sk = s * math.sqrt(k)
        bant.append({"tarih": t, "alt2": son * math.exp(-2 * sk), "alt1": son * math.exp(-sk),
                     "ust1": son * math.exp(sk), "ust2": son * math.exp(2 * sk)})
    sev = seviyeler(m)
    d = lambda n: c[-1] / c[-1 - n] - 1 if len(c) > n else None
    return {"sembol": sembol, "ad": AD.get(sembol, sembol), "tarih": tarih, "kapanis": son, "anlik": anlik,
            "d1": d(1), "d5": d(5), "d20": d(20), "sigma": s, "atr": g["atr14"][-1], "rsi14": g["rsi14"][-1],
            "ema20": g["ema20"][-1], "sma20": g["sma20"][-1], "sma50": g["sma50"][-1],
            "bant": bant, "seviyeler": sev, "sinyaller": sinyaller(m, g), "n": len(c),
            "_m": m, "_g": g}


# =============================================================== öz-kontrol
def onceki_tahmin(bugun):
    if not os.path.isdir(TAHMIN):
        return None
    dosyalar = sorted(f for f in os.listdir(TAHMIN) if f.endswith(".json") and f[:10] < bugun)
    return json.load(open(os.path.join(TAHMIN, dosyalar[-1]))) if dosyalar else None


def oz_kontrol(sonuclar, bugun):
    """Önceki raporların bantlarını gerçekleşen kapanışlarla karşılaştırır (son 10 rapor)."""
    if not os.path.isdir(TAHMIN):
        return {"satirlar": [], "ozet": None}
    dosyalar = sorted(f for f in os.listdir(TAHMIN) if f.endswith(".json") and f[:10] < bugun)[-10:]
    satirlar, toplam = [], {"n": 0, "bir": 0, "iki": 0, "yon": 0, "yon_n": 0}
    for f in dosyalar:
        eski = json.load(open(os.path.join(TAHMIN, f)))
        for sem, t in eski.get("semboller", {}).items():
            r = sonuclar.get(sem)
            if not r:
                continue
            m = r["_m"]
            kap = dict(zip(m["t"], m["c"]))
            for b in t["bant"]:
                if b["tarih"] not in kap:
                    continue
                gercek = kap[b["tarih"]]
                ic1 = b["alt1"] <= gercek <= b["ust1"]
                ic2 = b["alt2"] <= gercek <= b["ust2"]
                gun = t["bant"].index(b) + 1
                yon_dogru = None
                if t.get("yon") in ("yukari", "asagi"):
                    yon_dogru = (gercek > t["referans"]) == (t["yon"] == "yukari")
                    toplam["yon_n"] += 1
                    toplam["yon"] += int(yon_dogru)
                toplam["n"] += 1
                toplam["bir"] += int(ic1)
                toplam["iki"] += int(ic2)
                if f == dosyalar[-1] and gun == 1 or (f == dosyalar[-1] and sem in DETAY):
                    satirlar.append({"rapor": f[:10], "sembol": sem, "hedef_tarih": b["tarih"], "gun": gun,
                                     "referans": t["referans"], "alt1": b["alt1"], "ust1": b["ust1"],
                                     "alt2": b["alt2"], "ust2": b["ust2"], "gercek": gercek,
                                     "ic1": ic1, "ic2": ic2, "yon": t.get("yon"), "yon_dogru": yon_dogru})
    ozet = None
    if toplam["n"]:
        ozet = {"n": toplam["n"], "bir": toplam["bir"] / toplam["n"], "iki": toplam["iki"] / toplam["n"],
                "yon": toplam["yon"] / toplam["yon_n"] if toplam["yon_n"] else None, "yon_n": toplam["yon_n"]}
    return {"satirlar": satirlar, "ozet": ozet, "rapor_sayisi": len(dosyalar)}


# =============================================================== hesapla
def kmt_hesapla():
    os.makedirs(CIKTI, exist_ok=True)
    try:
        anlik = json.load(open(os.path.join(VERI, "anlik.json")))
    except Exception:
        anlik = {}
    sonuc = {}
    for s in PIYASA + DETAY + FONLAR:
        if os.path.exists(os.path.join(VERI, f"{s}.csv")):
            try:
                sonuc[s] = analiz_et(s, anlik.get(s))
            except Exception as e:
                print(f"{s}: hesaplanamadı ({e})")
    bugun = datetime.now().strftime("%Y-%m-%d")
    kontrol = oz_kontrol(sonuc, bugun)
    temiz = {s: {k: v for k, v in r.items() if not k.startswith("_")} for s, r in sonuc.items()}
    with open(os.path.join(CIKTI, "hesap.json"), "w") as f:
        json.dump({"olusturma": datetime.now().strftime("%Y-%m-%d %H:%M"), "semboller": temiz, "oz_kontrol": kontrol},
                  f, ensure_ascii=False, indent=1)
    for s, r in temiz.items():
        b1, bw = r["bant"][0], r["bant"][-1]
        sv = r["seviyeler"]
        print(f"{s:5} {r['tarih']} kap {r['kapanis']:.2f} d1 {r['d1']*100:+.1f}% d5 {r['d5']*100:+.1f}% "
              f"σ {r['sigma']*100:.2f}% | 1g68 {b1['alt1']:.2f}-{b1['ust1']:.2f} 1h68 {bw['alt1']:.2f}-{bw['ust1']:.2f} "
              f"| destek {sv['destek'][:2]} direnç {sv['direnc'][:2]} | RSI {r['rsi14'] or 0:.0f} | "
              + "; ".join(f"{a}:{b}" for a, b, _ in r["sinyaller"]))
    if kontrol["ozet"]:
        print("Öz-kontrol:", kontrol["ozet"])
    return sonuc


# =============================================================== grafikler
def grafikler(sonuc, klasor):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.edgecolor": "#9a9a95", "axes.labelcolor": "#33332f",
                         "xtick.color": "#55554f", "ytick.color": "#55554f"})
    MAV, GRI, YES, KIR, TUR = "#1f4e8c", "#8a8a85", "#2e7d32", "#c62828", "#e08a00"
    yollar = {}

    def eksen_tarih(ax, tarihler, adim):
        idx = list(range(0, len(tarihler), adim))
        ax.set_xticks(idx)
        ax.set_xticklabels([f"{int(t[8:])} {TR_AY[int(t[5:7])]}" for t in (tarihler[i] for i in idx)], rotation=0)

    def mumlar(ax, m, bas):
        for j, i in enumerate(range(bas, len(m["c"]))):
            o, h, l, c = m["o"][i], m["h"][i], m["l"][i], m["c"][i]
            renk = YES if c >= o else KIR
            ax.plot([j, j], [l, h], color=renk, lw=0.7)
            ax.add_patch(Rectangle((j - 0.32, min(o, c)), 0.64, max(abs(c - o), 1e-9), color=renk, lw=0))

    def koni(ax, r, x0, renk="#1f4e8c"):
        b = r["bant"]
        xs = [x0] + [x0 + k for k in range(1, len(b) + 1)]
        c = r["kapanis"]
        ax.fill_between(xs, [c] + [x["alt2"] for x in b], [c] + [x["ust2"] for x in b], color=renk, alpha=0.10, lw=0)
        ax.fill_between(xs, [c] + [x["alt1"] for x in b], [c] + [x["ust1"] for x in b], color=renk, alpha=0.22, lw=0)
        ax.plot(xs, [c] * len(xs), color=renk, lw=0.8, ls=":")
        ax.axvline(x0, color=GRI, lw=0.6, ls="--")
        return xs

    for s, r in sonuc.items():
        m, g = r["_m"], r["_g"]
        sv = r["seviyeler"]
        if s in DETAY:
            bas = max(0, len(m["c"]) - 45)
            gelecek = [x["tarih"] for x in r["bant"]]
            tarihler = m["t"][bas:] + gelecek
            fig = plt.figure(figsize=(7.4, 6.6))
            gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], hspace=0.42, wspace=0.22)
            # 1) geçmiş + 1 hafta
            ax = fig.add_subplot(gs[0, :])
            mumlar(ax, m, bas)
            n = len(m["c"]) - bas
            for ad_, seri, renk in (("EMA20", g["ema20"], TUR), ("SMA50", g["sma50"], "#6a1b9a")):
                ys = seri[bas:]
                if any(v is not None for v in ys):
                    ax.plot(range(n), ys, color=renk, lw=1, label=ad_)
            xs = koni(ax, r, n - 1)
            for v in sv["destek"][:2]:
                ax.axhline(v, color=YES, lw=0.7, ls="--", alpha=0.8)
                ax.text(len(tarihler) - 0.5, v, f" destek {v:.2f}", color=YES, va="center", fontsize=6.5)
            for v in sv["direnc"][:2]:
                ax.axhline(v, color=KIR, lw=0.7, ls="--", alpha=0.8)
                ax.text(len(tarihler) - 0.5, v, f" direnç {v:.2f}", color=KIR, va="center", fontsize=6.5)
            eksen_tarih(ax, tarihler, 7)
            ax.set_xlim(-1, len(tarihler) + 6)
            ax.set_title(f"{s} · geçmiş {n} işlem günü + önümüzdeki 1 hafta olası aralık", loc="left", fontsize=9, fontweight="bold")
            ax.legend(loc="upper left", fontsize=6.5, frameon=False)
            ax.grid(axis="y", color="#e6e6e2", lw=0.6)
            # 2) yakın görünüm: son 10 gün + 1 gün
            ax2 = fig.add_subplot(gs[1, 0])
            b2 = len(m["c"]) - 10
            mumlar(ax2, m, b2)
            b = r["bant"][0]
            x1 = 10
            ax2.add_patch(Rectangle((x1 - 0.4, b["alt2"]), 0.8, b["ust2"] - b["alt2"], color=MAV, alpha=0.10, lw=0))
            ax2.add_patch(Rectangle((x1 - 0.4, b["alt1"]), 0.8, b["ust1"] - b["alt1"], color=MAV, alpha=0.25, lw=0))
            gp = sv["gunluk_pivot"]
            for k, renk in (("R2", KIR), ("R1", KIR), ("P", GRI), ("S1", YES), ("S2", YES)):
                ax2.axhline(gp[k], color=renk, lw=0.6, ls=":" if k in ("R2", "S2") else "--", alpha=0.9)
                ax2.text(11.5, gp[k], f" {k} {gp[k]:.2f}", color=renk, va="center", fontsize=6.3)
            ax2.axvline(9.5, color=GRI, lw=0.6, ls="--")
            eksen_tarih(ax2, m["t"][b2:] + [b["tarih"]], 3)
            ax2.set_xlim(-1, 14.5)
            ax2.set_title(f"Önümüzdeki 1 gün ({int(b['tarih'][8:])} {TR_AY[int(b['tarih'][5:7])]})", loc="left", fontsize=8.5, fontweight="bold")
            ax2.grid(axis="y", color="#e6e6e2", lw=0.6)
            # 3) 1 hafta
            ax3 = fig.add_subplot(gs[1, 1])
            b3 = len(m["c"]) - 10
            ax3.plot(range(10), m["c"][b3:], color=MAV, lw=1.4)
            koni(ax3, r, 9)
            hp = sv["haftalik_pivot"]
            for k, renk in (("R1", KIR), ("P", GRI), ("S1", YES)):
                ax3.axhline(hp[k], color=renk, lw=0.6, ls="--")
                ax3.text(14.6, hp[k], f" {k} {hp[k]:.2f}", color=renk, va="center", fontsize=6.3)
            son = r["bant"][-1]
            for k in ("alt1", "ust1"):
                ax3.annotate(f"{son[k]:.2f}", (14, son[k]), xytext=(2, 0), textcoords="offset points", fontsize=6, color=MAV, va="center")
            eksen_tarih(ax3, m["t"][b3:] + gelecek, 3)
            ax3.set_xlim(-0.5, 18.5)
            ax3.set_title("Önümüzdeki 1 hafta (5 işlem günü)", loc="left", fontsize=8.5, fontweight="bold")
            ax3.grid(axis="y", color="#e6e6e2", lw=0.6)
            fig.text(0.01, 0.005, "Koyu bant ≈ %68, açık bant ≈ %95 olasılık aralığı (son 20 günün oynaklığı). Merkez çizgisi yön tahmini değildir.",
                     fontsize=6.3, color="#55554f")
            yol = os.path.join(klasor, f"g_{s}.png")
            fig.savefig(yol, dpi=170, bbox_inches="tight")
            plt.close(fig)
            yollar[s] = yol
    # piyasa + fonlar: küçük grafikler
    kucuk = [s for s in PIYASA + FONLAR if s in sonuc]
    for grup, ad in ((PIYASA, "piyasa"), (FONLAR, "fonlar")):
        semboller = [s for s in grup if s in sonuc]
        if not semboller:
            continue
        sutun = 2 if ad == "piyasa" else 3
        satir = math.ceil(len(semboller) / sutun)
        fig, axs = plt.subplots(satir, sutun, figsize=(7.4 if sutun == 2 else 9.6, 2.25 * satir), squeeze=False)
        for k, s in enumerate(semboller):
            r = sonuc[s]
            m = r["_m"]
            ax = axs[k // sutun][k % sutun]
            bas = max(0, len(m["c"]) - 30)
            n = len(m["c"]) - bas
            ax.plot(range(n), m["c"][bas:], color=MAV, lw=1.3)
            ema20 = r["_g"]["ema20"][bas:]
            ax.plot(range(n), ema20, color=TUR, lw=0.8)
            koni(ax, r, n - 1)
            b = r["bant"][0]
            ax.plot([n, n], [b["alt1"], b["ust1"]], color=MAV, lw=3, alpha=0.6, solid_capstyle="butt")
            gelecek = [x["tarih"] for x in r["bant"]]
            eksen_tarih(ax, m["t"][bas:] + gelecek, 8)
            ax.set_xlim(-1, n + 6)
            bitis = r["tarih"]
            ax.set_title(f"{AD.get(s, s)} · {r['kapanis']:.2f} ({r['d1']*100:+.1f}%)", loc="left", fontsize=8, fontweight="bold")
            ax.text(0.99, 0.03, f"1 gün %68: {b['alt1']:.2f}–{b['ust1']:.2f}\n1 hafta %68: {r['bant'][-1]['alt1']:.2f}–{r['bant'][-1]['ust1']:.2f}",
                    transform=ax.transAxes, ha="right", va="bottom", fontsize=6.2, color="#33332f",
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#dcdcd7", lw=0.5))
            ax.grid(axis="y", color="#e6e6e2", lw=0.6)
        for k in range(len(semboller), satir * sutun):
            axs[k // sutun][k % sutun].axis("off")
        fig.tight_layout()
        yol = os.path.join(klasor, f"g_{ad}.png")
        fig.savefig(yol, dpi=170, bbox_inches="tight")
        plt.close(fig)
        yollar[ad] = yol
    return yollar


# =============================================================== PDF
def kmt_pdf():
    sonuc = kmt_hesapla()
    hesap = json.load(open(os.path.join(CIKTI, "hesap.json")))
    icerik = json.load(open(os.path.join(KLASOR, "icerik.json")))
    tarih = icerik.get("tarih") or datetime.now().strftime("%Y-%m-%d")
    yollar = grafikler(sonuc, CIKTI)

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)
    from xml.sax.saxutils import escape

    fdir = "/usr/share/fonts/truetype/dejavu/"
    pdfmetrics.registerFont(TTFont("DV", fdir + "DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DVB", fdir + "DejaVuSans-Bold.ttf"))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")
    MAV = colors.HexColor("#1f4e8c")
    st = {
        "baslik": ParagraphStyle("b", fontName="DVB", fontSize=17, leading=21, textColor=MAV, spaceAfter=2),
        "alt": ParagraphStyle("a", fontName="DV", fontSize=8.5, leading=11, textColor=colors.HexColor("#55554f")),
        "h1": ParagraphStyle("h1", fontName="DVB", fontSize=12.5, leading=16, textColor=MAV, spaceBefore=8, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName="DVB", fontSize=10, leading=13, spaceBefore=6, spaceAfter=2),
        "p": ParagraphStyle("p", fontName="DV", fontSize=8.6, leading=12.2, spaceAfter=3),
        "li": ParagraphStyle("li", fontName="DV", fontSize=8.6, leading=12, leftIndent=10, bulletIndent=2, spaceAfter=1.5),
        "k": ParagraphStyle("k", fontName="DV", fontSize=7, leading=9, textColor=colors.HexColor("#55554f")),
        "tb": ParagraphStyle("tb", fontName="DV", fontSize=7.4, leading=9.2),
        "tbb": ParagraphStyle("tbb", fontName="DVB", fontSize=7.4, leading=9.2),
    }

    def P(t, s="p"):
        return Paragraph(t, st[s])

    def maddeler(liste):
        return [Paragraph(x, st["li"], bulletText="•") for x in liste]

    def tablo(veri, gen, baslik=True, renkler=None):
        t = Table([[c if not isinstance(c, str) else Paragraph(c, st["tbb" if (baslik and i == 0) else "tb"])
                    for c in row] for i, row in enumerate(veri)], colWidths=gen, repeatRows=1 if baslik else 0)
        stil = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9d9d4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2)]
        if baslik:
            stil.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f8")))
        stil += renkler or []
        t.setStyle(TableStyle(stil))
        return t

    def yz(x, n=1):
        return "–" if x is None else f"{x*100:+.{n}f}%"

    def f2(x):
        return "–" if x is None else f"{x:,.2f}"

    H = hesap["semboller"]
    hikaye = []
    tr_tarih = f"{int(tarih[8:])} {TR_AY[int(tarih[5:7])]} {tarih[:4]}"
    hikaye += [P(f"ABD Piyasa ve Hisse Analizi · {tr_tarih}", "baslik"),
               P(escape(icerik.get("alt_baslik", "")) + " · Hazırlanma: " + hesap["olusturma"] + " (Türkiye)", "alt"),
               Spacer(1, 6)]
    # özet kutusu
    ozet = icerik.get("ozet", [])
    if ozet:
        kutu = Table([[[P("<b>Bugünün özeti</b>", "h2")] + maddeler(ozet)]], colWidths=[175 * mm])
        kutu.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6fa")),
                                  ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9d3e3")),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
        hikaye += [kutu, Spacer(1, 6)]

    # öz-kontrol
    ok = hesap.get("oz_kontrol") or {}
    hikaye.append(P("1. Dünkü tahminlerin kontrolü", "h1"))
    if ok.get("satirlar"):
        veri = [["Sembol", "Rapor", "Hedef gün", "Referans", "%68 aralık", "%95 aralık", "Gerçekleşen", "Sonuç"]]
        renk = []
        for k, x in enumerate(ok["satirlar"], 1):
            sonuc_ = "%68 içinde" if x["ic1"] else ("%95 içinde" if x["ic2"] else "aralık DIŞI")
            veri.append([x["sembol"], x["rapor"][5:], f"{x['hedef_tarih'][5:]} (+{x['gun']}g)", f2(x["referans"]),
                         f"{f2(x['alt1'])}–{f2(x['ust1'])}", f"{f2(x['alt2'])}–{f2(x['ust2'])}", f2(x["gercek"]), sonuc_])
            renk.append(("TEXTCOLOR", (7, k), (7, k), colors.HexColor("#2e7d32" if x["ic1"] else ("#e08a00" if x["ic2"] else "#c62828"))))
        hikaye.append(tablo(veri, [16 * mm, 15 * mm, 22 * mm, 20 * mm, 30 * mm, 30 * mm, 22 * mm, 25 * mm], renkler=renk))
        o = ok.get("ozet")
        if o:
            hikaye.append(P(f"Son {ok.get('rapor_sayisi')} raporda {o['n']} kontrol: kapanışların "
                            f"<b>%{o['bir']*100:.0f}</b>'i %68 aralığında (hedef ~%68), <b>%{o['iki']*100:.0f}</b>'i %95 aralığında (hedef ~%95)."
                            + (f" Yön beklentisi tutma oranı: %{o['yon']*100:.0f} ({o['yon_n']} kontrol)." if o.get("yon") is not None else ""), "k"))
    for x in icerik.get("oz_kontrol_yorum", []):
        hikaye.append(P(x))
    if not ok.get("satirlar") and not icerik.get("oz_kontrol_yorum"):
        hikaye.append(P("Bu ilk rapor; bugünün aralıkları kaydedildi, yarın gerçekleşen fiyatlarla karşılaştırılacak."))

    # piyasa
    hikaye.append(P("2. Amerikan borsasının genel durumu", "h1"))
    for x in icerik.get("piyasa", []):
        hikaye.append(P(x))
    if icerik.get("piyasa_tablo"):
        hikaye.append(tablo(icerik["piyasa_tablo"], [45 * mm, 35 * mm, 100 * mm]))
        hikaye.append(Spacer(1, 4))
    if "piyasa" in yollar:
        hikaye.append(Image(yollar["piyasa"], width=175 * mm, height=175 * mm * 0.31))
    hikaye.append(P("Olası senaryolar (önümüzdeki 1 hafta)", "h2"))
    if icerik.get("senaryolar"):
        veri = [["Senaryo", "Olasılık (yorum)", "Tetikleyici", "S&P 500 / SPY için anlamı"]] + icerik["senaryolar"]
        hikaye.append(tablo(veri, [28 * mm, 24 * mm, 70 * mm, 58 * mm]))
    if icerik.get("takvim"):
        hikaye.append(P("Takvim", "h2"))
        hikaye += maddeler(icerik["takvim"])

    # detaylı hisseler
    for s in DETAY:
        if s not in H:
            continue
        r, d = H[s], icerik.get("hisseler", {}).get(s, {})
        hikaye.append(PageBreak())
        hikaye.append(P(f"{3 + DETAY.index(s)}. {s} · {AD[s]}", "h1"))
        anlik = f" · anlık {f2(r['anlik'])}" if r.get("anlik") else ""
        hikaye.append(P(f"Son kapanış <b>{f2(r['kapanis'])} $</b> ({r['tarih']}){anlik} · gün {yz(r['d1'])} · hafta {yz(r['d5'])} · "
                        f"ay {yz(r['d20'])} · günlük oynaklık %{r['sigma']*100:.2f} · ATR {f2(r['atr'])} · RSI(14) {r['rsi14']:.0f}", "alt"))
        if s in yollar:
            hikaye.append(Image(yollar[s], width=175 * mm, height=175 * mm * 0.89))
        sv = r["seviyeler"]
        b1, bw = r["bant"][0], r["bant"][-1]
        gp, hp = sv["gunluk_pivot"], sv["haftalik_pivot"]
        veri = [["", "1 gün (" + b1["tarih"][5:] + ")", "1 hafta (" + bw["tarih"][5:] + ")"],
                ["%68 olası aralık", f"{f2(b1['alt1'])} – {f2(b1['ust1'])}", f"{f2(bw['alt1'])} – {f2(bw['ust1'])}"],
                ["%95 olası aralık", f"{f2(b1['alt2'])} – {f2(b1['ust2'])}", f"{f2(bw['alt2'])} – {f2(bw['ust2'])}"],
                ["Pivot (P)", f2(gp["P"]), f2(hp["P"])],
                ["Direnç R1 / R2", f"{f2(gp['R1'])} / {f2(gp['R2'])}", f"{f2(hp['R1'])} / {f2(hp['R2'])}"],
                ["Destek S1 / S2", f"{f2(gp['S1'])} / {f2(gp['S2'])}", f"{f2(hp['S1'])} / {f2(hp['S2'])}"],
                ["Salınım destekleri", ", ".join(f2(v) for v in sv["destek"]) or "–", f"20 gün dibi {f2(sv['dip20'])}"],
                ["Salınım dirençleri", ", ".join(f2(v) for v in sv["direnc"]) or "–", f"20 gün zirvesi {f2(sv['zirve20'])}"]]
        sol = tablo(veri, [30 * mm, 30 * mm, 30 * mm])
        sg = [["Gösterge", "Durum", "Ayrıntı"]] + [[a, b, c] for a, b, c in r["sinyaller"]]
        renk = []
        for k, (_, b, _) in enumerate(r["sinyaller"], 1):
            if b in ("YUKARI", "AL", "DÖNÜŞ ALIMI"):
                renk.append(("TEXTCOLOR", (1, k), (1, k), colors.HexColor("#2e7d32")))
            elif b in ("AŞAĞI", "SAT", "AŞIRI ALIM", "KISA VADE ŞİŞKİN"):
                renk.append(("TEXTCOLOR", (1, k), (1, k), colors.HexColor("#c62828")))
        sag = tablo(sg, [27 * mm, 22 * mm, 37 * mm], renkler=renk)
        hikaye.append(Table([[sol, sag]], colWidths=[92 * mm, 88 * mm],
                            style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        if d.get("al_sat"):
            hikaye.append(P("Al-sat seviyeleri (kurallara göre, tavsiye değildir)", "h2"))
            hikaye.append(tablo([["Seviye", "Fiyat", "Mantığı"]] + d["al_sat"], [42 * mm, 28 * mm, 110 * mm]))
        for baslik, anahtar in (("Teknik görünüm", "teknik"), ("Haberler ve temel tablo", "temel"),
                                ("Davranışsal sinyaller", "davranis"), ("Senaryolar", "senaryo"), ("Riskler", "risk")):
            if d.get(anahtar):
                hikaye.append(P(baslik, "h2"))
                hikaye += maddeler(d[anahtar])

    # fonlar
    hikaye.append(PageBreak())
    hikaye.append(P(f"{3 + len(DETAY)}. Yatırım yapılabilecek fonlar hakkında bilgi", "h1"))
    for x in icerik.get("fonlar_giris", []):
        hikaye.append(P(x))
    veri = [["Fon", "Son", "Gün", "Hafta", "Ay", "RSI", "Trend", "1 gün %68", "1 hafta %68", "Not"]]
    for s in FONLAR:
        if s not in H:
            continue
        r = H[s]
        trend = next((b for a, b, _ in r["sinyaller"] if a.startswith("Trend")), "–")
        veri.append([s, f2(r["kapanis"]), yz(r["d1"]), yz(r["d5"]), yz(r["d20"]), f"{r['rsi14']:.0f}" if r["rsi14"] else "–",
                     trend, f"{f2(r['bant'][0]['alt1'])}–{f2(r['bant'][0]['ust1'])}",
                     f"{f2(r['bant'][-1]['alt1'])}–{f2(r['bant'][-1]['ust1'])}",
                     escape(icerik.get("fon_notlari", {}).get(s, "")) + (f" (veri {r['tarih'][5:]})" if r["tarih"] < max(x["tarih"] for x in H.values()) else "")])
    hikaye.append(tablo(veri, [13 * mm, 14 * mm, 13 * mm, 13 * mm, 13 * mm, 9 * mm, 16 * mm, 22 * mm, 22 * mm, 40 * mm]))
    hikaye.append(Spacer(1, 4))
    if "fonlar" in yollar:
        from reportlab.lib.utils import ImageReader
        w, h = ImageReader(yollar["fonlar"]).getSize()
        yuk = min(235 * mm, 175 * mm * h / w)
        hikaye.append(Image(yollar["fonlar"], width=yuk * w / h, height=yuk))
    for x in icerik.get("fonlar", []):
        hikaye.append(P(x))

    # yöntem + kaynaklar
    hikaye.append(P("Yöntem", "h1"))
    hikaye += maddeler([
        "Olası aralıklar: son 20 işlem gününün günlük oynaklığı (σ) ile hesaplanır. 1 gün: fiyat × e<super>±σ</super> (%68) ve × e<super>±2σ</super> (%95); "
        "1 hafta: σ·√gün. Merkez çizgisi bugünkü fiyattır, yön tahmini içermez. Fiyatın bu aralıkların dışına çıkması beklenen bir durumdur (%95 aralığı için yaklaşık her 20 günde bir).",
        "Pivotlar: klasik pivot (P = (Y+D+K)/3, R1 = 2P−D, S1 = 2P−Y, R2 = P+(Y−D), S2 = P−(Y−D)); günlük için son gün, haftalık için son 5 gün.",
        "Destek/direnç: son dönemin yerel dip ve tepeleri. Sinyaller: EMA20/SMA50 trendi, 20 gün zirve / 10 gün dip kırılımı, RSI(14), RSI(2), MACD(12,26,9), hacim.",
        "Öz-kontrol: her raporun aralıkları kaydedilir; sonraki raporda gerçekleşen kapanışlarla karşılaştırılır ve tutma oranı yazılır.",
    ])
    if icerik.get("kaynaklar"):
        hikaye.append(P("Kaynaklar", "h1"))
        for ad, url in icerik["kaynaklar"]:
            hikaye.append(Paragraph(f'<link href="{escape(url)}" color="#1f4e8c">{escape(ad)}</link>', st["k"]))
    hikaye.append(Spacer(1, 6))
    hikaye.append(P("Bu rapor bilgi amaçlıdır; yatırım tavsiyesi değildir. Seviyeler ve aralıklar geçmiş fiyatlardan hesaplanan "
                    "olasılıklardır, gelecekteki fiyatı garanti etmez. Yatırım kararı ve sorumluluğu size aittir.", "k"))

    def sayfa_alti(c, doc):
        c.saveState()
        c.setFont("DV", 7)
        c.setFillColor(colors.HexColor("#8a8a85"))
        c.drawString(15 * mm, 9 * mm, f"ABD Piyasa ve Hisse Analizi · {tr_tarih} · yatırım tavsiyesi değildir")
        c.drawRightString(195 * mm, 9 * mm, f"{doc.page}")
        c.restoreState()

    yol = os.path.join(CIKTI, f"ABD-Analiz-{tarih}.pdf")
    doc = SimpleDocTemplate(yol, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm,
                            bottomMargin=15 * mm, title=f"ABD Piyasa ve Hisse Analizi {tarih}", author="Claude")
    doc.build(hikaye, onFirstPage=sayfa_alti, onLaterPages=sayfa_alti)

    # tahmin kaydı (öz-kontrol için)
    os.makedirs(TAHMIN, exist_ok=True)
    kayit = {"tarih": tarih, "olusturma": hesap["olusturma"], "semboller": {}}
    for s, r in H.items():
        kayit["semboller"][s] = {"referans": r["kapanis"], "referans_tarih": r["tarih"], "bant": r["bant"],
                                 "yon": (icerik.get("hisseler", {}).get(s, {}) or {}).get("yon")}
    with open(os.path.join(TAHMIN, f"{tarih}.json"), "w") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=1)
    print("PDF:", yol)
    return yol


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("hesapla", "pdf"):
        print(__doc__)
    elif sys.argv[1] == "hesapla":
        kmt_hesapla()
    else:
        kmt_pdf()

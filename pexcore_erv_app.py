"""
PEXCORE ERV Calculator — Streamlit Web App
Chạy: streamlit run pexcore_erv_app.py
Truy cập từ điện thoại: http://<IP_máy_tính>:8501
"""

import streamlit as st
import math
import json
import os
from datetime import datetime
import io

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PEXCORE ERV Calculator",
    page_icon="💨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── HELPERS ────────────────────────────────────────────────────────────────
def safe_float(v, default=0.0):
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return default

def money(v):
    return f"{float(v):,.0f}"

def avg_range_str(v, default=0.0):
    s = str(v)
    try:
        if "-" in s:
            a, b = s.split("-", 1)
            return (float(a) + float(b)) / 2.0
        return float(s)
    except Exception:
        return float(default)

# ─── CATALOG ────────────────────────────────────────────────────────────────
CENTRAL_ERV_CATALOG = [
    {"id":"CFA150C",  "flow":150,  "esp":95,  "noise":29, "power":58,  "temp_eff":"80-84", "enthalpy_eff_cooling":"71-79", "enthalpy_eff_heating":"73-79", "brand":"HOLTOP", "weight_kg":20,  "suitable_area_m2":"30-60",   "tropical_derating":0.97, "filter_dp_f7":45},
    {"id":"CFA250C",  "flow":250,  "esp":85,  "noise":28, "power":62,  "temp_eff":"79-86", "enthalpy_eff_cooling":"68-83", "enthalpy_eff_heating":"70-83", "brand":"HOLTOP", "weight_kg":23,  "suitable_area_m2":"60-90",   "tropical_derating":0.97, "filter_dp_f7":52},
    {"id":"CFA350C",  "flow":350,  "esp":160, "noise":32, "power":140, "temp_eff":"80-89", "enthalpy_eff_cooling":"71-82", "enthalpy_eff_heating":"72-84", "brand":"HOLTOP", "weight_kg":30,  "suitable_area_m2":"90-130",  "tropical_derating":0.97, "filter_dp_f7":58},
    {"id":"CFA500C",  "flow":500,  "esp":120, "noise":34, "power":165, "temp_eff":"78-87", "enthalpy_eff_cooling":"67-82", "enthalpy_eff_heating":"69-83", "brand":"HOLTOP", "weight_kg":33,  "suitable_area_m2":"130-170", "tropical_derating":0.97, "filter_dp_f7":65},
    {"id":"CFA650C",  "flow":650,  "esp":120, "noise":35, "power":252, "temp_eff":"77-86", "enthalpy_eff_cooling":"66-81", "enthalpy_eff_heating":"69-82", "brand":"HOLTOP", "weight_kg":38,  "suitable_area_m2":"170-220", "tropical_derating":0.96, "filter_dp_f7":72},
    {"id":"CFA800C",  "flow":800,  "esp":150, "noise":35, "power":335, "temp_eff":"79-85", "enthalpy_eff_cooling":"70-81", "enthalpy_eff_heating":"71-82", "brand":"HOLTOP", "weight_kg":48,  "suitable_area_m2":"220-300", "tropical_derating":0.96, "filter_dp_f7":78},
    {"id":"CFA1000C", "flow":1000, "esp":170, "noise":37, "power":420, "temp_eff":"80-90", "enthalpy_eff_cooling":"71-86", "enthalpy_eff_heating":"73-87", "brand":"HOLTOP", "weight_kg":54,  "suitable_area_m2":"300-400", "tropical_derating":0.96, "filter_dp_f7":85},
    {"id":"CFA1500C", "flow":1500, "esp":175, "noise":39, "power":670, "temp_eff":"80-85", "enthalpy_eff_cooling":"71-81", "enthalpy_eff_heating":"72-82", "brand":"HOLTOP", "weight_kg":105, "suitable_area_m2":"400-600", "tropical_derating":0.95, "filter_dp_f7":95},
    {"id":"CFA2000C", "flow":2000, "esp":150, "noise":40, "power":850, "temp_eff":"80-90", "enthalpy_eff_cooling":"71-86", "enthalpy_eff_heating":"73-87", "brand":"HOLTOP", "weight_kg":117, "suitable_area_m2":"600-800", "tropical_derating":0.95, "filter_dp_f7":108},
]

ERV_PRICES = {
    "CFA150C":28500000, "CFA250C":32500000, "CFA350C":37800000,
    "CFA500C":46500000, "CFA650C":52800000, "CFA800C":59500000,
    "CFA1000C":72000000,"CFA1500C":98000000,"CFA2000C":125000000,
}

# ─── CORE ENGINE ────────────────────────────────────────────────────────────
def compute_design(inp):
    area       = inp["area"]
    height     = inp["height"]
    rooms      = max(1, inp["rooms"])
    candidates = esp_ok or nom_ok or flow_ok or [CENTRAL_ERV_CATALOG[-1]]

    hot_humid_dh = 28.0
    rho = 1.2

    all_eff = [
        0.55 * avg_range_str(m.get("enthalpy_eff_cooling","70"),70)
        + 0.25 * avg_range_str(m.get("enthalpy_eff_heating","72"),72)
        + 0.20 * avg_range_str(m.get("temp_eff","80"),80)
        for m in candidates
    ]
    min_eff = min(all_eff); max_eff = max(all_eff)
    min_pwr = min(m["power"] for m in candidates)
    max_pwr = max(m["power"] for m in candidates)
    min_noise = min(m["noise"] for m in candidates)
    max_noise = max(m["noise"] for m in candidates)

    W_LOADING=0.34; W_ESP=0.24; W_RECOVERY=0.18; W_EFF=0.12; W_POWER=0.07; W_NOISE=0.05

    results = []
    for m in candidates:
        lr     = required_flow / m["flow"] if m["flow"] else 999
        ec_avg = avg_range_str(m.get("enthalpy_eff_cooling","70"),70)
        eh_avg = avg_range_str(m.get("enthalpy_eff_heating","72"),72)
        t_avg  = avg_range_str(m.get("temp_eff","80"),80)
        trop   = m.get("tropical_derating", 0.97)
        rec_kw = rho * (required_flow/3600.0) * hot_humid_dh * (ec_avg * trop / 100.0)
        rpw    = rec_kw * 1000.0 / max(1.0, m["power"])

        if lr > 1.0:
            ls = max(0.0, 60.0 - (lr-1.0)*100.0*4.0)
        else:
            ls = max(0.0, 100.0 - abs(lr - loading_target)*200.0)

        es = min(100, 80 + min(20,(m["esp"]-required_esp)*0.6)) if m["esp"]>=required_esp else max(0, 90-(required_esp-m["esp"])*2.8)
        ps = 100.0*(max_pwr-m["power"])/(max_pwr-min_pwr) if max_pwr>min_pwr else 100.0
        ns = 100.0*(max_noise-m["noise"])/(max_noise-min_noise) if max_noise>min_noise else 100.0
        rs = min(100.0, rpw*12.0)
        raw_eff = 0.55*ec_avg + 0.25*eh_avg + 0.20*t_avg
        ef = 100.0*(raw_eff-min_eff)/(max_eff-min_eff) if max_eff>min_eff else 100.0
        gap = max(0.0,(m["flow"]-required_nom)/required_nom) if required_nom else 0.0
        penalty = min(24.0, gap*85.0)
        score = ls*W_LOADING + es*W_ESP + rs*W_RECOVERY + ef*W_EFF + ps*W_POWER + ns*W_NOISE - penalty

        results.append({
            "model": m, "score": score,
            "loading_pct": round(lr*100, 1),
            "recovery_kw": round(rec_kw, 2),
            "esp_ok": m["esp"] >= min_esp,
        })

    results.sort(key=lambda x: -x["score"])
    best = results[0]

    # auto resize
    tl = loading_target
    if best["loading_pct"] < (tl-0.20)*100:
        smaller = [r for r in results if r["model"]["flow"] < best["model"]["flow"]
                   and r["model"]["flow"] >= required_flow]
        if smaller:
            best = sorted(smaller, key=lambda x: -x["score"])[0]
    elif best["loading_pct"] > (tl+0.10)*100:
        larger = [r for r in results if r["model"]["flow"] > best["model"]["flow"]]
        if larger:
            best = sorted(larger, key=lambda x: -x["score"])[0]

    return best, results[:5]

def compute_savings(design_flow, model, cop=3.5, hours_year=2600, tariff=2200):
    rho = 1.2; dh = 28.0
    ec_avg = avg_range_str(model.get("enthalpy_eff_cooling","75"), 75)
    trop   = model.get("tropical_derating", 0.97)
    eff    = ec_avg * trop / 100.0
    q_saved_kw  = rho * (design_flow/3600.0) * dh * eff
    w_saved_kw  = q_saved_kw / cop
    kwh_year    = w_saved_kw * hours_year
    vnd_year    = kwh_year * tariff
    return {
        "q_saved_kw": round(q_saved_kw, 2),
        "w_saved_kw": round(w_saved_kw, 3),
        "kwh_year": round(kwh_year, 0),
        "vnd_year_m": round(vnd_year/1_000_000, 1),
    }

# ─── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main .block-container { padding-top: 1rem; padding-bottom: 2rem; }
  .metric-card {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 14px 16px; margin-bottom: 8px;
  }
  .metric-card .label { font-size: 11px; color: #64748b; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.05em; }
  .metric-card .value { font-size: 22px; font-weight: 700; color: #0f172a; }
  .metric-card .sub { font-size: 11px; color: #94a3b8; margin-top: 2px; }
  .model-badge {
    background: #0f172a; color: white; border-radius: 10px;
    padding: 16px 20px; margin: 8px 0;
  }
  .model-badge .name { font-size: 24px; font-weight: 800; color: #f97316; }
  .model-badge .sub  { font-size: 12px; color: #94a3b8; }
  .recommend-tag {
    background: #16a34a; color: white; font-size: 11px; font-weight: 700;
    padding: 3px 10px; border-radius: 20px; display: inline-block;
  }
  .warn-tag {
    background: #f97316; color: white; font-size: 11px; font-weight: 700;
    padding: 3px 10px; border-radius: 20px; display: inline-block;
  }
  .section-header {
    background: #0f172a; color: white; padding: 8px 14px;
    border-radius: 8px; font-weight: 700; font-size: 13px;
    margin: 16px 0 8px 0;
  }
  .stTabs [data-baseweb="tab"] { font-size: 13px; }
  @media (max-width: 768px) {
    .metric-card .value { font-size: 18px; }
    .model-badge .name  { font-size: 20px; }
  }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ─────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.markdown("## 💨")
with col_title:
    st.markdown("# PEXCORE ERV Calculator")
    st.markdown("<small style='color:#64748b'>Hệ thống cấp khí tươi thu hồi nhiệt — Khí hậu nhiệt đới Việt Nam</small>",
                unsafe_allow_html=True)
st.divider()

# ─── TABS ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📐 Thiết kế & Chọn máy",
    "📊 Phân tích chi tiết",
    "💰 Dự toán chi phí",
    "📋 Catalogue",
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — THIẾT KẾ & CHỌN MÁY
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    left, right = st.columns([1, 1.2], gap="large")

    with left:
        st.markdown('<div class="section-header">🏠 THÔNG TIN KHÔNG GIAN</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            area   = st.number_input("Diện tích sàn (m²)", 20.0, 2000.0, 100.0, 5.0)
            rooms  = st.number_input("Số phòng ngủ", 1, 20, 3, 1)
            wcs    = st.number_input("Số WC", 0, 10, 2, 1)
        with c2:
            height   = st.number_input("Chiều cao trần (m)", 2.4, 5.0, 2.8, 0.1)
            kitchens = st.number_input("Bếp kín", 0, 3, 1, 1)
            occupancy = st.number_input("Số người", 1, 50, 4, 1)

        st.markdown('<div class="section-header">⚙️ THÔNG SỐ THIẾT KẾ</div>', unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            ach          = st.slider("ACH mục tiêu", 0.3, 2.0, 0.85, 0.05,
                                     help="Air Change per Hour — số lần thay khí/giờ")
            margin_pct   = st.slider("Dự phòng lưu lượng (%)", 5, 30, 15, 5)
        with c4:
            loading_target = st.slider("Loading target (%)", 60, 95, 80, 5,
                                       help="Tỷ lệ tải máy mục tiêu — 75-85% tối ưu")
            filter_type    = st.selectbox("Loại filter",
                ["F7 (PM2.5 — khuyến nghị VN)", "G3 (bụi thô)", "G3+F7", "Không lắp"],
                index=0)

        filter_key = filter_type.split(" ")[0]   # "F7", "G3", "G3+F7", "Không"
        filter_key = "None" if filter_key == "Không" else filter_key

        st.markdown('<div class="section-header">📏 HỆ THỐNG ỐNG GIÓ</div>', unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        with c5:
            trunk_len  = st.number_input("Chiều dài ống trunk (m)", 3.0, 30.0, 8.0, 1.0)
        with c6:
            branch_len = st.number_input("Chiều dài nhánh TB (m)", 2.0, 20.0, 10.0, 1.0)

        # COP và thông tin tài chính
        with st.expander("💡 Thông số tiết kiệm năng lượng"):
            cop       = st.slider("COP hệ thống điều hòa", 2.5, 5.0, 3.5, 0.1)
            hours_yr  = st.number_input("Giờ vận hành/năm", 1000, 8760, 2600, 100)
            tariff    = st.number_input("Đơn giá điện (VNĐ/kWh)", 1000, 5000, 2200, 100)

        calc_btn = st.button("🔄 TÍNH TOÁN & CHỌN MODEL", type="primary", use_container_width=True)

    # ── Tính toán ────────────────────────────────────────────────────────────
    inp = {
        "area": area, "height": height, "rooms": rooms, "wcs": wcs,
        "kitchens": kitchens, "occupancy": occupancy, "ach": ach,
        "margin_pct": margin_pct, "loading_target": loading_target,
        "filter_type": filter_key, "trunk_len": trunk_len, "branch_len": branch_len,
    }

    d    = compute_design(inp)
    best, top5 = select_model(d, loading_target/100.0, filter_key)
    sel  = best["model"]
    sav  = compute_savings(d["design_flow"], sel, cop, hours_yr, tariff)

    with right:
        st.markdown('<div class="section-header">📊 KẾT QUẢ LƯU LƯỢNG</div>', unsafe_allow_html=True)

        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.markdown(f"""<div class="metric-card">
                <div class="label">Thể tích</div>
                <div class="value">{d['volume']:.0f}</div>
                <div class="sub">m³</div></div>""", unsafe_allow_html=True)
        with mc2:
            st.markdown(f"""<div class="metric-card">
                <div class="label">Flow thiết kế</div>
                <div class="value">{d['design_flow']:.0f}</div>
                <div class="sub">m³/h (CMH)</div></div>""", unsafe_allow_html=True)
        with mc3:
            st.markdown(f"""<div class="metric-card">
                <div class="label">ESP yêu cầu</div>
                <div class="value">{d['required_esp']:.0f}</div>
                <div class="sub">Pa (incl. filter)</div></div>""", unsafe_allow_html=True)

        # Flow breakdown
        with st.expander("📐 Chi tiết lưu lượng"):
            import pandas as pd
            df_flow = pd.DataFrame([
                {"Phương pháp": "Theo ACH", "Lưu lượng (CMH)": d["flow_ach"]},
                {"Phương pháp": "Theo số người (25 m³/h/người)", "Lưu lượng (CMH)": d["flow_people"]},
                {"Phương pháp": "Theo số phòng (30 m³/h/phòng)", "Lưu lượng (CMH)": d["flow_supply_base"]},
                {"Phương pháp": "Hút thải (phòng+WC+bếp)", "Lưu lượng (CMH)": d["flow_extract"]},
                {"Phương pháp": "➡ Flow thiết kế (có dự phòng)", "Lưu lượng (CMH)": d["design_flow"]},
            ])
            st.dataframe(df_flow, hide_index=True, use_container_width=True)

        # Model badge
        loading_color = "#16a34a" if best["loading_pct"] <= 92 else "#f97316"
        esp_icon = "✅" if best["esp_ok"] else "⚠️"
        st.markdown(f"""
        <div class="model-badge">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <div class="sub">MODEL ĐỀ XUẤT — {sel['brand']}</div>
              <div class="name">{sel['id']}</div>
              <div class="sub">Phù hợp diện tích: {sel['suitable_area_m2']} m²</div>
            </div>
            <div style="text-align:right">
              <span class="recommend-tag">⭐ ĐỀ XUẤT</span><br><br>
              <span style="color:#f97316;font-weight:700;font-size:18px">
                {best['loading_pct']:.1f}% loading
              </span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Spec table
        st.markdown('<div class="section-header">🔧 THÔNG SỐ KỸ THUẬT</div>', unsafe_allow_html=True)
        spec_cols = st.columns(5)
        specs = [
            ("Lưu lượng", f"{sel['flow']} CMH"),
            ("ESP", f"{sel['esp']} Pa"),
            ("Công suất", f"{sel['power']} W"),
            ("Độ ồn", f"{sel['noise']} dB(A)"),
            ("η Enthalpy", sel['enthalpy_eff_cooling'] + "%"),
        ]
        for col, (label, val) in zip(spec_cols, specs):
            with col:
                st.markdown(f"""<div class="metric-card" style="text-align:center">
                    <div class="label">{label}</div>
                    <div class="value" style="font-size:16px">{val}</div>
                </div>""", unsafe_allow_html=True)

        # ESP check
        if best["esp_ok"]:
            st.success(f"✅ ESP model ({sel['esp']} Pa) ≥ yêu cầu ({d['required_esp']:.0f} Pa) — đủ áp")
        else:
            st.warning(f"⚠️ ESP model ({sel['esp']} Pa) < yêu cầu ({d['required_esp']:.0f} Pa) — cân nhắc rút ngắn ống hoặc bỏ filter")

        # Energy savings
        st.markdown('<div class="section-header">⚡ TIẾT KIỆM NĂNG LƯỢNG</div>', unsafe_allow_html=True)
        sv1, sv2, sv3 = st.columns(3)
        with sv1:
            st.markdown(f"""<div class="metric-card">
                <div class="label">Công suất tiết kiệm</div>
                <div class="value">{sav['q_saved_kw']}</div>
                <div class="sub">kW tải nhiệt</div></div>""", unsafe_allow_html=True)
        with sv2:
            st.markdown(f"""<div class="metric-card">
                <div class="label">Điện tiết kiệm/năm</div>
                <div class="value">{sav['kwh_year']:,.0f}</div>
                <div class="sub">kWh/năm</div></div>""", unsafe_allow_html=True)
        with sv3:
            st.markdown(f"""<div class="metric-card">
                <div class="label">Tiền điện tiết kiệm</div>
                <div class="value" style="color:#16a34a">{sav['vnd_year_m']}</div>
                <div class="sub">triệu VNĐ/năm</div></div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — PHÂN TÍCH CHI TIẾT
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">🏆 TOP 5 MODEL PHÙ HỢP NHẤT</div>', unsafe_allow_html=True)

    import pandas as pd
    rows = []
    for i, r in enumerate(top5):
        m = r["model"]
        rows.append({
            "Hạng": f"{'⭐' if i==0 else i+1}",
            "Model": m["id"],
            "Flow (CMH)": m["flow"],
            "Loading (%)": f"{r['loading_pct']:.1f}",
            "ESP (Pa)": m["esp"],
            "η Enthalpy C (%)": m["model"].get("enthalpy_eff_cooling",""),
            "Recovery (kW)": r["recovery_kw"],
            "Công suất (W)": m["power"],
            "Noise dB(A)": m["noise"],
            "Score": f"{r['score']:.1f}",
            "ESP OK": "✅" if r["esp_ok"] else "⚠️",
        })

    df_top = pd.DataFrame(rows)
    st.dataframe(df_top, hide_index=True, use_container_width=True)

    # Scoring breakdown
    st.markdown('<div class="section-header">📊 SCORING WEIGHTS (Trọng số chọn model)</div>', unsafe_allow_html=True)
    col_w, col_note = st.columns([1, 1])
    with col_w:
        weights = {
            "Loading (tỷ lệ tải)": 34,
            "ESP (áp suất tĩnh)": 24,
            "Recovery (thu hồi nhiệt)": 18,
            "Efficiency (hiệu suất)": 12,
            "Power (tiêu thụ điện)": 7,
            "Noise (độ ồn)": 5,
        }
        df_w = pd.DataFrame(weights.items(), columns=["Tiêu chí","Trọng số (%)"])
        st.dataframe(df_w, hide_index=True, use_container_width=True)
    with col_note:
        st.info("""
**Ghi chú — Khí hậu nhiệt đới VN:**
- **Tropical derating** áp dụng: η thực tế = η catalogue × 0.95–0.97
- **Filter F7** cộng thêm ~65 Pa vào ESP yêu cầu
- **Loading 75–85%** là vùng tối ưu cho VN (nhu cầu thay đổi theo mùa)
- Mùa đông Hà Nội: lưu lượng có thể giảm 20–30%
        """)

    # Flow analysis chart
    st.markdown('<div class="section-header">📈 SO SÁNH LƯU LƯỢNG CÁC PHƯƠNG PHÁP</div>', unsafe_allow_html=True)
    df_chart = pd.DataFrame({
        "Phương pháp": ["ACH", "Số người", "Số phòng", "Hút thải", "Thiết kế"],
        "CMH": [d["flow_ach"], d["flow_people"], d["flow_supply_base"], d["flow_extract"], d["design_flow"]],
    })
    st.bar_chart(df_chart.set_index("Phương pháp"), height=250)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — DỰ TOÁN CHI PHÍ
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    import pandas as pd

    st.markdown('<div class="section-header">🛒 BOM THIẾT BỊ & VẬT TƯ</div>', unsafe_allow_html=True)

    # Số lượng thiết bị
    erv_qty = 1
    erv_price = ERV_PRICES.get(sel["id"], 0)

    # Ước tính ống gió
    pipe_total_m = (d["rooms"] + d["wcs"] + d["kitchens"]) * 8 + trunk_len * 2
    supply_pts   = d["rooms"]
    extract_pts  = d["rooms"] + d["wcs"] + d["kitchens"]

    # BOM cơ bản
    bom_items = [
        {"Hạng mục": f"ERV {sel['id']} ({sel['flow']} CMH)",       "ĐVT":"Bộ", "SL":1,             "Đơn giá":erv_price,        "Thành tiền":erv_price},
        {"Hạng mục": "Ống gió PE Ø75/90 (nhánh cấp)",              "ĐVT":"m",  "SL":supply_pts*8,  "Đơn giá":70000,            "Thành tiền":supply_pts*8*70000},
        {"Hạng mục": "Ống gió PE Ø75/90 (nhánh hút)",              "ĐVT":"m",  "SL":extract_pts*8, "Đơn giá":70000,            "Thành tiền":extract_pts*8*70000},
        {"Hạng mục": "Ống gió trunk Ø160/200",                     "ĐVT":"m",  "SL":int(trunk_len*2),"Đơn giá":180000,         "Thành tiền":int(trunk_len*2)*180000},
        {"Hạng mục": "Hộp chia gió + miệng gió cấp",               "ĐVT":"Bộ", "SL":supply_pts,    "Đơn giá":900000,           "Thành tiền":supply_pts*900000},
        {"Hạng mục": "Miệng gió hút + valve",                      "ĐVT":"Cái","SL":extract_pts,   "Đơn giá":300000,           "Thành tiền":extract_pts*300000},
        {"Hạng mục": "Giảm âm ống trunk",                          "ĐVT":"Cái","SL":2,             "Đơn giá":700000,           "Thành tiền":1400000},
        {"Hạng mục": "Vật tư phụ (kẹp, ron, co, phụ kiện)",        "ĐVT":"Bộ", "SL":1,             "Đơn giá":int(erv_price*0.08),"Thành tiền":int(erv_price*0.08)},
        {"Hạng mục": "Thi công lắp đặt",                           "ĐVT":"Bộ", "SL":1,             "Đơn giá":int(erv_price*0.12),"Thành tiền":int(erv_price*0.12)},
    ]

    df_bom = pd.DataFrame(bom_items)

    # Cho phép sửa BOM
    st.caption("✏️ Bạn có thể sửa số lượng hoặc đơn giá trực tiếp trong bảng:")
    df_edited = st.data_editor(
        df_bom,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Đơn giá":    st.column_config.NumberColumn(format="%,.0f"),
            "Thành tiền": st.column_config.NumberColumn(format="%,.0f", disabled=True),
            "SL":         st.column_config.NumberColumn(min_value=0, max_value=999),
        },
        num_rows="dynamic",
    )

    # Tính lại thành tiền sau khi sửa
    subtotal = sum(
        row.get("SL",0) * row.get("Đơn giá",0)
        for _, row in df_edited.iterrows()
    )

    # Adjustments
    st.markdown('<div class="section-header">💸 ĐIỀU CHỈNH GIÁ</div>', unsafe_allow_html=True)
    adj1, adj2, adj3, adj4 = st.columns(4)
    with adj1: contingency = st.number_input("Dự phòng (%)", 0, 20, 5)
    with adj2: transport   = st.number_input("Vận chuyển (VNĐ)", 0, 10000000, 0, 500000)
    with adj3: discount    = st.number_input("Chiết khấu (%)", 0, 30, 0)
    with adj4: vat_pct     = st.number_input("VAT (%)", 0, 15, 10)

    contingency_val = subtotal * contingency / 100
    total_before_dis = subtotal + contingency_val + transport
    discount_val = total_before_dis * discount / 100
    net_before_vat = total_before_dis - discount_val
    vat_val = net_before_vat * vat_pct / 100
    grand_total = net_before_vat + vat_val

    # Summary
    st.markdown('<div class="section-header">📊 TỔNG HỢP</div>', unsafe_allow_html=True)
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Tổng vật tư & thiết bị</div>
            <div class="value" style="font-size:15px">{money(subtotal)}</div>
            <div class="sub">VNĐ chưa VAT</div></div>""", unsafe_allow_html=True)
    with t2:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Sau điều chỉnh</div>
            <div class="value" style="font-size:15px">{money(net_before_vat)}</div>
            <div class="sub">VNĐ chưa VAT</div></div>""", unsafe_allow_html=True)
    with t3:
        st.markdown(f"""<div class="metric-card">
            <div class="label">TỔNG SAU VAT</div>
            <div class="value" style="font-size:15px;color:#e8600a">{money(grand_total)}</div>
            <div class="sub">VNĐ</div></div>""", unsafe_allow_html=True)
    with t4:
        payback = grand_total / (sav["vnd_year_m"] * 1_000_000) if sav["vnd_year_m"] > 0 else 0
        st.markdown(f"""<div class="metric-card">
            <div class="label">Thời gian hoàn vốn</div>
            <div class="value" style="color:#16a34a">{payback:.1f}</div>
            <div class="sub">năm</div></div>""", unsafe_allow_html=True)

    # Export
    st.divider()
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        # Export CSV
        csv_buf = io.StringIO()
        df_edited.to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            "📥 Tải BOM (CSV)",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"BOM_ERV_{sel['id']}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with export_col2:
        # Export JSON project
        project_data = {
            "project_date": datetime.now().isoformat(),
            "model": sel["id"],
            "design": d,
            "savings": sav,
            "grand_total": grand_total,
            "inputs": inp,
        }
        st.download_button(
            "💾 Lưu dự án (JSON)",
            data=json.dumps(project_data, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"Project_ERV_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True,
        )

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — CATALOGUE
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    import pandas as pd

    st.markdown('<div class="section-header">📋 HOLTOP CFA SERIES — Catalogue đầy đủ</div>', unsafe_allow_html=True)

    cat_rows = []
    for m in CENTRAL_ERV_CATALOG:
        price = ERV_PRICES.get(m["id"], 0)
        area_str = m.get("suitable_area_m2","")
        cat_rows.append({
            "Model": m["id"],
            "Flow (CMH)": m["flow"],
            "ESP (Pa)": m["esp"],
            "η Enthalpy Cooling (%)": m["enthalpy_eff_cooling"],
            "η Enthalpy Heating (%)": m["enthalpy_eff_heating"],
            "η Temp (%)": m["temp_eff"],
            "Noise dB(A)": m["noise"],
            "Power (W)": m["power"],
            "Weight (kg)": m.get("weight_kg",""),
            "Diện tích phù hợp (m²)": area_str,
            "Giá tham khảo (VNĐ)": f"{money(price)}",
        })

    df_cat = pd.DataFrame(cat_rows)

    # Highlight row của model được chọn
    def highlight_selected(row):
        if row["Model"] == sel["id"]:
            return ["background-color: #fff7ed; font-weight: bold"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_cat.style.apply(highlight_selected, axis=1),
        hide_index=True,
        use_container_width=True,
        height=380,
    )

    st.info(f"🟠 Dòng được highlight = Model đang được đề xuất cho dự án này: **{sel['id']}**")

    # Filter options note
    st.markdown('<div class="section-header">🔧 FILTER OPTIONS — Lưu ý cho khí hậu Việt Nam</div>', unsafe_allow_html=True)
    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown("""
**G3 (bụi thô):**
- Lọc hạt > 10 μm
- Tổn thất áp: ~15–25 Pa
- Thay / rửa: 1–2 tháng/lần tại VN
- Dùng làm pre-filter bảo vệ F7

**F7 (PM2.5):**
- Lọc được 60–80% PM2.5
- Tổn thất áp: 45–108 Pa
- Thay: **3–4 tháng/lần** tại VN (châu Âu: 6–12 tháng)
- Bắt buộc tại Hà Nội / TP.HCM
        """)
    with fc2:
        st.markdown("""
**Khuyến nghị cho Việt Nam:**

✅ **G3 + F7** = tối ưu nhất
- G3 giữ bụi thô, kéo dài tuổi thọ F7
- F7 lọc PM2.5 bảo vệ sức khoẻ

⚠️ **Lưu ý ESP:**
- F7 cộng thêm ~65 Pa vào tổn thất
- Phần mềm đã tự động tính vào ESP yêu cầu
- Nếu chọn F7 mà model không đủ ESP → cân nhắc rút ngắn ống hoặc chọn model ESP cao hơn

🌡️ **Tropical derating:**
- Hiệu suất thực tế = 95–97% giá trị catalogue châu Âu
- Do độ ẩm cao (75–90% RH) ảnh hưởng đến lõi ER paper
        """)

    # Technical notes
    with st.expander("📖 Ghi chú kỹ thuật — Lõi ERV & Bảo trì"):
        st.markdown("""
**Lõi ER Paper (5th Gen HOLTOP):**
- Cross-flow enthalpy exchanger — trao đổi cả sensible + latent heat
- Vật liệu: giấy đặc chủng tẩm hóa chất hút ẩm, fire-retardant, mildew-resistant
- Cross-contamination rate: ~3–5% (chấp nhận được cho dân dụng)

**Lịch bảo trì tại Việt Nam:**
| Hạng mục | Tần suất VN | Châu Âu |
|---|---|---|
| Vệ sinh lọc G3 | 1–2 tháng | 3–6 tháng |
| Thay filter F7 | 3–4 tháng | 6–12 tháng |
| Vệ sinh lõi ERV | 6 tháng | 12 tháng |
| Kiểm tra cân bằng lưu lượng | 12 tháng | 24 tháng |

**Vệ sinh lõi ER Paper:**
- Dùng khí nén áp thấp (<3 bar), thổi theo chiều dòng khí
- KHÔNG dùng nước — sẽ hòa tan coating hút ẩm
- KHÔNG dùng hoá chất tẩy rửa
        """)

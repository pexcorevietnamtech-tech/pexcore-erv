"""PEXCORE ERV Calculator Streamlit App v2 - from desktop v5.10"""
import streamlit as st
import math, json, io, uuid
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="PEXCORE ERV",page_icon="💨",layout="wide",initial_sidebar_state="expanded")

# ── helpers ──────────────────────────────────────────────────────────────────
def sf(v,d=0.0):
    try: return float(str(v).replace(",","").strip())
    except: return d
def si(v,d=0):
    try:
        s=str(v).replace(",","").strip()
        if s.upper() in ("","NAN","NONE"): return d
        return int(round(float(s)))
    except: return d
def money(v):
    try: return f"{float(v):,.0f}"
    except: return "0"
def avg_rs(v,dft=0.0):
    s=str(v)
    try:
        if "-" in s:
            a,b=s.split("-",1); return (float(a)+float(b))/2.0
        return float(s)
    except: return float(dft)
def nm(m):
    if m is None: return ""
    return str(m).strip().upper().replace(" ","-").replace("–","-").replace("—","-")
def fk_label(label):
    s=str(label or "").upper()
    if "G3" in s and "F7" in s: return "G3+F7"
    if "F7" in s: return "F7"
    if "G3" in s: return "G3"
    return "NONE"
def fdp_model(m,fk):
    if fk=="G3+F7": return float(m.get("filter_dp_g3",18))+float(m.get("filter_dp_f7",65))
    if fk=="F7": return float(m.get("filter_dp_f7",65))
    if fk=="G3": return float(m.get("filter_dp_g3",18))
    return 0.0
def fdp_typ(fk): return {"G3":18.,"F7":65.,"G3+F7":83.,"NONE":0.}.get(fk,0.)
def ffm(fk): return {"G3":12.,"F7":20.,"G3+F7":25.,"NONE":8.}.get(fk,12.)
def cdiv(a,b): return int(math.ceil(float(a)/float(b))) if b else 0
def gp(pd_,*keys,fb=0): 
    for k in keys:
        nk=nm(k)
        if nk in pd_: return float(pd_[nk])
    return float(fb)

CENTRAL_ERV_CATALOG = [
    # HOLTOP Comfort Fresh Air Ceiling Mounted ERV - Technical Parameters
    # Rated Airflow: CMH/CFM. flow field uses CMH for calculation.
    {"id": "CFA150C", "flow": 150, "cfm": 88, "esp": 95, "noise": 29, "power": 58, "voltage": "220-240/50Hz, 120/60Hz", "temp_eff": "80-84", "enthalpy_eff_cooling": "71-79", "enthalpy_eff_heating": "73-79", "core_type": "cross_flow_enthalpy_paper", "filter_option": "G3/F7 optional", "fan_type": "DC", "brand": "HOLTOP", "weight_kg": 20, "suitable_area_m2": "30-60", "tropical_derating": 0.97, "filter_dp_g3": 12, "filter_dp_f7": 45},
    {"id": "CFA250C", "flow": 250, "cfm": 147, "esp": 85, "noise": 28, "power": 62, "voltage": "220-240/50Hz, 120/60Hz", "temp_eff": "79-86", "enthalpy_eff_cooling": "68-83", "enthalpy_eff_heating": "70-83", "core_type": "cross_flow_enthalpy_paper", "filter_option": "G3/F7 optional", "fan_type": "DC", "brand": "HOLTOP", "weight_kg": 23, "suitable_area_m2": "60-90", "tropical_derating": 0.97, "filter_dp_g3": 15, "filter_dp_f7": 52},
    {"id": "CFA350C", "flow": 350, "cfm": 205, "esp": 160, "noise": 32, "power": 140, "voltage": "220-240/50Hz, 120/60Hz", "temp_eff": "80-89", "enthalpy_eff_cooling": "71-82", "enthalpy_eff_heating": "72-84", "core_type": "cross_flow_enthalpy_paper", "filter_option": "G3/F7 optional", "fan_type": "DC", "brand": "HOLTOP", "weight_kg": 30, "suitable_area_m2": "90-130", "tropical_derating": 0.97, "filter_dp_g3": 18, "filter_dp_f7": 58},
    {"id": "CFA500C", "flow": 500, "cfm": 294, "esp": 120, "noise": 34, "power": 165, "voltage": "220-240/50Hz, 120/60Hz", "temp_eff": "78-87", "enthalpy_eff_cooling": "67-82", "enthalpy_eff_heating": "69-83", "core_type": "cross_flow_enthalpy_paper", "filter_option": "G3/F7 optional", "fan_type": "DC", "brand": "HOLTOP", "weight_kg": 33, "suitable_area_m2": "130-170", "tropical_derating": 0.97, "filter_dp_g3": 22, "filter_dp_f7": 65, "note": "ESP 120Pa thấp hơn CFA350C — cần kiểm tra tổng trở ống gió kỹ"},
    {"id": "CFA650C", "flow": 650, "cfm": 382, "esp": 120, "noise": 35, "power": 252, "voltage": "220-240/50Hz", "temp_eff": "77-86", "enthalpy_eff_cooling": "66-81", "enthalpy_eff_heating": "69-82", "core_type": "cross_flow_enthalpy_paper", "filter_option": "G3/F7 optional", "fan_type": "DC", "brand": "HOLTOP", "weight_kg": 38, "suitable_area_m2": "170-220", "tropical_derating": 0.96, "filter_dp_g3": 26, "filter_dp_f7": 72},
    {"id": "CFA800C", "flow": 800, "cfm": 470, "esp": 150, "noise": 35, "power": 335, "voltage": "220-240/50Hz", "temp_eff": "79-85", "enthalpy_eff_cooling": "70-81", "enthalpy_eff_heating": "71-82", "core_type": "cross_flow_enthalpy_paper", "filter_option": "G3/F7 optional", "fan_type": "DC", "brand": "HOLTOP", "weight_kg": 48, "suitable_area_m2": "220-300", "tropical_derating": 0.96, "filter_dp_g3": 28, "filter_dp_f7": 78},
    {"id": "CFA1000C", "flow": 1000, "cfm": 588, "esp": 170, "noise": 37, "power": 420, "voltage": "220-240/50Hz", "temp_eff": "80-90", "enthalpy_eff_cooling": "71-86", "enthalpy_eff_heating": "73-87", "core_type": "cross_flow_enthalpy_paper", "filter_option": "G3/F7 optional", "fan_type": "DC", "brand": "HOLTOP", "weight_kg": 54, "suitable_area_m2": "300-400", "tropical_derating": 0.96, "filter_dp_g3": 32, "filter_dp_f7": 85},
    {"id": "CFA1500C", "flow": 1500, "cfm": 882, "esp": 175, "noise": 39, "power": 670, "voltage": "220-240/50Hz", "temp_eff": "80-85", "enthalpy_eff_cooling": "71-81", "enthalpy_eff_heating": "72-82", "core_type": "cross_flow_enthalpy_paper", "filter_option": "G3/F7 optional", "fan_type": "DC", "brand": "HOLTOP", "weight_kg": 105, "suitable_area_m2": "400-600", "tropical_derating": 0.95, "filter_dp_g3": 40, "filter_dp_f7": 95},
    {"id": "CFA2000C", "flow": 2000, "cfm": 1176, "esp": 150, "noise": 40, "power": 850, "voltage": "220-240/50Hz", "temp_eff": "80-90", "enthalpy_eff_cooling": "71-86", "enthalpy_eff_heating": "73-87", "core_type": "cross_flow_enthalpy_paper", "filter_option": "G3/F7 optional", "fan_type": "DC", "brand": "HOLTOP", "weight_kg": 117, "suitable_area_m2": "600-800", "tropical_derating": 0.95, "filter_dp_g3": 48, "filter_dp_f7": 108, "note": "ESP 150Pa — kiểm tra tổng áp ống gió khi dùng F7/G3+F7"},
]

ERV_EQUIPMENT_PRICES = {
    "CFA150C": 28500000,
    "CFA250C": 32500000,
    "CFA350C": 37800000,
    "CFA500C": 46500000,
    "CFA650C": 52800000,
    "CFA800C": 59500000,
    "CFA1000C": 72000000,
    "CFA1500C": 98000000,
    "CFA2000C": 125000000,
    "AV-TPM10/DFW": 12800000,
}

DEFAULT_PRICES = {
    "DN-75GREEN": 66100,
    "DN-90PE": 72000,
    "DN-110GREEN": 82600,
    "DN-160GREEN": 170900,
    "DN-200GREEN": 199000,
    "BOX-DN160/75*5": 870200,
    "BOX-DN160/110*6": 1546600,
    "BOX-DN200/110*6": 1767700,
    "DN160-SILENCING": 760800,
    "DN110-SILENCING": 632500,
    "DN-200SILENCING": 1362800,
    "DN160-VENTCAPX": 310900,
    "DN110-VENTCAPX": 233300,
    "DN200-VENTCAPX": 389000,
    "DN-75ORING": 5800,
    "DN-110ORING": 9500,
    "DN-160ORING": 14200,
    "DN-200ORING": 22900,
    "DN-75OSHAPED": 14900,
    "DN-110OSHAPED": 20400,
    "DN-160OSHAPED": 47300,
    "DN-200OSHAPED": 56600,
    "YM-75A": 187900,
    "YM-100A": 216400,
    "FK-75YPK": 87200,
    "FK-100YPK": 101200,
    "DN-75DIRECT": 49200,
    "DN-110DIRECT": 61500,
    "DN-160DIRECT": 79900,
    "DN-200DIRECT": 131900,
    "DN-110ELBOW": 93300,
    "DN-160ELBOW": 166300,
    "DN-200ELBOW": 246900,
    "DN-110DINOX": 9500,
    "DN160-DINOX": 13700,
    "DN200-DINOX": 19400,
    "DN-160/160FLEX": 165200,
    "DN-160/110FLEX": 97300,
    "DN-200/200FLEX": 204800,
}

OUTLET_CATALOG = {
    "YM-75A": {"type": "supply", "area": 0.0055, "tolerance": 10},
    "YM-100A": {"type": "supply", "area": 0.0095, "tolerance": 10},
    "FK-75YPK": {"type": "extract", "area": 0.0050, "tolerance": 12},
    "FK-100YPK": {"type": "extract", "area": 0.0085, "tolerance": 12},
}


USAGE_MAP = {
    "Tiêu chuẩn": {"ach":0.85,"ppf":1.08,"margin":15},
    "Thấp":        {"ach":0.70,"ppf":1.03,"margin":12},
    "Cao":         {"ach":1.00,"ppf":1.10,"margin":18},
}
PRIORITY_MAP = {
    "Tiết kiệm đầu tư":    {"loading":90,"topology":"Centralized - Trunk + Branch"},
    "Cân bằng":            {"loading":80,"topology":"Centralized - Octopus Supply + Branch Return"},
    "Êm / dư tải an toàn": {"loading":70,"topology":"Centralized - Full Octopus Supply/Return"},
}

def compute_design(p):
    area=p["area"]; height=p["height"]
    rooms=max(1,p["rooms"]); wcs=max(0,p["wcs"]); kitchens=max(0,p["kitchens"])
    occupancy=max(1,p["occupancy"])
    ach=p["ach"]; s_room=p["s_room"]; e_room=p["e_room"]
    e_wc=p["e_wc"]; e_kitchen=p["e_kitchen"]
    ppf=max(1.0,p["ppf"]); margin=p["margin"]
    loading_target=max(50.,min(100.,p["loading_target"]))
    branch_len=p["branch_len"]; trunk_len=p["trunk_len"]
    pipe_waste=max(1.,p["pipe_waste"]); topology=p["topology"]

    volume=area*height; flow_ach=volume*ach
    flow_people=occupancy*25.; q_supply_rooms=rooms*s_room
    q_supply_target=max(flow_ach,flow_people,q_supply_rooms)
    flow_supply_base=q_supply_target; flow_supply=flow_supply_base*ppf
    flow_extract_rooms=rooms*e_room; flow_extract_wet=wcs*e_wc
    flow_extract_kitchen=kitchens*e_kitchen
    flow_extract=flow_extract_rooms+flow_extract_wet+flow_extract_kitchen
    base_design_flow=max(flow_supply,flow_extract)
    design_flow=base_design_flow*(1+margin/100.)
    required_nominal=design_flow/(loading_target/100.)

    supply_pts=rooms; extract_pts=rooms+wcs+kitchens
    supply_pt_flow=max(20,flow_supply/max(rooms,1))
    extract_pt_flow=max(18,flow_extract/max(extract_pts,1))

    if supply_pt_flow<=40:   sb_d=75; s_out="YM-75A";   s_pipe="DN-75GREEN"
    elif supply_pt_flow<=60: sb_d=90; s_out="YM-100A";  s_pipe="DN-90PE"
    else:                    sb_d=110;s_out="YM-100A";  s_pipe="DN-110GREEN"
    if extract_pt_flow<=40:   eb_d=75; e_out="FK-75YPK";  e_pipe="DN-75GREEN"
    elif extract_pt_flow<=60: eb_d=90; e_out="FK-100YPK"; e_pipe="DN-90PE"
    else:                     eb_d=110;e_out="FK-100YPK"; e_pipe="DN-110GREEN"

    if design_flow<=180:
        td=110;tm="DN-110GREEN";sil="DN110-SILENCING";vc="DN110-VENTCAPX"
        dr="DN-110DIRECT";el="DN-110ELBOW";cl="DN-110DINOX";ori="DN-110ORING";osh="DN-110OSHAPED";fl="DN-160/110FLEX"
    elif design_flow<=420:
        td=160;tm="DN-160GREEN";sil="DN160-SILENCING";vc="DN160-VENTCAPX"
        dr="DN-160DIRECT";el="DN-160ELBOW";cl="DN160-DINOX";ori="DN-160ORING";osh="DN-160OSHAPED";fl="DN-160/160FLEX"
    else:
        td=200;tm="DN-200GREEN";sil="DN-200SILENCING";vc="DN200-VENTCAPX"
        dr="DN-200DIRECT";el="DN-200ELBOW";cl="DN200-DINOX";ori="DN-200ORING";osh="DN-200OSHAPED";fl="DN-200/200FLEX"

    if sb_d==75: bpb=5; dm="BOX-DN160/75*5"
    else:        bpb=6; dm="BOX-DN160/110*6" if td<=160 else "BOX-DN200/110*6"

    return {
        "area":area,"height":height,"volume":volume,"rooms":rooms,"wcs":wcs,
        "kitchens":kitchens,"occupancy":occupancy,
        "flow_ach":round(flow_ach,1),"flow_people":round(flow_people,1),
        "flow_supply_base":round(flow_supply_base,1),"flow_supply":round(flow_supply,1),
        "flow_extract":round(flow_extract,1),"flow_extract_rooms":round(flow_extract_rooms,1),
        "flow_extract_wet":round(flow_extract_wet,1),"flow_extract_kitchen":round(flow_extract_kitchen,1),
        "base_design_flow":round(base_design_flow,1),"design_flow":round(design_flow,1),
        "required_nominal":round(required_nominal,1),
        "positive_pressure_factor":ppf,"pipe_waste_factor":pipe_waste,
        "topology":topology,"branch_len":branch_len,"trunk_len":trunk_len,
        "supply_points":supply_pts,"extract_points":extract_pts,
        "supply_branch_d":sb_d,"extract_branch_d":eb_d,"trunk_d":td,
        "supply_outlet_model":s_out,"extract_outlet_model":e_out,
        "supply_pipe_model":s_pipe,"extract_pipe_model":e_pipe,
        "trunk_model":tm,"silencer_model":sil,"ventcap_model":vc,
        "direct_model":dr,"elbow_model":el,"clamp_model":cl,
        "oring_model":ori,"oshape_model":osh,"flex_model":fl,
        "dist_model":dm,"branches_per_box":bpb,
        "supply_point_flow":round(supply_pt_flow,1),"extract_point_flow":round(extract_pt_flow,1),
        "supply_target_velocity":round((supply_pt_flow/3600)/OUTLET_CATALOG.get(s_out,{"area":0.006})["area"],2),
        "extract_target_velocity":round((extract_pt_flow/3600)/OUTLET_CATALOG.get(e_out,{"area":0.006})["area"],2),
    }

def select_model(d, fk, loading_target_pct):
    rf=d["design_flow"]; rn=d["required_nominal"]
    pw=d["pipe_waste_factor"]; topo=d["topology"]
    if "Full Octopus" in topo:   ca=34;tf=1.0; bf=1.5; fe=12;ba=8
    elif "Octopus Supply" in topo: ca=38;tf=1.25;bf=1.35;fe=14;ba=10
    else:                          ca=46;tf=1.65;bf=1.25;fe=18;ba=6
    term=10; cm=max(8,rf*0.02)
    duct_esp=(d["trunk_len"]*tf+d["branch_len"]*bf)*pw
    base_esp=ca+duct_esp+fe+ba+term+cm

    def mre(m): return base_esp+fdp_model(m,fk)+ffm(fk)
    def esp_ok(m): return m["esp"]>=mre(m)*0.92

    esp_c=[m for m in CENTRAL_ERV_CATALOG if m["flow"]>=rn and esp_ok(m)]
    nom_c=[m for m in CENTRAL_ERV_CATALOG if m["flow"]>=rn]
    fl_c =[m for m in CENTRAL_ERV_CATALOG if m["flow"]>=rf and esp_ok(m)]
    cands=esp_c or nom_c or fl_c or [CENTRAL_ERV_CATALOG[-1]]

    dh=28.;rho=1.2
    all_eff=[0.55*avg_rs(m.get("enthalpy_eff_cooling","70"),70)
             +0.25*avg_rs(m.get("enthalpy_eff_heating","72"),72)
             +0.20*avg_rs(m.get("temp_eff","80"),80) for m in cands]
    mne=min(all_eff); mxe=max(all_eff)
    mnp=min(m["power"] for m in cands); mxp=max(m["power"] for m in cands)
    mnn=min(m["noise"] for m in cands); mxn=max(m["noise"] for m in cands)
    tl=loading_target_pct/100.
    W_L=0.34;W_E=0.24;W_R=0.18;W_EF=0.12;W_P=0.07;W_N=0.05

    comp=[]
    for m in cands:
        lr=rf/m["flow"] if m["flow"] else 999
        ec=avg_rs(m.get("enthalpy_eff_cooling","70"),70)
        eh=avg_rs(m.get("enthalpy_eff_heating","72"),72)
        t=avg_rs(m.get("temp_eff","80"),80)
        trop=m.get("tropical_derating",0.97); ec_adj=ec*trop
        rk=rho*(rf/3600)*dh*(ec_adj/100); rpw=rk*1000/max(1,m["power"])
        req_esp=mre(m)
        if lr>1.: ls=max(0.,60.-(lr-1.)*100*4.)
        else:     ls=max(0.,100.-abs(lr-tl)*200.)
        es=(min(100,80+min(20,(m["esp"]-req_esp)*.6)) if m["esp"]>=req_esp else max(0,90-(req_esp-m["esp"])*2.8))
        ps=100*(mxp-m["power"])/(mxp-mnp) if mxp>mnp else 100.
        ns=100*(mxn-m["noise"])/(mxn-mnn) if mxn>mnn else 100.
        rs=min(100.,rpw*12)
        raw=0.55*ec_adj+0.25*eh+0.20*t
        ef=100*(raw-mne)/(mxe-mne) if mxe>mne else 100.
        gap=max(0,(m["flow"]-rn)/rn) if rn else 0
        score=ls*W_L+es*W_E+rs*W_R+ef*W_EF+ps*W_P+ns*W_N-min(24,gap*85)
        comp.append({"id":m["id"],"flow":m["flow"],"loading":round(lr*100,1),
            "esp":m["esp"],"required_esp":round(req_esp,1),
            "filter_dp":round(fdp_model(m,fk),1),
            "esp_ok":esp_ok(m),"power":m["power"],"noise":m["noise"],
            "enthalpy_eff_cooling":round(ec_adj,1),"recovery_kw":round(rk,2),
            "tropical_derating":trop,"score":round(score,2)})

    comp.sort(key=lambda x:-x["score"])
    best=comp[0]
    DS=max(0.45,tl-0.20); US=min(0.98,tl+0.10)
    if best["loading"]<DS*100:
        sm=[r for r in comp if r["flow"]<best["flow"] and r["flow"]>=rf]
        if sm: best=sorted(sm,key=lambda x:-x["score"])[0]
    elif best["loading"]>US*100:
        lg=[r for r in comp if r["flow"]>best["flow"]]
        if lg: best=sorted(lg,key=lambda x:-x["score"])[0]

    bm=next(m for m in CENTRAL_ERV_CATALOG if m["id"]==best["id"])
    return bm, best, comp[:5]

def build_bom(d, bm, br, fk, opts, markup, pdict, epdict):
    items=[]; topo=d["topology"]; pw=d["pipe_waste_factor"]
    def add(grp,desc,mdl,unit,qty,cost,rmk=""):
        sale=cost*(1+markup/100.)
        items.append({"group":grp,"desc":desc,"model":mdl,"unit":unit,
            "qty":round(qty,2),"cost_price":round(cost),"sale_price":round(sale),"remarks":rmk,"source":"auto"})

    ecost=float(epdict.get(nm(bm["id"]),ERV_EQUIPMENT_PRICES.get(bm["id"],0)))
    add("Thiết bị chính",
        f"ERV trần {bm['id']} ({bm['flow']} m³/h) | {bm['brand']} | Loading {br['loading']:.1f}%",
        bm["id"],"Bộ",1,ecost,
        f"ESP {bm['esp']}Pa | η cooling {br['enthalpy_eff_cooling']:.1f}% | {bm['power']}W | {bm['noise']}dB(A)")

    if "Full Octopus" in topo:
        sbl=d["supply_points"]*d["branch_len"]*pw; ebl=d["extract_points"]*d["branch_len"]*pw; tml=2.0
        sb=cdiv(d["supply_points"],d["branches_per_box"]); eb=cdiv(d["extract_points"],d["branches_per_box"])
    elif "Octopus Supply" in topo:
        sbl=d["supply_points"]*d["branch_len"]*pw; ebl=d["extract_points"]*d["branch_len"]*0.65*pw
        tml=d["trunk_len"]*pw; sb=cdiv(d["supply_points"],d["branches_per_box"]); eb=cdiv(d["extract_points"],d["branches_per_box"])
    else:
        sbl=d["supply_points"]*d["branch_len"]*0.7*pw; ebl=d["extract_points"]*d["branch_len"]*0.7*pw
        tml=d["trunk_len"]*pw; sb=cdiv(d["supply_points"],d["branches_per_box"]); eb=cdiv(d["extract_points"],d["branches_per_box"])

    ttl=tml*2+0.5; th=cdiv(ttl,1.5); sbh=cdiv(sbl,1.5); ebh=cdiv(ebl,1.5)
    tc=cdiv(ttl,3); te=4; bd=cdiv(sbl+ebl,3); bv=d["supply_points"]+d["extract_points"]
    ap=max(1,cdiv(bv,8)); cq=cdiv(ttl+sbl+ebl,1.5)*2; oq=cq

    add("Ống gió cấp",f"Ống gió PE Ø{d['supply_branch_d']}",d["supply_pipe_model"],"m",sbl,gp(pdict,d["supply_pipe_model"],fb=66100))
    add("Ống gió hút",f"Ống gió PE Ø{d['extract_branch_d']}",d["extract_pipe_model"],"m",ebl,gp(pdict,d["extract_pipe_model"],fb=66100))
    add("Ống trunk",f"Trunk Ø{d['trunk_d']}",d["trunk_model"],"m",ttl,gp(pdict,d["trunk_model"],fb=170900))
    add("Hộp chia","Hộp chia cấp",d["dist_model"],"Cái",sb,gp(pdict,d["dist_model"],fb=870200))
    add("Hộp chia","Hộp chia hút",d["dist_model"],"Cái",eb,gp(pdict,d["dist_model"],fb=870200))
    add("Miệng gió",f"Miệng cấp {d['supply_outlet_model']}",d["supply_outlet_model"],"Cái",d["supply_points"],gp(pdict,d["supply_outlet_model"],fb=187900))
    add("Miệng gió",f"Miệng hút {d['extract_outlet_model']}",d["extract_outlet_model"],"Cái",d["extract_points"],gp(pdict,d["extract_outlet_model"],fb=87200))
    add("Giảm ồn","Ống tiêu âm",d["silencer_model"],"Cái",2,gp(pdict,d["silencer_model"],fb=760800))
    add("Cap ngoài","VentcapX",d["ventcap_model"],"Cái",2,gp(pdict,d["ventcap_model"],fb=310900))
    add("Phụ kiện","Vòng đệm",d["oring_model"],"Cái",oq,gp(pdict,d["oring_model"],fb=9500))
    add("Phụ kiện","Quang treo",d["oshape_model"],"Cái",th+sbh+ebh,gp(pdict,d["oshape_model"],fb=20400))
    add("Phụ kiện","Nối mềm đầu máy",d["flex_model"],"Cái",2,gp(pdict,d["flex_model"],fb=165200))
    add("Phụ kiện","Nối thẳng",d["direct_model"],"Cái",tc+bd,gp(pdict,d["direct_model"],fb=61500))
    add("Phụ kiện","Co/cút trunk",d["elbow_model"],"Cái",te,gp(pdict,d["elbow_model"],fb=93300))
    add("Phụ kiện","Đai siết",d["clamp_model"],"Cái",cq,gp(pdict,d["clamp_model"],fb=9500))
    add("Cân bằng","Van cân bằng","BALANCE-VALVE","Cái",bv,95000)
    add("Phụ kiện","Cửa thăm bảo trì","ACCESS-PANEL","Cái",ap,185000)
    if bm["flow"]>=350: add("Phụ kiện","Filter G3 dự phòng","FILTER-G3-SPARE","Bộ",1,480000)
    if opts.get("pm25") or bm["flow"]>=500: add("Phụ kiện","Filter F7","FILTER-F7-UPGRADE","Bộ",1,1350000,"Khuyến nghị VN")
    if opts.get("bypass"):    add("Điều khiển","Auto Bypass","AUTO-BYPASS","Bộ",1,750000)
    if opts.get("sleep"):     add("Điều khiển","Sleep Mode","SLEEP-MODE","Bộ",1,650000)
    if opts.get("defrost"):   add("Điều khiển","Auto Defrost","DEFROST","Bộ",1,550000)
    if opts.get("ac_interlock"): add("Điều khiển","AC Interlock","AC-INTERLOCK","Bộ",1,1200000)
    if opts.get("modbus"):    add("Điều khiển","Modbus/BMS","MODBUS","Bộ",1,1800000)
    if opts.get("filter_alarm"): add("Điều khiển","Filter Alarm","FILTER-ALARM","Bộ",1,450000)
    if opts.get("co2"):       add("Sensor","Cảm biến CO₂","CO2-SENSOR","Cái",1,1650000)
    if opts.get("pm25"):      add("Sensor","Cảm biến PM2.5","PM25-SENSOR","Cái",1,1450000)
    if opts.get("humidity"):  add("Sensor","Cảm biến RH","RH-SENSOR","Cái",1,850000)

    labor=4500000+d["area"]*28000+(d["supply_points"]+d["extract_points"])*170000+tml*20000+ap*45000
    misc=1200000+d["area"]*5000+(sb+eb)*90000+ap*20000
    add("Nhân công","Thi công, lắp đặt, cân chỉnh, test","LABOR","Gói",1,labor)
    add("Khác","Vật tư phụ, khoan cắt, hoàn thiện","SITE-MISC","Gói",1,misc)
    return items

def calc_totals(bom, manual, cpct, transport, other, dpct, vpct):
    all_=[*bom,*manual]
    sub=sum(r["qty"]*r["sale_price"] for r in all_)
    cost=sum(r["qty"]*r["cost_price"] for r in all_)
    cont=sub*cpct/100; sub2=sub+cont+transport+other
    disc=sub2*dpct/100; net=sub2-disc; vat=net*vpct/100; grand=net+vat
    return {"subtotal":sub,"cost_total":cost,"contingency":cont,
            "net_before_vat":net,"vat":vat,"grand_total":grand}

def calc_sav(df, bm, cop=3.5, hrs=2600, tariff=2200):
    ec=avg_rs(bm.get("enthalpy_eff_cooling","75"),75)*bm.get("tropical_derating",0.97)/100
    q=1.2*(df/3600)*28*ec; w=q/cop; kwh=w*hrs; vnd=kwh*tariff
    return {"q_kw":round(q,2),"w_kw":round(w,3),"kwh":round(kwh),"vnd_m":round(vnd/1e6,1)}


# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.mc{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;margin:4px 0}
.mc .lb{font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase}
.mc .vl{font-size:20px;font-weight:700;color:#0f172a}
.mc .sb{font-size:11px;color:#94a3b8}
.sh{background:#0f172a;color:white;padding:7px 14px;border-radius:7px;font-weight:700;font-size:13px;margin:14px 0 8px 0}
.mb{background:#0f172a;color:white;border-radius:10px;padding:14px 18px;margin:8px 0}
.mb .nm{font-size:22px;font-weight:800;color:#f97316}
.tok{background:#16a34a;color:white;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;display:inline-block}
.twn{background:#f97316;color:white;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;display:inline-block}
</style>""", unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💨 PEXCORE ERV v5.10")
    st.markdown("---")
    st.markdown("### 🏠 Không gian")
    area=st.number_input("Diện tích (m²)",20.,2000.,118.,5.)
    height=st.number_input("Chiều cao (m)",2.2,5.,2.8,.1)
    c1,c2=st.columns(2)
    with c1:
        rooms=st.number_input("Phòng ngủ",1,20,4,1)
        kitchens=st.number_input("Bếp kín",0,3,1,1)
    with c2:
        wcs=st.number_input("WC",0,10,2,1)
        occupancy=st.number_input("Số người",1,50,4,1)

    st.markdown("### ⚡ Preset")
    up=st.selectbox("Mức sử dụng",["Tiêu chuẩn","Thấp","Cao"])
    pp=st.selectbox("Ưu tiên",["Cân bằng","Tiết kiệm đầu tư","Êm / dư tải an toàn"])
    u=USAGE_MAP[up]; pr=PRIORITY_MAP[pp]

    st.markdown("### ⚙️ Thông số nâng cao")
    with st.expander("Mở rộng"):
        ach=st.slider("ACH",0.3,2.,float(u["ach"]),.05)
        ppf=st.slider("PPF (áp dương)",1.,1.2,float(u["ppf"]),.01)
        margin=st.slider("Dự phòng (%)",5,30,int(u["margin"]),5)
        lt=st.slider("Loading target (%)",50,95,int(pr["loading"]),5)
        topo_opts=["Centralized - Octopus Supply + Branch Return",
                   "Centralized - Full Octopus Supply/Return",
                   "Centralized - Trunk + Branch"]
        topo=st.selectbox("Topology",topo_opts,index=topo_opts.index(pr["topology"]))
        s_room=st.number_input("Cấp/phòng (m³/h)",10.,60.,30.,5.)
        e_room=st.number_input("Hút/phòng (m³/h)",10.,50.,25.,5.)
        e_wc=st.number_input("Hút/WC (m³/h)",10.,40.,20.,5.)
        e_kitchen=st.number_input("Hút/bếp (m³/h)",10.,60.,30.,5.)
        trunk_len=st.number_input("Trunk len (m)",2.,30.,8.,1.)
        branch_len=st.number_input("Branch len TB (m)",2.,20.,10.,1.)
        pipe_waste=st.slider("Hệ số hao hụt ống",1.,1.5,1.2,.05)

    st.markdown("### 🔧 Filter")
    fl=st.selectbox("Loại filter",["G3 + F7 (khuyến nghị VN)","F7 (PM2.5)","G3 (bụi thô)","Không lắp filter"])
    fk=fk_label(fl)

    st.markdown("### 💰 Tài chính")
    markup=st.slider("Biên LN (%)",0,50,18,1)
    cpct=st.slider("Dự phòng giá (%)",0,15,3,1)
    vpct=st.slider("VAT (%)",0,15,10,1)
    dpct=st.slider("Chiết khấu (%)",0,30,0,1)
    transport=st.number_input("Vận chuyển (VNĐ)",0,20000000,0,500000)
    other_fee=st.number_input("Chi phí khác (VNĐ)",0,20000000,0,500000)
    cop=st.slider("COP ĐH",2.,5.,3.5,.1)
    hrs=st.number_input("Giờ VH/năm",500,8760,2600,100)
    tariff=st.number_input("Giá điện (VNĐ/kWh)",500,5000,2200,100)

    st.markdown("### 🎛️ Điều khiển & Sensor")
    c3,c4=st.columns(2)
    with c3:
        ob=st.checkbox("Auto Bypass",True)
        osl=st.checkbox("Sleep Mode",True)
        od=st.checkbox("Auto Defrost",True)
        oco2=st.checkbox("CO₂ Sensor")
    with c4:
        opm=st.checkbox("PM2.5 Sensor")
        orh=st.checkbox("RH Sensor")
        omb=st.checkbox("Modbus/BMS")
        ofa=st.checkbox("Filter Alarm",True)
        oac=st.checkbox("AC Interlock")

# ── COMPUTE ──────────────────────────────────────────────────────────────────
params={"area":area,"height":height,"rooms":rooms,"wcs":wcs,"kitchens":kitchens,
        "occupancy":occupancy,"ach":ach,"ppf":ppf,"margin":margin,"loading_target":lt,
        "topology":topo,"s_room":s_room,"e_room":e_room,"e_wc":e_wc,"e_kitchen":e_kitchen,
        "trunk_len":trunk_len,"branch_len":branch_len,"pipe_waste":pipe_waste}

d=compute_design(params)
pdict={nm(k):v for k,v in DEFAULT_PRICES.items()}
epdict={nm(k):v for k,v in ERV_EQUIPMENT_PRICES.items()}
bm,br,top5=select_model(d,fk,lt)
opts={"bypass":ob,"sleep":osl,"defrost":od,"co2":oco2,"pm25":opm,
      "humidity":orh,"modbus":omb,"filter_alarm":ofa,"ac_interlock":oac}
bom=build_bom(d,bm,br,fk,opts,markup,pdict,epdict)
sav=calc_sav(d["design_flow"],bm,cop,hrs,tariff)
if "manual_bom" not in st.session_state: st.session_state.manual_bom=[]
tots=calc_totals(bom,st.session_state.manual_bom,cpct,transport,other_fee,dpct,vpct)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("# 💨 PEXCORE ERV Calculator")
st.markdown("<small style='color:#64748b'>Cấp khí tươi thu hồi nhiệt | Khí hậu nhiệt đới VN | Engine v5.10</small>",unsafe_allow_html=True)
st.divider()

tab1,tab2,tab3,tab4,tab5=st.tabs(["📐 Thiết kế & Chọn máy","📊 Phân tích chi tiết","💰 BOM & Dự toán","🔧 Commissioning","📋 Catalogue"])

# ══════════════════ TAB 1 ══════════════════
with tab1:
    L,R=st.columns([1,1.3],gap="large")
    with L:
        st.markdown('<div class="sh">📊 LƯU LƯỢNG GIÓ</div>',unsafe_allow_html=True)
        a1,a2,a3=st.columns(3)
        for col,(lb,vl,sb) in zip([a1,a2,a3],[
            ("Thể tích",f"{d['volume']:.0f}","m³"),
            ("Flow thiết kế",f"{d['design_flow']:.0f}","m³/h"),
            ("ESP yêu cầu",f"{br['required_esp']:.0f}","Pa (incl. filter)"),
        ]):
            with col: st.markdown(f'<div class="mc"><div class="lb">{lb}</div><div class="vl">{vl}</div><div class="sb">{sb}</div></div>',unsafe_allow_html=True)
        with st.expander("Chi tiết lưu lượng"):
            st.dataframe(pd.DataFrame([
                {"PP":"ACH","CMH":d["flow_ach"]},{"PP":"Số người","CMH":d["flow_people"]},
                {"PP":f"Số phòng×{s_room}","CMH":d["flow_supply_base"]},
                {"PP":f"Supply×PPF{ppf:.2f}","CMH":d["flow_supply"]},
                {"PP":"Hút thải","CMH":d["flow_extract"]},{"PP":"➡ Design flow","CMH":d["design_flow"]},
            ]),hide_index=True,use_container_width=True)
        st.markdown('<div class="sh">🔧 ỐNG GIÓ</div>',unsafe_allow_html=True)
        p1,p2,p3=st.columns(3)
        with p1: st.metric("Nhánh cấp",f"Ø{d['supply_branch_d']}"); st.metric("Miệng cấp",d["supply_outlet_model"])
        with p2: st.metric("Nhánh hút",f"Ø{d['extract_branch_d']}"); st.metric("Miệng hút",d["extract_outlet_model"])
        with p3: st.metric("Trunk",f"Ø{d['trunk_d']}"); st.metric("PPF",f"×{ppf:.2f}")
        st.caption(f"v_cấp≈{d['supply_target_velocity']:.2f} m/s | v_hút≈{d['extract_target_velocity']:.2f} m/s | "
                   f"Điểm cấp {d['supply_points']} | Điểm hút {d['extract_points']} | Pipe waste ×{pipe_waste:.2f}")
    with R:
        lok=br["loading"]<=90
        st.markdown(f"""<div class="mb">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div><div style="font-size:11px;color:#94a3b8">MODEL ĐỀ XUẤT — {bm['brand']}</div>
              <div class="nm">{bm['id']}</div>
              <div style="font-size:12px;color:#94a3b8">Phù hợp {bm['suitable_area_m2']} m²</div></div>
            <div style="text-align:right">
              <span class="{'tok' if lok else 'twn'}">⭐ ĐỀ XUẤT</span><br><br>
              <span style="color:#f97316;font-weight:700;font-size:18px">{br['loading']:.1f}% loading</span>
            </div></div></div>""",unsafe_allow_html=True)
        if br["esp_ok"]: st.success(f"✅ ESP {bm['esp']} Pa ≥ yêu cầu {br['required_esp']:.0f} Pa")
        else: st.error(f"⚠️ ESP {bm['esp']} Pa < yêu cầu {br['required_esp']:.0f} Pa")
        fdp_v=fdp_model(bm,fk); ffm_v=ffm(fk)
        st.info(f"🔧 Filter {fk}: ΔP={fdp_v:.0f}Pa | Fouling={ffm_v:.0f}Pa | Tổng={fdp_v+ffm_v:.0f}Pa | Tropical ×{bm['tropical_derating']}")
        st.markdown('<div class="sh">📊 THÔNG SỐ KỸ THUẬT</div>',unsafe_allow_html=True)
        s1,s2,s3,s4,s5=st.columns(5)
        for col,(lb,vl) in zip([s1,s2,s3,s4,s5],[("Flow",f"{bm['flow']} CMH"),("ESP",f"{bm['esp']} Pa"),("Power",f"{bm['power']} W"),("Noise",f"{bm['noise']} dB"),("η Enth C",bm["enthalpy_eff_cooling"]+"%")]):
            with col: st.markdown(f'<div class="mc" style="text-align:center"><div class="lb">{lb}</div><div class="vl" style="font-size:15px">{vl}</div></div>',unsafe_allow_html=True)
        st.caption(f"Tropical derating ×{bm['tropical_derating']} → η cooling adj = {br['enthalpy_eff_cooling']:.1f}%")
        st.markdown('<div class="sh">⚡ TIẾT KIỆM NĂNG LƯỢNG</div>',unsafe_allow_html=True)
        e1,e2,e3=st.columns(3)
        with e1: st.markdown(f'<div class="mc"><div class="lb">Q tiết kiệm</div><div class="vl">{sav["q_kw"]}</div><div class="sb">kW</div></div>',unsafe_allow_html=True)
        with e2: st.markdown(f'<div class="mc"><div class="lb">Điện TK/năm</div><div class="vl">{sav["kwh"]:,.0f}</div><div class="sb">kWh</div></div>',unsafe_allow_html=True)
        with e3: st.markdown(f'<div class="mc"><div class="lb">Tiền điện TK</div><div class="vl" style="color:#16a34a">{sav["vnd_m"]}</div><div class="sb">triệu VNĐ/năm</div></div>',unsafe_allow_html=True)
        pb=tots["grand_total"]/(sav["vnd_m"]*1e6) if sav["vnd_m"]>0 else 0
        st.metric("⏱ Hoàn vốn",f"{pb:.1f} năm")

# ══════════════════ TAB 2 ══════════════════
with tab2:
    st.markdown('<div class="sh">🏆 TOP 5 MODEL THEO SCORING</div>',unsafe_allow_html=True)
    df_t=pd.DataFrame([{"Hạng":"⭐" if i==0 else str(i+1),"Model":r["id"],
        "Flow":r["flow"],"Loading%":r["loading"],"ESP Pa":r["esp"],
        "ESP req":r["required_esp"],"ΔP filter":r["filter_dp"],"ESP OK":"✅" if r["esp_ok"] else "⚠️",
        "η Enth C%":r["enthalpy_eff_cooling"],"Tropical":r["tropical_derating"],
        "Recovery kW":r["recovery_kw"],"Power W":r["power"],"Noise dB":r["noise"],
        "Score":r["score"]} for i,r in enumerate(top5)])
    st.dataframe(df_t,hide_index=True,use_container_width=True)

    c_w,c_n=st.columns(2)
    with c_w:
        st.markdown('<div class="sh">⚖️ TRỌNG SỐ SCORING</div>',unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([
            {"Tiêu chí":"Loading (tỷ lệ tải)","W%":34},
            {"Tiêu chí":"ESP (áp suất tĩnh)","W%":24},
            {"Tiêu chí":"Recovery (nhiệt adj. tropical)","W%":18},
            {"Tiêu chí":"Efficiency (normalize)","W%":12},
            {"Tiêu chí":"Power (tiêu thụ điện)","W%":7},
            {"Tiêu chí":"Noise (độ ồn)","W%":5},
        ]),hide_index=True,use_container_width=True)
    with c_n:
        st.info(f"""
**Thông số hiện tại:**
- Filter: **{fk}** → ΔP={fdp_typ(fk):.0f}Pa | Fouling={ffm(fk):.0f}Pa
- Pipe waste: **×{pipe_waste:.2f}**  
- PPF: **×{ppf:.2f}** → Q_supply = Q_base × {ppf:.2f}
- Tropical derating: **×{bm['tropical_derating']}**
- Loading target: **{lt}%**
- Topology: **{topo.split('-')[-1].strip()}**
        """)

    st.markdown('<div class="sh">📊 SO SÁNH LƯU LƯỢNG</div>',unsafe_allow_html=True)
    st.bar_chart(pd.DataFrame({
        "PP":["ACH","Số người","Số phòng","Supply×PPF","Hút thải","Thiết kế"],
        "CMH":[d["flow_ach"],d["flow_people"],d["flow_supply_base"],d["flow_supply"],d["flow_extract"],d["design_flow"]],
    }).set_index("PP"),height=240)

    st.markdown('<div class="sh">🔍 ESP BREAKDOWN</div>',unsafe_allow_html=True)
    if "Full Octopus" in topo: tf2,bf2,ca2,fa2,ba2=1.,1.5,34,12,8
    elif "Octopus Supply" in topo: tf2,bf2,ca2,fa2,ba2=1.25,1.35,38,14,10
    else: tf2,bf2,ca2,fa2,ba2=1.65,1.25,46,18,6
    de=(trunk_len*tf2+branch_len*bf2)*pipe_waste
    fdpv=fdp_model(bm,fk); ffmv=ffm(fk)
    st.dataframe(pd.DataFrame([
        {"Thành phần":"Lõi ERV","Pa":ca2},
        {"Thành phần":f"Ống gió ×{pipe_waste:.2f}","Pa":round(de,1)},
        {"Thành phần":"Co/cút/phụ kiện","Pa":fa2},
        {"Thành phần":"Hộp chia gió","Pa":ba2},
        {"Thành phần":"Miệng gió","Pa":10},
        {"Thành phần":f"Filter {fk}","Pa":fdpv},
        {"Thành phần":"Fouling margin (VN)","Pa":ffmv},
        {"Thành phần":"Commissioning margin","Pa":round(max(8,d["design_flow"]*0.02),1)},
        {"Thành phần":"TỔNG ESP yêu cầu","Pa":round(br['required_esp'],1)},
    ]),hide_index=True,use_container_width=True)

# ══════════════════ TAB 3 ══════════════════
with tab3:
    st.markdown(f'<div class="sh">🛒 BOM TỰ ĐỘNG — {bm["id"]} | Markup {markup}% | {topo.split("-")[-1].strip()}</div>',unsafe_allow_html=True)
    df_bom=pd.DataFrame(bom)
    df_bom["Thành tiền"]=df_bom["qty"]*df_bom["sale_price"]
    st.dataframe(df_bom[["group","desc","model","unit","qty","cost_price","sale_price","Thành tiền","remarks"]].rename(
        columns={"group":"Nhóm","desc":"Hạng mục","model":"Model","unit":"ĐVT","qty":"SL",
                 "cost_price":"Giá vốn","sale_price":"Đơn giá bán","remarks":"Ghi chú"}
    ).style.format({"Giá vốn":"{:,.0f}","Đơn giá bán":"{:,.0f}","Thành tiền":"{:,.0f}","SL":"{:,.1f}"}),
        hide_index=True,use_container_width=True,height=300)

    st.markdown('<div class="sh">➕ THÊM HẠNG MỤC THỦ CÔNG</div>',unsafe_allow_html=True)
    with st.form("add_m"):
        mc1,mc2,mc3=st.columns(3)
        with mc1: mg=st.text_input("Nhóm","Manual"); md=st.text_input("Mô tả","")
        with mc2: mm=st.text_input("Model",""); mu=st.selectbox("ĐVT",["Cái","Bộ","m","m²","Gói"])
        with mc3: mq=st.number_input("SL",0.1,9999.,1.,.5); ms=st.number_input("Đơn giá bán",0,999999999,0,50000)
        mn=st.text_input("Ghi chú","")
        if st.form_submit_button("➕ Thêm"):
            if md:
                mc=ms/(1+markup/100.) if markup>-99 else ms
                st.session_state.manual_bom.append({"group":mg,"desc":md,"model":mm,"unit":mu,
                    "qty":mq,"cost_price":round(mc),"sale_price":ms,"Thành tiền":mq*ms,"remarks":mn,"source":"manual"})
                st.rerun()

    if st.session_state.manual_bom:
        st.dataframe(pd.DataFrame(st.session_state.manual_bom)[["group","desc","model","unit","qty","sale_price","Thành tiền"]],
            hide_index=True,use_container_width=True)
        if st.button("🗑️ Xóa manual BOM"):
            st.session_state.manual_bom=[]; st.rerun()

    tots2=calc_totals(bom,st.session_state.manual_bom,cpct,transport,other_fee,dpct,vpct)
    st.markdown('<div class="sh">💸 TỔNG HỢP CHI PHÍ</div>',unsafe_allow_html=True)
    ta,tb,tc,td=st.columns(4)
    with ta: st.markdown(f'<div class="mc"><div class="lb">Tổng giá bán</div><div class="vl" style="font-size:14px">{money(tots2["subtotal"])}</div><div class="sb">VNĐ chưa VAT</div></div>',unsafe_allow_html=True)
    with tb: st.markdown(f'<div class="mc"><div class="lb">Sau dự phòng+CK</div><div class="vl" style="font-size:14px">{money(tots2["net_before_vat"])}</div><div class="sb">VNĐ chưa VAT</div></div>',unsafe_allow_html=True)
    with tc: st.markdown(f'<div class="mc"><div class="lb">TỔNG SAU VAT</div><div class="vl" style="font-size:14px;color:#e8600a">{money(tots2["grand_total"])}</div><div class="sb">VNĐ</div></div>',unsafe_allow_html=True)
    with td:
        pb2=tots2["grand_total"]/(sav["vnd_m"]*1e6) if sav["vnd_m"]>0 else 0
        st.markdown(f'<div class="mc"><div class="lb">Hoàn vốn</div><div class="vl" style="color:#16a34a">{pb2:.1f}</div><div class="sb">năm</div></div>',unsafe_allow_html=True)

    col1,col2=st.columns(2)
    with col1:
        all_b=bom+st.session_state.manual_bom
        df_ex=pd.DataFrame(all_b); df_ex["Thành tiền"]=df_ex["qty"]*df_ex["sale_price"]
        buf=io.StringIO(); df_ex.to_csv(buf,index=False,encoding="utf-8-sig")
        st.download_button("📥 Tải BOM (CSV)",buf.getvalue().encode("utf-8-sig"),
            f"BOM_{bm['id']}_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)
    with col2:
        pj={"date":datetime.now().isoformat(),"model":bm["id"],"design":d,"savings":sav,"totals":tots2,"params":params}
        st.download_button("💾 Lưu dự án (JSON)",json.dumps(pj,ensure_ascii=False,indent=2).encode(),
            f"Project_{datetime.now().strftime('%Y%m%d_%H%M')}.json","application/json",use_container_width=True)

# ══════════════════ TAB 4 ══════════════════
with tab4:
    st.markdown('<div class="sh">🔧 BẢNG ĐO COMMISSIONING</div>',unsafe_allow_html=True)
    st.caption(f"Model: {bm['id']} | Flow: {d['design_flow']:.0f} m³/h | Topology: {topo.split('-')[-1].strip()}")
    sm=OUTLET_CATALOG.get(d["supply_outlet_model"],{"area":0.006,"tolerance":10})
    em=OUTLET_CATALOG.get(d["extract_outlet_model"],{"area":0.006,"tolerance":12})
    qs=d["flow_supply"]/max(1,d["supply_points"])
    qer=d["flow_extract_rooms"]/max(1,rooms) if rooms>0 else 0
    qew=d["flow_extract_wet"]/max(1,wcs) if wcs>0 else 0
    qek=d["flow_extract_kitchen"]/max(1,kitchens) if kitchens>0 else 0
    cr=[]
    for i in range(rooms): cr.append({"Vị trí":f"Cấp phòng {i+1}","Loại":"Cấp","Model":d["supply_outlet_model"],"Q mục tiêu":round(qs,1),"v mục tiêu":round((qs/3600)/sm["area"],2),"Tolerance%":sm["tolerance"]})
    for i in range(rooms): cr.append({"Vị trí":f"Hút phòng {i+1}","Loại":"Hút","Model":d["extract_outlet_model"],"Q mục tiêu":round(qer,1),"v mục tiêu":round((qer/3600)/em["area"],2),"Tolerance%":em["tolerance"]})
    for i in range(wcs): cr.append({"Vị trí":f"WC {i+1}","Loại":"Hút","Model":d["extract_outlet_model"],"Q mục tiêu":round(qew,1),"v mục tiêu":round((qew/3600)/em["area"],2),"Tolerance%":em["tolerance"]})
    for i in range(kitchens): cr.append({"Vị trí":f"Bếp {i+1}","Loại":"Hút","Model":d["extract_outlet_model"],"Q mục tiêu":round(qek,1),"v mục tiêu":round((qek/3600)/em["area"],2),"Tolerance%":em["tolerance"]})
    df_cr=pd.DataFrame(cr); df_cr["v thực (m/s)"]=""; df_cr["Trạng thái"]="Chưa đo"
    ed=st.data_editor(df_cr,hide_index=True,use_container_width=True,
        column_config={"v thực (m/s)":st.column_config.NumberColumn(min_value=0.,max_value=10.,format="%.2f")},num_rows="fixed")
    results2=[]
    for _,row in ed.iterrows():
        vr=row.get("v thực (m/s)","")
        try:
            vrf=float(str(vr)); ar=sm["area"] if row["Loại"]=="Cấp" else em["area"]
            qr=round(vrf*3600*ar,1); dev=round((qr-row["Q mục tiêu"])/row["Q mục tiêu"]*100,1) if row["Q mục tiêu"] else 0
            tol=row["Tolerance%"]
            st2="OK" if abs(dev)<=tol*0.5 else ("Cận biên" if abs(dev)<=tol else "Lệch")
            results2.append({"Vị trí":row["Vị trí"],"Q thực":qr,"% lệch":dev,"Trạng thái":st2})
        except: pass
    if results2:
        df_r2=pd.DataFrame(results2)
        c1,c2,c3=st.columns(3)
        with c1: st.metric("✅ OK",len([r for r in results2 if r["Trạng thái"]=="OK"]))
        with c2: st.metric("⚠️ Cận biên",len([r for r in results2 if r["Trạng thái"]=="Cận biên"]))
        with c3: st.metric("❌ Lệch",len([r for r in results2 if r["Trạng thái"]=="Lệch"]))
        st.dataframe(df_r2,hide_index=True,use_container_width=True)
    bufc=io.StringIO(); ed.to_csv(bufc,index=False,encoding="utf-8-sig")
    st.download_button("📄 Xuất biên bản CSV",bufc.getvalue().encode("utf-8-sig"),
        f"Commissioning_{bm['id']}_{datetime.now().strftime('%Y%m%d')}.csv","text/csv")

# ══════════════════ TAB 5 ══════════════════
with tab5:
    st.markdown('<div class="sh">📋 HOLTOP CFA SERIES — Catalogue</div>',unsafe_allow_html=True)
    cats=[{"Model":m["id"],"Flow CMH":m["flow"],"CFM":m["cfm"],"ESP Pa":m["esp"],
           "η C%":m["enthalpy_eff_cooling"],"η H%":m["enthalpy_eff_heating"],"η T%":m["temp_eff"],
           "Noise":m["noise"],"Power W":m["power"],"Weight kg":m["weight_kg"],
           "Diện tích m²":m["suitable_area_m2"],"Tropical":m["tropical_derating"],
           "ΔP G3":m["filter_dp_g3"],"ΔP F7":m["filter_dp_f7"],
           "Giá (VNĐ)":money(ERV_EQUIPMENT_PRICES.get(m["id"],0))} for m in CENTRAL_ERV_CATALOG]
    df_cat=pd.DataFrame(cats)
    def hl(row): return ["background:#fff7ed;font-weight:bold"]*len(row) if row["Model"]==bm["id"] else [""]*len(row)
    st.dataframe(df_cat.style.apply(hl,axis=1),hide_index=True,use_container_width=True,height=360)
    st.info(f"🟠 Highlight = Model đề xuất: **{bm['id']}** | Loading {br['loading']:.1f}%")

    with st.expander("🔧 Bảo trì tại Việt Nam"):
        st.markdown("""
| Hạng mục | Tần suất VN | Châu Âu |
|---|---|---|
| Vệ sinh filter G3 | 1–2 tháng | 3–6 tháng |
| Thay filter F7 | **3–4 tháng** | 6–12 tháng |
| Vệ sinh lõi ERV | **6 tháng** | 12 tháng |
| Cân bằng lưu lượng | 12 tháng | 24 tháng |
        """)
    with st.expander("💰 Giá phụ kiện HDPE"):
        st.dataframe(pd.DataFrame([{"Model":k,"Giá VNĐ":money(v)} for k,v in DEFAULT_PRICES.items()]),
            hide_index=True,use_container_width=True)

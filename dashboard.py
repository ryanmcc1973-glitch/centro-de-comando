import streamlit as st
import requests
import time
import html
import re
from datetime import datetime, timezone
from pathlib import Path

st.set_page_config(page_title="Painel Controle Sniper Project", page_icon="🦅", layout="wide")
FIREBASE_ROOT = "https://robos-marcello-default-rtdb.firebaseio.com"
FUTURES_API = "https://contract.mexc.com"
MAX_CARDS = 40

st.markdown("""
<style>
.stApp {background:radial-gradient(ellipse at 12% 0%,#102e55 0%,#07172e 40%,#030b19 100%);color:#e6f4ff}
.block-container {max-width:1420px;padding-top:1.4rem}
h1,h2,h3 {color:#eaf8ff}
[data-testid="stMetric"] {background:#0b2340;border:1px solid #205b93;border-radius:14px;padding:12px}
.card {position:relative;min-height:295px;background:linear-gradient(145deg,#102b4e,#07172b);
 border:1px solid #2176b7;border-radius:22px;padding:20px;margin:8px 0 18px;
 box-shadow:0 9px 24px #0007,0 0 16px #0a9cf421;overflow:hidden}
.card:before {content:"";position:absolute;top:0;left:0;right:0;height:3px;background:#2ecaff;box-shadow:0 0 16px #2ecaff}
.card-title {font-size:1.25rem;font-weight:800;color:#fff;letter-spacing:.4px}
.card-robot {font-size:.75rem;letter-spacing:1.4px;font-weight:800;color:#56d8ff}
.card-sub {font-size:.82rem;color:#9ebad5}
.tag {display:inline-block;padding:5px 11px;margin:6px 6px 10px 0;background:#123d64;
 color:#a6ebff;border:1px solid #2a83bb;border-radius:30px;font-size:.75rem;font-weight:800}
.long {color:#5df2bf}.short {color:#ff879d}.neutral {color:#a5bed8}
.kv {display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-bottom:1px solid #24415d}
.k {color:#a8bed4;font-size:.86rem}.v {color:#fff;font-weight:700;text-align:right;overflow-wrap:anywhere}
.note {color:#8fb2d1;font-size:.76rem;margin-top:13px}
.card-foot {margin-top:12px;color:#7bdcff;font-size:.78rem}
.headline {color:#62d9ff;font-size:clamp(1.5rem,3vw,2.6rem);font-weight:900;
 letter-spacing:1px;text-shadow:0 0 18px #0d9dff77}
.subtitle {color:#a9c8e4;font-size:.9rem}
div[data-testid="stImage"] img {border-radius:15px}
</style>
""", unsafe_allow_html=True)

def esc(x):
    return html.escape(str(x if x is not None else "—"))

def num(x):
    try:
        v=float(x)
        return v if v == v and abs(v) != float("inf") else None
    except (TypeError,ValueError,OverflowError):
        return None

def pricefmt(x):
    v=num(x)
    if v is None: return "—"
    digits=2 if abs(v)>=100 else 4 if abs(v)>=1 else 6 if abs(v)>=0.01 else 8
    return f"{v:,.{digits}f}"

def symbol_of(record):
    raw=str(record.get("ativo") or record.get("symbol") or "").upper()
    # Normalize symbols from Firebase to USDT futures notation
    raw=raw.split(":")[0].replace("/","").replace("_","").replace("-","")
    return raw if re.fullmatch(r"[A-Z0-9]{4,24}",raw) and raw.endswith("USDT") else None

@st.cache_data(ttl=10,show_spinner=False)
def firebase_data(collection):
    url=f"{FIREBASE_ROOT}/{collection}.json"
    response=requests.get(url,timeout=12)
    response.raise_for_status()
    data=response.json()
    return data if isinstance(data,dict) else {}

@st.cache_data(ttl=10, show_spinner=False)
def futures_prices():
    response = requests.get(f"{FUTURES_API}/api/v1/contract/ticker", timeout=15)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise ValueError("Resposta inesperada da MEXC Futures")
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("Lista de contratos MEXC indisponível")
    prices = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).upper().replace("_", "")
        price = num(item.get("lastPrice"))
        if symbol.endswith("USDT") and price is not None and price > 0:
            prices[symbol] = price
    if not prices:
        raise ValueError("Nenhuma cotação válida da MEXC Futures")
    return prices

def robot_name(r, is_nr7=False):
    if is_nr7:return "NR7"
    raw=str(r.get("robo") or "Não identificado")
    low=raw.lower()
    if "alpha" in low:return "ALPHA"
    if "gr" in low or "mcc" in low:return "GRÉCIA"
    if "sniper" in low:return "SNIPER"
    return raw

def timestamp_value(record,key):
    t=record.get("timestamp") or record.get("data") or record.get("created_at")
    if isinstance(t,(int,float)):return float(t)/1000 if t>1e11 else float(t)
    if isinstance(t,str):
        try:return datetime.fromisoformat(t.replace("Z","+00:00")).timestamp()
        except ValueError:pass
    try:return float(key.rsplit("_",1)[-1])
    except (ValueError,TypeError):return 0

def line(label,value):
    return f'<div class="kv"><span class="k">{esc(label)}</span><span class="v">{esc(value)}</span></div>'

def render_card(record, name, is_nr7, price):
    symbol=symbol_of(record) or str(record.get("ativo") or "Ativo não identificado")
    direction=str(record.get("direcao") or "AGUARDANDO").upper()
    phase=str(record.get("fase") or record.get("status") or "SINAL").upper()
    if is_nr7 and phase not in ("PRE","ARM","CONFIRM"):phase="SINAL"
    side="long" if direction=="LONG" else "short" if direction=="SHORT" else "neutral"
    entry=num(record.get("entrada"))
    target=num(record.get("alvo") if record.get("alvo") is not None else record.get("tp1"))
    stop=num(record.get("stop"))
    # Prices alone cannot establish a fill, an active position, or realized PnL.
    potential=None
    if entry and target and direction in ("LONG","SHORT"):
        potential=(target-entry)/entry*100*(1 if direction=="LONG" else -1)
    rows=line("Cotação MEXC Futures",pricefmt(price) if price else "Indisponível")
    if entry is not None: rows+=line("Entrada indicada",pricefmt(entry))
    if stop is not None: rows+=line("Stop indicado",pricefmt(stop))
    if target is not None: rows+=line("Alvo / TP1",pricefmt(target))
    for label,field in (("TP2","tp2"),("TP3","tp3")):
        if num(record.get(field)) is not None:rows+=line(label,pricefmt(record[field]))
    if potential is not None:rows+=line("Variação teórica até TP1",f"{potential:+.2f}% (sem taxas)")
    if is_nr7:
        rows+=line("Contexto 4H",record.get("contexto") or "—")
        rows+=line("Padrão / gatilho","NR7 1H / 15M")
    else:
        if record.get("timeframe"):rows+=line("Timeframe",record["timeframe"])
        if record.get("gatilho"):rows+=line("Gatilho",record["gatilho"])
    status_label=phase if phase not in ("ATIVO","TRADE ATIVO") else "SINAL REGISTRADO"
    # Explicitly never claim live trade execution from market-price comparison.
    extra="Simulação • sem ordem executada" if is_nr7 else "Alerta registrado • execução não verificada"
    if is_nr7 and record.get("descricao"):
        desc=str(record["descricao"])[:190]
        extra+=f" • {desc}"
    return (f'<div class="card"><div class="card-robot">🤖 {esc(name)}</div>'
            f'<div class="card-title">{esc(symbol)} <span class="{side}">{esc(direction)}</span></div>'
            f'<span class="tag">{esc(status_label)}</span>'
            f'<span class="tag">MEXC FUTUROS</span>'
            f'{rows}<div class="note">{esc(extra)}</div></div>')

header_left,header_right=st.columns([1,7],vertical_alignment="center")
with header_left:
    photo=Path(__file__).with_name("sniper.png")
    if photo.exists():st.image(str(photo),width=110)
    else:st.markdown("## 🦅")
with header_right:
    st.markdown('<div class="headline">PAINEL CONTROLE SNIPER PROJECT</div>'
                '<div class="subtitle">Alpha • Grécia • Sniper • NR7 | Sinais de futuros | Monitoramento informativo</div>',
                unsafe_allow_html=True)

errors=[]
trades={}
nr7={}
prices={}
try:trades=firebase_data("trades")
except (requests.RequestException,ValueError) as e:errors.append(f"Firebase /trades: {type(e).__name__}")
try:nr7=firebase_data("nr7_simulacoes")
except (requests.RequestException,ValueError) as e:errors.append(f"Firebase /nr7_simulacoes: {type(e).__name__}")
try:prices=futures_prices()
except (requests.RequestException,ValueError) as e:errors.append(f"MEXC Futures: {type(e).__name__}")

records=[]
for key,record in trades.items():
    if not isinstance(record,dict):continue
    name=robot_name(record)
    if name not in ("ALPHA","GRÉCIA","SNIPER"):continue
    records.append((timestamp_value(record,key),record,name,False))
for key,record in nr7.items():
    if isinstance(record,dict):
        records.append((timestamp_value(record,key),record,"NR7",True))
records.sort(key=lambda x:x[0],reverse=True)

m1,m2,m3,m4=st.columns(4)
m1.metric("Sinais carregados",len(records))
m2.metric("Alpha / Grécia / Sniper",sum(not r[3] for r in records))
m3.metric("Alertas NR7",sum(r[3] for r in records))
m4.metric("Fonte de preço","MEXC Futures" if prices else "Indisponível")
for err in errors:st.warning(err)

filter_robot=st.selectbox("Filtrar robô",["Todos","ALPHA","GRÉCIA","SNIPER","NR7"])

filter_phase=st.selectbox(
    "Filtrar sinais",
    ["Somente CONFIRM","Todos os sinais"],
    index=0
)

shown=[
    r for r in records
    if (filter_robot=="Todos" or r[2]==filter_robot)
    and (
        filter_phase=="Todos os sinais"
        or str(r[1].get("fase") or r[1].get("status") or "").strip().upper()=="CONFIRM"
    )
][:MAX_CARDS]

if not shown:st.info("Nenhum sinal registrado para este filtro.")
else:
    for offset in range(0,len(shown),2):
        cols=st.columns(2,gap="medium")
        for col,item in zip(cols,shown[offset:offset+2]):
            _,record,name,is_nr7=item
            with col:
                symbol=symbol_of(record)
                st.markdown(render_card(record,name,is_nr7,prices.get(symbol)),unsafe_allow_html=True)

st.caption("Cotações: MEXC USDT-M Futures • Firebase: leitura apenas • Nenhum PnL é classificado como realizado sem execução confirmada.")
st.caption(f"Atualização automática a cada 10 segundos • {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
time.sleep(10)
st.rerun()

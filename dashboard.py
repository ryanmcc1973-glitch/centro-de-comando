import streamlit as st
import pandas as pd
import time
import requests
import os
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA (Visual Dark/Neon)
# ==========================================
st.set_page_config(page_title="Alpha Terminal", layout="wide", page_icon="👾")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00ffcc; font-family: 'Courier New', Courier, monospace; }
    h1 { color: #00ffcc; text-align: center; text-shadow: 0 0 10px #00ffcc; border-bottom: 2px solid #00ffcc; padding-bottom: 10px; }
    
    /* Cards */
    .trade-card { background: linear-gradient(145deg, #0a0a0a, #111111); padding: 20px; border-radius: 15px; border: 1px solid #333; border-left: 8px solid #00ffcc; margin-bottom: 25px; box-shadow: 0 0 15px rgba(0, 255, 204, 0.1); transition: 0.3s; }
    .trade-card:hover { box-shadow: 0 0 25px rgba(0, 255, 204, 0.4); transform: translateY(-2px); }
    
    /* Card Short (Vermelho Neon) */
    .trade-card-short { border-left: 8px solid #ff0055; box-shadow: 0 0 15px rgba(255, 0, 85, 0.1); }
    .trade-card-short:hover { box-shadow: 0 0 25px rgba(255, 0, 85, 0.4); }

    /* Card Aguardando (Cinza) */
    .trade-card-waiting { border-left: 8px solid #aaaaaa; box-shadow: 0 0 15px rgba(170, 170, 170, 0.1); opacity: 0.8; }

    /* Textos */
    .title { font-size: 26px; font-weight: bold; color: #ffffff; margin-bottom: 10px; }
    .pnl { font-size: 28px; font-weight: bold; color: #00ffcc; text-shadow: 0 0 8px #00ffcc; }
    .pnl-negative { color: #ff0055; text-shadow: 0 0 8px #ff0055; }
    .info { font-size: 15px; color: #aaaaaa; margin: 5px 0; }
    .info-value { color: #ffffff; font-weight: bold; }
    .status-waiting { color: #ffcc00; font-weight: bold; font-size: 18px; }
    .status-active { color: #00ffcc; font-weight: bold; font-size: 18px; }
    </style>
""", unsafe_allow_html=True)

st.title("👾 ALPHA TERMINAL")

# ==========================================
# FUNÇÕES (MEXC SPOT E FUTUROS + FIREBASE)
# ==========================================
def obter_preco_atual(ativo):
    simbolo_mexc = ativo.replace("/", "_")
    
    # Tenta Futuros
    url_fut = f"https://contract.mexc.com/api/v1/contract/ticker?symbol={simbolo_mexc}"
    try:
        res = requests.get(url_fut, timeout=5).json()
        if res['success']:
            return float(res['data']['lastPrice'])
    except Exception: pass
        
    # Tenta Spot
    url_spot = f"https://api.mexc.com/api/v3/ticker/price?symbol={simbolo_mexc}"
    try:
        res_spot = requests.get(url_spot, timeout=5).json()
        if 'price' in res_spot:
            return float(res_spot['price'])
    except Exception: pass
        
    return None

def carregar_trades_firebase():
    url = "https://robos-marcello-default-rtdb.firebaseio.com/trades.json"
    try:
        res = requests.get(url, timeout=5).json()
        if res:
            items = list(res.items())
            
            # --- FILTRO: ACEITA ALPHA E MCC ---
            # Verifica se o nome do robô no Firebase é "AlphaEWS" ou contém "MCC"
            robos_permitidos = ["AlphaEWS", "MCC (30m)", "MCC"]
            trades_filtrados = [item for item in items if item[1].get("robo") in robos_permitidos]
            
            # Ordena pelo timestamp (nome do ativo)
            def extrair_timestamp(item):
                try: return int(item[0].split('_')[-1])
                except: return 0
            trades_filtrados.sort(key=extrair_timestamp)
            
            # Pega os 10 mais recentes de ambos
            return [item[1] for item in trades_filtrados[-10:]]
        return []
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return []

# ==========================================
# LÓGICA PRINCIPAL E RENDERIZAÇÃO
# ==========================================
trades = carregar_trades_firebase()

if not trades:
    st.markdown("<h3 style='text-align:center; color:#666;'>Nenhum sinal do Alpha ou MCC no momento.</h3>", unsafe_allow_html=True)
else:
    trades.reverse() # Mais recentes no topo
    
    for trade in trades:
        ativo = trade.get("ativo", "").replace("_", "/")
        preco_atual = obter_preco_atual(ativo)
        if preco_atual is None or preco_atual == 0: continue

        entrada = float(trade.get("entrada", 0))
        alvo = float(trade.get("alvo", 0))
        direcao = trade.get("direcao", "LONG")
        nome_robo = trade.get("robo", "Desconhecido")

        if entrada == 0 or alvo == 0: continue

        # --- CÁLCULOS DE TRADING ---
        if direcao == "LONG":
            chegou_na_entrada = preco_atual <= entrada
            dist_entrada_pct = ((preco_atual - entrada) / preco_atual) * 100
            potencial_pct = ((alvo - entrada) / entrada) * 100
            pnl_pct = ((preco_atual - entrada) / entrada) * 100 if chegou_na_entrada else 0.0
            progresso = ((preco_atual - entrada) / (alvo - entrada)) * 100 if alvo > entrada else 0
        else:
            chegou_na_entrada = preco_atual >= entrada
            dist_entrada_pct = ((entrada - preco_atual) / preco_atual) * 100
            potencial_pct = ((entrada - alvo) / entrada) * 100
            pnl_pct = ((entrada - preco_atual) / entrada) * 100 if chegou_na_entrada else 0.0
            progresso = ((entrada - preco_atual) / (entrada - alvo)) * 100 if alvo < entrada else 0
            
        progresso_barra = max(0.0, min(100.0, progresso))

        # --- VISUAL DO CARD ---
        if not chegou_na_entrada:
            card_class = "trade-card trade-card-waiting"
            status_html = f'<span class="status-waiting">⏳ AGUARDANDO PULLBACK (Faltam {abs(dist_entrada_pct):.2f}%)</span>'
            pnl_class = "info"
            pnl_text = "Aguardando..."
        else:
            card_class = "trade-card" if direcao == "LONG" else "trade-card trade-card-short"
            status_html = '<span class="status-active">🔥 TRADE ATIVO</span>'
            pnl_class = "pnl" if pnl_pct >= 0 else "pnl pnl-negative"
            pnl_text = f"{pnl_pct:+.2f}%"

        emoji = "🟢" if direcao == "LONG" else "🔴"

        with st.container():
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 1.5, 1.5])
            
            with col1:
                # Adicionado o nome do robô no título para você saber de quem é o sinal
                st.markdown(f'<p class="title">{emoji} {ativo} ({direcao})</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info" style="font-size:12px; color:#888;">🤖 {nome_robo}</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Entrada (GP): <span class="info-value">{entrada}</span></p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Preço Atual: <span class="info-value">{preco_atual:.5f} ⚡</span></p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Alvo: <span class="info-value">{alvo}</span></p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Potencial de Ganho no Alvo: <span style="color:#00ffcc;">+{potencial_pct:.2f}%</span></p>', unsafe_allow_html=True)
                
            with col2:
                st.markdown('<p class="info">Progresso até o Alvo</p>', unsafe_allow_html=True)
                st.progress(progresso_barra / 100)
                st.write(f"{progresso:.1f}%")
                
            with col3:
                st.markdown(status_html, unsafe_allow_html=True)
                st.markdown('<p class="info">PnL Real (se ativo)</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="{pnl_class}">{pnl_text}</p>', unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)

st.write("---")
st.caption(f"Alpha Terminal v3.1 | Atualiza a cada 10s | Última leitura: {datetime.now().strftime('%H:%M:%S')}")

time.sleep(10)
st.rerun()

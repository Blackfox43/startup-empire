import streamlit as st
import time
import pandas as pd
import altair as alt
import json
import base64
import math
from datetime import datetime

# ==========================================
# CONFIGURATION & DATA
# ==========================================

BUSINESS_CONFIG = [
    {"id": "lemonade", "name": "Lemonade Stand", "base_cost": 15, "base_income": 1, "icon": "🍋", "desc": "Neighborhood hydration specialist."},
    {"id": "dropship", "name": "Dropshipping Store", "base_cost": 150, "base_income": 8, "icon": "📦", "desc": "Selling cheap gadgets at 500% markup."},
    {"id": "web_agency", "name": "Web Agency", "base_cost": 1500, "base_income": 45, "icon": "💻", "desc": "Building landing pages for startups."},
    {"id": "crypto_farm", "name": "Crypto Farm", "base_cost": 12000, "base_income": 200, "icon": "⛏️", "desc": "Turning electricity into speculative assets."},
    {"id": "ai_startup", "name": "AI SaaS Unicorn", "base_cost": 150000, "base_income": 1200, "icon": "🦄", "desc": "Disrupting industries with LLMs."},
    {"id": "quantum", "name": "Quantum Server", "base_cost": 2500000, "base_income": 15000, "icon": "⚛️", "desc": "Computing in parallel dimensions."},
    {"id": "mars_colony", "name": "Mars Colony", "base_cost": 45000000, "base_income": 120000, "icon": "🚀", "desc": "Interplanetary real estate."},
]

UPGRADE_CONFIG = [
    {"id": "click_1", "name": "Mechanical Keyboard", "cost": 500, "type": "click", "mult": 2, "icon": "⌨️", "desc": "x2 Click Power"},
    {"id": "auto_1", "name": "Outsource Labor", "cost": 2500, "type": "global", "mult": 1.2, "icon": "🤝", "desc": "+20% All Income"},
    {"id": "click_2", "name": "Neural Link", "cost": 50000, "type": "click", "mult": 5, "icon": "🧠", "desc": "x5 Click Power"},
    {"id": "auto_2", "name": "Tax Loopholes", "cost": 1000000, "type": "global", "mult": 1.5, "icon": "🏝️", "desc": "+50% All Income"},
    {"id": "synergy_1", "name": "Market Monopoly", "cost": 50000000, "type": "global", "mult": 2.0, "icon": "🎩", "desc": "x2 All Income"},
]

# ==========================================
# CORE CLASSES
# ==========================================

class GameState:
    def __init__(self):
        # Defaults
        self.money = 0.0
        self.lifetime_earnings = 0.0
        self.start_time = time.time()
        self.last_tick = time.time()
        
        # Assets
        self.businesses = {b['id']: 0 for b in BUSINESS_CONFIG}
        self.upgrades = []
        
        # Prestige
        self.angels = 0  # Prestige currency
        self.prestige_mult = 0.05  # 5% bonus per angel
        
        # Analytics
        self.history_time = []
        self.history_value = []

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        obj = cls()
        data = json.loads(json_str)
        for key, value in data.items():
            setattr(obj, key, value)
        return obj

# ==========================================
# GAME ENGINE LOGIC
# ==========================================

def initialize_session():
    if 'game_state' not in st.session_state:
        st.session_state.game_state = GameState()
        st.session_state.live_mode = False

def get_business_cost(base_cost, count):
    return int(base_cost * (1.15 ** count))

def calculate_rates(state):
    # 1. Base Passive
    passive_income = 0
    for b in BUSINESS_CONFIG:
        count = state.businesses.get(b['id'], 0)
        passive_income += b['base_income'] * count
    
    # 2. Apply Upgrades
    global_mult = 1.0
    click_mult = 1.0
    
    for u_id in state.upgrades:
        u_data = next((u for u in UPGRADE_CONFIG if u['id'] == u_id), None)
        if u_data:
            if u_data['type'] == 'global':
                global_mult *= u_data['mult']
            elif u_data['type'] == 'click':
                click_mult *= u_data['mult']
    
    # 3. Apply Prestige (Angels)
    angel_bonus = 1.0 + (state.angels * state.prestige_mult)
    
    final_passive = passive_income * global_mult * angel_bonus
    
    # Click power is 5% of passive income (min 1) * multipliers
    base_click = max(1, final_passive * 0.05)
    final_click = base_click * click_mult * angel_bonus
    
    return final_passive, final_click

def process_tick():
    state = st.session_state.game_state
    now = time.time()
    delta = now - state.last_tick
    
    # Logic Update
    if delta > 0:
        passive, _ = calculate_rates(state)
        earnings = passive * delta
        state.money += earnings
        state.lifetime_earnings += earnings
        state.last_tick = now
        
        # Update Chart Data (throttle to every few seconds or substantial changes)
        game_time = int(now - state.start_time)
        if not state.history_time or game_time > state.history_time[-1] + 2:
            state.history_time.append(game_time)
            state.history_value.append(state.money)
            # Keep chart data manageable
            if len(state.history_time) > 100:
                state.history_time.pop(0)
                state.history_value.pop(0)

def format_currency(amount):
    if amount >= 1e12: return f"${amount/1e12:.2f}T"
    if amount >= 1e9: return f"${amount/1e9:.2f}B"
    if amount >= 1e6: return f"${amount/1e6:.2f}M"
    if amount >= 1e3: return f"${amount/1e3:.2f}K"
    return f"${amount:,.0f}"

# ==========================================
# UI RENDERING
# ==========================================

st.set_page_config(page_title="Startup Empire Advanced", page_icon="📈", layout="wide")

# Custom CSS for Cyberpunk/Dark Mode feel
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-family: 'Courier New', monospace; color: #00ff41; }
    button[kind="primary"] { border: 1px solid #00ff41; background-color: rgba(0, 255, 65, 0.1); color: #00ff41; }
    button[kind="primary"]:hover { border: 1px solid #fff; background-color: rgba(0, 255, 65, 0.4); color: #fff; }
    .business-card { padding: 10px; border: 1px solid #333; border-radius: 8px; margin-bottom: 10px; background-color: #161b22; }
</style>
""", unsafe_allow_html=True)

initialize_session()
process_tick() # Calculate earnings since last refresh

state = st.session_state.game_state
passive_rate, click_rate = calculate_rates(state)

# --- SIDEBAR: CONTROLS ---
with st.sidebar:
    st.title("🚀 Empire OS v2.0")
    
    # Live Mode Toggle
    live_mode = st.toggle("Live Mode (Auto-Refresh)", value=st.session_state.live_mode)
    st.session_state.live_mode = live_mode
    if live_mode:
        time.sleep(1)
        st.rerun()

    st.divider()
    
    # Save/Load System
    with st.expander("💾 Save / Load"):
        # Generate Save String
        json_str = state.to_json()
        b64_str = base64.b64encode(json_str.encode()).decode()
        st.text_input("Your Save Code (Copy this):", value=b64_str, key="save_display")
        
        # Load Save String
        load_str = st.text_input("Paste Save Code:", key="load_input")
        if st.button("Load Game"):
            try:
                decoded = base64.b64decode(load_str).decode()
                st.session_state.game_state = GameState.from_json(decoded)
                st.success("Game Loaded!")
                time.sleep(1)
                st.rerun()
            except:
                st.error("Invalid Code")
                
    # PRESTIGE SYSTEM
    st.divider()
    st.subheader("👼 Angel Investors")
    
    # Formula: sqrt(lifetime_earnings / 1,000,000)
    potential_angels = int(math.sqrt(max(0, state.lifetime_earnings / 1_000_000)))
    current_angels = state.angels
    claimable = max(0, potential_angels - current_angels)
    
    st.write(f"**Current Angels:** {current_angels}")
    st.write(f"**Bonus:** +{int(current_angels * state.prestige_mult * 100)}% Global Income")
    
    if claimable > 0:
        st.success(f"Claimable: +{claimable} Angels")
        if st.button("🔴 SELL COMPANY & PRESTIGE", help="Resets money and buildings. Keeps Angels and Upgrades."):
            # Prestige Logic
            new_angels = current_angels + claimable
            # Reset
            st.session_state.game_state = GameState()
            st.session_state.game_state.angels = new_angels
            # Optional: Keep upgrades or not? Hardcore mode = reset upgrades too. Let's keep them for fun.
            st.session_state.game_state.upgrades = state.upgrades 
            st.rerun()
    else:
        st.caption(f"Need {format_currency((potential_angels+1)**2 * 1000000)} lifetime earnings for next Angel.")

# --- MAIN DASHBOARD ---

# Top Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Liquid Assets", format_currency(state.money))
c2.metric("Net Worth", format_currency(state.lifetime_earnings))
c3.metric("Passive Income", f"{format_currency(passive_rate)} /s")
c4.metric("Click Value", format_currency(click_rate))

# Main Tabs
tab1, tab2, tab3 = st.tabs(["🏢 Operations", "🔬 R&D Lab", "📊 Analytics"])

with tab1:
    # Big Clicker
    if st.button(f"MANUAL WORK (+{format_currency(click_rate)})", type="primary", use_container_width=True):
        state.money += click_rate
        state.lifetime_earnings += click_rate
        # Trigger minimal refresh
        st.rerun()

    st.write("---")

    # Business List
    for b in BUSINESS_CONFIG:
        b_id = b['id']
        count = state.businesses.get(b_id, 0)
        cost = get_business_cost(b['base_cost'], count)
        can_afford = state.money >= cost
        
        # Layout
        col_icon, col_info, col_btn = st.columns([1, 4, 2])
        
        with col_icon:
            st.markdown(f"<h1 style='text-align: center; margin: 0;'>{b['icon']}</h1>", unsafe_allow_html=True)
            
        with col_info:
            st.markdown(f"**{b['name']}** (Lvl {count})")
            st.caption(b['desc'])
            st.caption(f"Income: {format_currency(b['base_income'] * count)}/s")
            
        with col_btn:
            btn_label = f"Buy: {format_currency(cost)}"
            if st.button(btn_label, key=f"buy_{b_id}", disabled=not can_afford, use_container_width=True):
                state.money -= cost
                state.businesses[b_id] += 1
                st.toast(f"Bought {b['name']}!", icon=b['icon'])
                st.rerun()
        
        st.markdown("<hr style='margin: 5px 0; opacity: 0.2;'>", unsafe_allow_html=True)

with tab2:
    st.subheader("Available Upgrades")
    cols = st.columns(2)
    
    for i, u in enumerate(UPGRADE_CONFIG):
        u_id = u['id']
        owned = u_id in state.upgrades
        can_afford = state.money >= u['cost']
        
        with cols[i % 2]:
            container_border = True
            if owned:
                st.success(f"✅ {u['name']} (Active)")
            else:
                with st.container(border=True):
                    st.markdown(f"**{u['icon']} {u['name']}**")
                    st.caption(u['desc'])
                    if st.button(f"Research {format_currency(u['cost'])}", key=f"upg_{u_id}", disabled=not can_afford):
                        state.money -= u['cost']
                        state.upgrades.append(u_id)
                        st.balloons()
                        st.rerun()

with tab3:
    st.subheader("Financial Trajectory")
    
    if len(state.history_value) > 1:
        # Create Dataframe for Altair
        df = pd.DataFrame({
            'Time': state.history_time,
            'Net Worth': state.history_value
        })
        
        # Area Chart
        chart = alt.Chart(df).mark_area(
            line={'color':'#00ff41'},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='#00ff41', offset=0),
                       alt.GradientStop(color='rgba(0, 255, 65, 0)', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x='Time',
            y='Net Worth',
            tooltip=['Time', 'Net Worth']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Play for a few seconds to generate data.")

    # Asset Distribution
    st.subheader("Asset Portfolio")
    dist_data = []
    for b in BUSINESS_CONFIG:
        count = state.businesses.get(b['id'], 0)
        if count > 0:
            dist_data.append({"Asset": b['name'], "Count": count})
            
    if dist_data:
        df_dist = pd.DataFrame(dist_data)
        pie = alt.Chart(df_dist).mark_arc(innerRadius=50).encode(
            theta="Count",
            color="Asset",
            tooltip=["Asset", "Count"]
        )
        st.altair_chart(pie, use_container_width=True)

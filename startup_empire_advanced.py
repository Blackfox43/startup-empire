import streamlit as st
import time
import pandas as pd
import altair as alt
import json
import base64
import math
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# DATABASE CONNECTION (CRITICAL SECTION - FIXED)
# ==========================================

# Use a Streamlit singleton pattern to initialize Firebase only once
if not firebase_admin._apps:
    cloud_config = st.secrets.get("firebase")
    
    if cloud_config:
        try:
            # Assemble the credentials dictionary from individual secrets fields
            # This is more robust than parsing a single large JSON string
            key_dict = {
                "type": cloud_config["type"],
                "project_id": cloud_config["project_id"],
                "private_key_id": cloud_config["private_key_id"],
                # The private_key is now correctly read as a multi-line string
                "private_key": cloud_config["private_key"], 
                "client_email": cloud_config["client_email"],
                "client_id": cloud_config["client_id"],
                "auth_uri": cloud_config["auth_uri"],
                "token_uri": cloud_config["token_uri"],
                "auth_provider_x509_cert_url": cloud_config["auth_provider_x509_cert_url"],
                "client_x509_cert_url": cloud_config["client_x509_cert_url"],
            }

            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            st.toast("Cloud Database Connected!", icon="☁️")
        except Exception as e:
            st.error(f"🚨 Firebase Initialization Failed. Check secret keys under [firebase]. Error: {e}")
    else:
        st.warning("⚠️ Firebase secret [firebase] section not found. Running in local-only mode.")
        
# Initialize Firestore client only if Firebase is initialized
if firebase_admin._apps:
    db = firestore.client()
else:
    db = None # Use this as a guard clause in cloud functions

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
# CORE CLASSES (Game State)
# ==========================================

class GameState:
    def __init__(self):
        # Ensure all required attributes are initialized here to avoid errors
        self.money = 0.0
        self.lifetime_earnings = 0.0
        self.start_time = time.time()
        self.last_tick = time.time()
        self.businesses = {b['id']: 0 for b in BUSINESS_CONFIG}
        self.upgrades = []
        self.angels = 0
        self.prestige_mult = 0.05
        self.history_time = [0]
        self.history_value = [0]

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        obj = cls()
        data = json.loads(json_str)
        # Safely set attributes, handling keys that might not exist in older saves
        for key, value in data.items():
            setattr(obj, key, value)
        return obj

# ==========================================
# CLOUD SAVE/LOAD FUNCTIONS
# ==========================================

def save_to_cloud(username, game_state_dict):
    """Saves the current game state to Firestore"""
    if not db: return st.error("Database unavailable.")
    doc_ref = db.collection("players").document(username)
    
    # Store history data separately to avoid hitting document size limits if history gets huge
    doc_data = {k: v for k, v in game_state_dict.items() if k not in ['history_time', 'history_value']}
    doc_ref.set(doc_data)
    
    st.toast("☁️ Game Saved to Cloud!", icon="💾")

def load_from_cloud(username):
    """Loads game state from Firestore"""
    if not db: return st.error("Database unavailable.")
    doc_ref = db.collection("players").document(username)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        # Ensure list fields are initialized if they were skipped in old save files
        data['history_time'] = [0]
        data['history_value'] = [0]
        return data
    else:
        return None

def get_leaderboard():
    """Fetches top 10 players by Net Worth"""
    if not db: return []
    try:
        users_ref = db.collection("players")
        # Requires a composite index in Firestore for 'lifetime_earnings' DESC
        query = users_ref.order_by("lifetime_earnings", direction=firestore.Query.DESCENDING).limit(10)
        results = query.stream()
        
        leaderboard_data = []
        for doc in results:
            data = doc.to_dict()
            leaderboard_data.append({
                "CEO": doc.id,
                "Net Worth": data.get('lifetime_earnings', 0),
                "Angels": data.get('angels', 0)
            })
        return leaderboard_data
    except Exception as e:
        # Provide a more specific warning for index errors
        st.warning(f"⚠️ Leaderboard index error. You may need to create a Firestore index for 'lifetime_earnings' DESC. Details: {e}")
        return []


# ==========================================
# GAME ENGINE LOGIC 
# ==========================================

def initialize_session():
    # Only initialize if the key is missing
    if 'game_state' not in st.session_state:
        st.session_state.game_state = GameState()
    if 'live_mode' not in st.session_state:
        st.session_state.live_mode = False
    if 'username' not in st.session_state:
        st.session_state.username = ""

def get_business_cost(base_cost, count):
    return int(base_cost * (1.15 ** count))

def calculate_rates(state):
    passive_income = 0
    for b in BUSINESS_CONFIG:
        count = state.businesses.get(b['id'], 0)
        passive_income += b['base_income'] * count
    
    global_mult = 1.0
    click_mult = 1.0
    
    for u_id in state.upgrades:
        u_data = next((u for u in UPGRADE_CONFIG if u['id'] == u_id), None)
        if u_data:
            if u_data['type'] == 'global':
                global_mult *= u_data['mult']
            elif u_data['type'] == 'click':
                click_mult *= u_data['mult']
    
    angel_bonus = 1.0 + (state.angels * state.prestige_mult)
    
    final_passive = passive_income * global_mult * angel_bonus
    
    base_click = max(1, final_passive * 0.05)
    final_click = base_click * click_mult * angel_bonus
    
    return final_passive, final_click

def process_tick():
    state = st.session_state.game_state
    now = time.time()
    delta = now - state.last_tick
    
    if delta > 0:
        passive, _ = calculate_rates(state)
        earnings = passive * delta
        state.money += earnings
        state.lifetime_earnings += earnings
        state.last_tick = now
        
        game_time = int(now - state.start_time)
        if not state.history_time or game_time > state.history_time[-1] + 2:
            state.history_time.append(game_time)
            state.history_value.append(state.money)
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

st.set_page_config(page_title="Startup Empire Advanced Cloud", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-family: 'Courier New', monospace; color: #00ff41; }
    button[kind="primary"] { border: 1px solid #00ff41; background-color: rgba(0, 255, 65, 0.1); color: #00ff41; }
    button[kind="primary"]:hover { border: 1px solid #fff; background-color: rgba(0, 255, 65, 0.4); color: #fff; }
</style>
""", unsafe_allow_html=True)

initialize_session()
process_tick()

# Define the 'state' shortcut variable here for use throughout the script
state = st.session_state.game_state
passive_rate, click_rate = calculate_rates(state)

# --- SIDEBAR: CONTROLS ---
with st.sidebar:
    st.title("🚀 Empire OS v3.0 (Cloud)")
    
    # -------------------
    # Cloud HQ Section
    # -------------------
    st.subheader("☁️ Cloud HQ")
    
    # Simple Login System
    new_username = st.text_input("Enter CEO Name (ID)", value=st.session_state.username, key="login_input")
    st.session_state.username = new_username
    
    cloud_connected = (db is not None)
    
    col_save, col_load = st.columns(2)
    with col_save:
        if st.button("Save to Cloud", disabled=not cloud_connected or not new_username):
            data_to_save = st.session_state.game_state.__dict__
            save_to_cloud(new_username, data_to_save)

    with col_load:
        if st.button("Load from Cloud", disabled=not cloud_connected or not new_username):
            cloud_data = load_from_cloud(new_username)
            if isinstance(cloud_data, dict):
                st.session_state.game_state = GameState()
                for k, v in cloud_data.items():
                    setattr(st.session_state.game_state, k, v)
                st.success(f"Welcome back, CEO {new_username}!")
                st.rerun()
            elif cloud_data is None:
                st.warning("User not found. Starting a new game.")
            
    st.divider()
    
    # Live Mode Toggle
    live_mode = st.toggle("Live Mode (Auto-Refresh)", value=st.session_state.live_mode)
    st.session_state.live_mode = live_mode

    # Prestige System
    st.subheader("👼 Angel Investors")
    potential_angels = int(math.sqrt(max(0, state.lifetime_earnings / 1_000_000)))
    current_angels = state.angels
    claimable = max(0, potential_angels - current_angels)
    
    st.write(f"**Current Angels:** {current_angels}")
    st.write(f"**Bonus:** +{int(current_angels * state.prestige_mult * 100)}% Global Income")
    
    if claimable > 0:
        st.success(f"Claimable: +{claimable} Angels")
        if st.button("🔴 SELL COMPANY & PRESTIGE", help="Resets money and buildings. Keeps Angels and Upgrades."):
            new_angels = current_angels + claimable
            st.session_state.game_state = GameState()
            st.session_state.game_state.angels = new_angels
            st.session_state.game_state.upgrades = state.upgrades 
            st.rerun()
    else:
        st.caption(f"Need {format_currency((potential_angels+1)**2 * 1000000)} lifetime earnings for next Angel.")

# --- MAIN DASHBOARD ---

c1, c2, c3, c4 = st.columns(4)
c1.metric("Liquid Assets", format_currency(state.money))
c2.metric("Net Worth", format_currency(state.lifetime_earnings))
c3.metric("Passive Income", f"{format_currency(passive_rate)} /s")
c4.metric("Click Value", format_currency(click_rate))

tab1, tab2, tab3, tab4 = st.tabs(["🏢 Operations", "🔬 R&D Lab", "📊 Analytics", "🏆 World Rankings"])

with tab1:
    if st.button(f"MANUAL WORK (+{format_currency(click_rate)})", type="primary", use_container_width=True):
        state.money += click_rate
        state.lifetime_earnings += click_rate
        st.rerun()

    st.write("---")

    for b in BUSINESS_CONFIG:
        b_id = b['id']
        count = state.businesses.get(b_id, 0)
        cost = get_business_cost(b['base_cost'], count)
        can_afford = state.money >= cost
        
        col_icon, col_info, col_btn = st.columns([1, 4, 2])
        
        with col_icon:
            st.markdown(f"<h1 style='text-align: center; margin: 0;'>{b['icon']}</h1>", unsafe_allow_html=True)
            
        with col_info:
            st.markdown(f"**{b['name']}** (Lvl {count})")
            st.caption(b['desc'])
            # Simplified income calculation for display
            base_income_calc = b['base_income'] * count * (1.0 + state.angels * state.prestige_mult)
            final_income_display = base_income_calc * calculate_rates(state)[0] / (calculate_rates(state)[0] if calculate_rates(state)[0] > 0 else 1)
            st.caption(f"Income: {format_currency(final_income_display)}/s")
            
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
        df = pd.DataFrame({'Time': state.history_time, 'Net Worth': state.history_value})
        chart = alt.Chart(df).mark_area(
            line={'color':'#00ff41'},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='#00ff41', offset=0),
                       alt.GradientStop(color='rgba(0, 255, 65, 0)', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x='Time', y='Net Worth', tooltip=['Time', 'Net Worth']
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Play for a few seconds to generate data.")

    st.subheader("Asset Portfolio")
    dist_data = []
    for b in BUSINESS_CONFIG:
        count = state.businesses.get(b['id'], 0)
        if count > 0:
            dist_data.append({"Asset": b['name'], "Count": count})
            
    if dist_data:
        df_dist = pd.DataFrame(dist_data)
        pie = alt.Chart(df_dist).mark_arc(innerRadius=50).encode(
            theta="Count", color="Asset", tooltip=["Asset", "Count"]
        )
        st.altair_chart(pie, use_container_width=True)

with tab4:
    st.subheader("🏆 Global Top CEOs")
    
    if st.button("Refresh Rankings"):
        lb_data = get_leaderboard()
        if lb_data:
            df = pd.DataFrame(lb_data)
            df['Net Worth'] = df['Net Worth'].apply(format_currency)
            df['Rank'] = range(1, len(df) + 1)
            
            st.dataframe(
                df[['Rank', 'CEO', 'Net Worth', 'Angels']], 
                use_container_width=True, 
                hide_index=True
            )
        elif db is None:
            st.warning("Cannot fetch leaderboard: Database connection failed.")
        else:
            st.info("No players ranked yet. Be the first!")

# --- Auto Refresh Footer --- 
if st.session_state.live_mode or state.money < 1000:
    time.sleep(1)
    st.rerun()

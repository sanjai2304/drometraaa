import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster, HeatMap
import datetime
import plotly.express as px
import plotly.graph_objects as go

# Set Page Config
st.set_page_config(
    page_title="AstraTraffic AI - Bengaluru Congestion Intelligence System",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Custom Safe Label Encoder Class Definition
# ---------------------------------------------------------
class SafeLabelEncoder:
    def __init__(self, default_val=-1):
        self.classes_ = None
        self.mapping_ = {}
        self.inverse_mapping_ = {}
        self.default_val = default_val
    
    def fit(self, s):
        unique_vals = sorted(pd.Series(s).dropna().astype(str).unique())
        self.classes_ = unique_vals
        self.mapping_ = {val: idx for idx, val in enumerate(unique_vals)}
        self.inverse_mapping_ = {idx: val for idx, val in enumerate(unique_vals)}
        return self
    
    def transform(self, s):
        return pd.Series(s).astype(str).map(self.mapping_).fillna(self.default_val).astype(int)
    
    def fit_transform(self, s):
        self.fit(s)
        return self.transform(s)
        
    def inverse_transform(self, s):
        return pd.Series(s).map(self.inverse_mapping_).fillna("Unknown")

# ---------------------------------------------------------
# Custom Premium Styling (Dark / Glassmorphism Theme)
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* Main Background & Text Color */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #111827 !important;
        border-right: 1px solid #1f2937;
    }
    
    /* Headers */
    h1, h2, h3, h4 {
        color: #38bdf8 !important;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    
    .gradient-text {
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    
    /* Custom KPI Cards Grid */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 15px;
        margin-bottom: 25px;
    }
    .kpi-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(56, 189, 248, 0.1);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        flex-direction: column;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
    }
    .kpi-card:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: rgba(56, 189, 248, 0.3);
        box-shadow: 0 20px 30px -10px rgba(56, 189, 248, 0.2);
    }
    .kpi-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
    }
    .kpi-icon {
        font-size: 24px;
        background: rgba(56, 189, 248, 0.1);
        padding: 8px;
        border-radius: 8px;
        color: #38bdf8;
    }
    .kpi-title {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #ffffff;
        margin-top: 5px;
    }
    
    /* Card Container Panels */
    .card-panel {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
        transition: transform 0.3s ease;
    }
    .card-panel:hover {
        transform: translateY(-2px);
    }
    
    /* Recommendation Card styling */
    .rec-item {
        background: rgba(30, 41, 59, 0.9);
        border-left: 5px solid #38bdf8;
        padding: 15px;
        border-radius: 4px 12px 12px 4px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
        transition: all 0.2s ease;
    }
    .rec-item:hover {
        transform: scale(1.01);
        background: rgba(30, 41, 59, 1);
    }
    
    /* Risk Badges */
    .risk-low {
        background-color: rgba(16, 185, 129, 0.15);
        border: 1px solid #10b981;
        color: #10b981;
        padding: 10px 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 20px;
        letter-spacing: 1px;
    }
    .risk-medium {
        background-color: rgba(245, 158, 11, 0.15);
        border: 1px solid #f59e0b;
        color: #f59e0b;
        padding: 10px 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 20px;
        letter-spacing: 1px;
    }
    .risk-high {
        background-color: rgba(239, 68, 68, 0.15);
        border: 1px solid #ef4444;
        color: #ef4444;
        padding: 10px 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 20px;
        letter-spacing: 1px;
    }
    .risk-critical {
        background-color: rgba(220, 38, 38, 0.25);
        border: 2px solid #dc2626;
        color: #fca5a5;
        padding: 12px 18px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 22px;
        letter-spacing: 1px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 0.9; }
        50% { opacity: 0.6; }
        100% { opacity: 0.9; }
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Load Pre-trained Models and Scalers
# ---------------------------------------------------------
@st.cache_resource
def load_ml_resources():
    resources = {}
    try:
        resources['severity_model'] = joblib.load("models/final_severity_model.joblib")
        resources['spread_model'] = joblib.load("models/spread_prediction_model.joblib")
        resources['road_model'] = joblib.load("models/geofencing_road_model.joblib")
        resources['encoders'] = joblib.load("models/label_encoders.joblib")
        return resources, True
    except Exception as e:
        return str(e), False

resources, models_loaded = load_ml_resources()

# Load dataset and calculate metrics
@st.cache_data
def load_dataset():
    if os.path.exists("models/engineered_dataset.parquet"):
        df_parquet = pd.read_parquet("models/engineered_dataset.parquet")
    else:
        df_parquet = pd.read_csv("dataset/Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv")
        df_parquet['start_datetime'] = pd.to_datetime(df_parquet['start_datetime'], errors='coerce')
        df_parquet['closed_datetime'] = pd.to_datetime(df_parquet['closed_datetime'], errors='coerce')
        df_parquet = df_parquet.dropna(subset=['start_datetime', 'latitude', 'longitude']).copy()
        df_parquet = df_parquet.sort_values('start_datetime').reset_index(drop=True)
        
    df_parquet['duration_minutes'] = (df_parquet['closed_datetime'] - df_parquet['start_datetime']).dt.total_seconds() / 60.0
    df_parquet['duration_minutes'] = df_parquet['duration_minutes'].fillna(64.5)
    
    if 'hour' not in df_parquet.columns:
        df_parquet['hour'] = df_parquet['start_datetime'].dt.hour
    if 'weekday' not in df_parquet.columns:
        df_parquet['weekday'] = df_parquet['start_datetime'].dt.weekday
        
    # Calculate 0-100 Event Impact Score for whole dataset
    prio_val = df_parquet['priority'].apply(lambda x: 25 if str(x).lower() == 'high' else 5)
    closure_val = df_parquet['requires_road_closure'].apply(lambda x: 20 if x else 0)
    dur_val = df_parquet['duration_minutes'].apply(lambda x: min(x, 180) / 180 * 20)
    type_val = df_parquet['event_type'].apply(lambda x: 10 if str(x).lower() == 'unplanned' else 5)
    
    zone_counts = df_parquet['zone'].value_counts()
    zone_high_counts = df_parquet[df_parquet['priority'].str.lower() == 'high']['zone'].value_counts()
    
    density_val = df_parquet['zone'].map(lambda x: min(zone_counts.get(x, 0), 1000) / 1000 * 10)
    
    def get_hist_sev(z):
        total = zone_counts.get(z, 0)
        high = zone_high_counts.get(z, 0)
        return (high / total * 15) if total > 0 else 7.5
        
    hist_sev_val = df_parquet['zone'].map(get_hist_sev)
    
    df_parquet['event_impact_score_100'] = (prio_val + closure_val + dur_val + type_val + density_val + hist_sev_val).round().astype(int)
    
    # Calculate congestion risk score for whole dataset
    df_parquet['congestion_risk_score'] = (
        df_parquet['priority'].apply(lambda x: 60 if str(x).lower() == 'high' else 10) +
        df_parquet['is_spread'] * 25 +
        df_parquet['requires_road_closure'].apply(lambda x: 15 if x else 0)
    )
    
    return df_parquet

df = load_dataset()

# ---------------------------------------------------------
# Top Header Section (Responsive & Enterprise-Grade)
# ---------------------------------------------------------
current_time_str = datetime.datetime.now().strftime("%a, %b %d, %Y | %H:%M:%S")

st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 20px; background: linear-gradient(90deg, #111827 0%, #1e293b 100%); padding: 25px; border-radius: 16px; border: 1px solid rgba(56, 189, 248, 0.1); margin-bottom: 30px;">
        <div style="font-size: 48px;">🚦</div>
        <div style="flex-grow: 1;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <h1 style="margin: 0; font-size: 32px; font-weight: 800; color: #ffffff;"><span class="gradient-text">AstraTraffic AI</span></h1>
                <span style="background: #ef4444; color: white; font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Live Command Center</span>
            </div>
            <div style="color: #94a3b8; font-size: 16px; margin-top: 4px; font-weight: 500;">
                AI-Powered Bengaluru Traffic Command Center (Event-Driven Congestion Intelligence)
            </div>
        </div>
        <div style="text-align: right; border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">
            <div style="color: #38bdf8; font-weight: bold; font-size: 14px;">BENGALURU SMART CITY</div>
            <div style="color: #ffffff; font-size: 18px; font-weight: 600; margin-top: 2px;">{current_time_str}</div>
            <div style="color: #94a3b8; font-size: 12px;">System Status: <span style="color: #10b981; font-weight: bold;">● Operational</span></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar Navigation (Icons & Layout)
# ---------------------------------------------------------
st.sidebar.markdown("### 🗺️ System Menu")
page = st.sidebar.radio(
    "Select Interface Page", 
    [
        "🏠 Dashboard", 
        "🔮 Real-Time Predictor", 
        "🗺 Geospatial Map", 
        "📊 Analytics",
        "⚙ AI Recommendations"
    ]
)

# ---------------------------------------------------------
# Dynamic KPI Calculation
# ---------------------------------------------------------
total_events = len(df)
high_prio = (df['priority'].str.lower() == 'high').sum()
active_incidents = (df['status'].str.lower() == 'active').sum()
road_closures = (df['requires_road_closure'] == True).sum()
avg_impact = int(df['event_impact_score_100'].mean())
high_critical_risk = (df['congestion_risk_score'] >= 60).sum()
congestion_risk_idx = int((high_critical_risk / total_events) * 100)

# Render KPI Cards (Phase 10 & Dashboard Cards requirement)
st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Total Reports</span>
                <span class="kpi-icon">📁</span>
            </div>
            <span class="kpi-value">{total_events:,}</span>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">High Severity</span>
                <span class="kpi-icon">🚨</span>
            </div>
            <span class="kpi-value">{high_prio:,}</span>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Active Live</span>
                <span class="kpi-icon">📡</span>
            </div>
            <span class="kpi-value">{active_incidents:,}</span>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Road Closures</span>
                <span class="kpi-icon">🚧</span>
            </div>
            <span class="kpi-value">{road_closures:,}</span>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Avg. Impact</span>
                <span class="kpi-icon">⚡</span>
            </div>
            <span class="kpi-value">{avg_impact} / 100</span>
        </div>
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Congestion Index</span>
                <span class="kpi-icon">📈</span>
            </div>
            <span class="kpi-value">{congestion_risk_idx}%</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Page 1: 🏠 Dashboard
# ---------------------------------------------------------
if page == "🏠 Dashboard":
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        st.markdown("<div class='card-panel'>", unsafe_allow_html=True)
        st.markdown("#### 💡 Bengaluru Smart City & AI Command Center Objective")
        st.write("""
        Bengaluru’s arterial network connects millions of commuters daily. Spontaneous events—such as breakdowns, accidents, waterlogging, or tree falls—trigger gridlocks that spread across adjacent junctions.
        
        **AstraTraffic AI** provides a real-time Decision Support System for Bengaluru Traffic Police (BTP) using machine learning pipelines to:
        * **Predict incident priority and severity** to dispatch resources.
        * **Map and geofence GPS coordinate feeds** to Bengaluru's 22 key traffic corridors.
        * **Assess spatial-temporal congestion risk** of propagation and gridlock spread.
        * **Generate immediate actionable SOP checklists** (manual routing, tow deployment, signal timing overrides).
        """)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Interactive Dark Table (Phase 10 and Tables requirement)
        st.markdown("#### 🔔 Recent Incidents & Triage Feed")
        
        # Filters and search for the table
        search_query = st.text_input("🔍 Search incidents by corridor, cause, or junction", "")
        
        table_df = df.copy()
        if search_query:
            table_df = table_df[
                table_df['corridor'].str.contains(search_query, case=False, na=False) |
                table_df['event_cause'].str.contains(search_query, case=False, na=False) |
                table_df['junction'].str.contains(search_query, case=False, na=False)
            ]
            
        recent_df = table_df.sort_values('start_datetime', ascending=False).head(10)
        
        # Format table cols for display
        display_cols = ['start_datetime', 'event_cause', 'priority', 'corridor', 'junction', 'event_impact_score_100']
        display_df = recent_df[display_cols].copy()
        display_df.columns = ['Start Time', 'Trigger Cause', 'Priority', 'Corridor', 'Junction', 'Impact Score (0-100)']
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        st.write("💡 *Use the search box above or hover over column headers to sort the table feed.*")
        
    with col_right:
        st.markdown("<div class='card-panel'>", unsafe_allow_html=True)
        st.markdown("#### 🛠️ Trigger Cause Distribution")
        cause_counts = df['event_cause'].value_counts().head(8).reset_index()
        fig = px.pie(
            cause_counts, 
            values='count', 
            names='event_cause', 
            hole=0.45,
            color_discrete_sequence=px.colors.sequential.Plotly3
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0'),
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", y=-0.1)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# Page 2: 🔮 Real-Time Predictor
# ---------------------------------------------------------
elif page == "🔮 Real-Time Predictor":
    st.markdown("### 🔮 Incident Risk Predictor Form")
    
    if not models_loaded:
        st.error(f"Failed to load ML models. Details: {resources}")
        st.stop()
        
    encoder_dict = resources['encoders']
    severity_model = resources['severity_model']
    spread_model = resources['spread_model']
    road_model = resources['road_model']
    
    # Pre-populate lists for dropdowns
    unique_zones = sorted(df['zone'].dropna().unique())
    
    with st.form("predictor_form"):
        st.markdown("#### 📝 Simulate Local Incident")
        c1, c2 = st.columns(2)
        with c1:
            event_type_choice = st.selectbox("Event Type", sorted(df['event_type'].unique()))
            event_cause_choice = st.selectbox("Event Cause", sorted(df['event_cause'].unique()))
            priority_choice = st.selectbox("Priority Level", ["High", "Low"])
            requires_closure_choice = st.selectbox("Requires Road Closure", ["No", "Yes"])
        with c2:
            zone_choice = st.selectbox("Municipal Zone", unique_zones)
            zone_junctions = df[df['zone'] == zone_choice]['junction'].dropna().unique()
            if len(zone_junctions) == 0:
                zone_junctions = df['junction'].dropna().unique()
            junction_choice = st.selectbox("Junction Name", sorted(zone_junctions))
            
            # Temporal parameters
            date_input = st.date_input("Start Date", datetime.date.today())
            time_input = st.time_input("Start Time", datetime.datetime.now().time())
            duration_input = st.number_input("Est. Duration (Minutes)", min_value=1, max_value=1440, value=60)
            
        submit_btn = st.form_submit_button("💡 Run AI Traffic Inference")
        
    if submit_btn:
        with st.spinner("Executing model pipeline..."):
            # 1. Dataset Driven Lookup for coordinates and hidden features
            match = df[df['junction'] == junction_choice]
            if len(match) == 0:
                match = df[df['zone'] == zone_choice]
            
            if len(match) > 0:
                lat_input = float(match['latitude'].mean())
                lon_input = float(match['longitude'].mean())
                corridor_choice = match['corridor'].mode()[0] if not match['corridor'].mode().empty else 'Non-corridor'
                police_station_choice = match['police_station'].mode()[0] if not match['police_station'].mode().empty else 'Unknown'
                gba_choice = match['gba_identifier'].mode()[0] if not match['gba_identifier'].mode().empty else 'Unknown'
                veh_type_choice = match['veh_type'].mode()[0] if not match['veh_type'].mode().empty else 'Unknown'
            else:
                lat_input = float(df['latitude'].mean())
                lon_input = float(df['longitude'].mean())
                corridor_choice = 'Non-corridor'
                police_station_choice = 'Unknown'
                gba_choice = 'Unknown'
                veh_type_choice = 'Unknown'
            
            # 2. Extract Temporal parameters
            dt = datetime.datetime.combine(date_input, time_input)
            hour = dt.hour
            weekday = dt.weekday()
            month = dt.month
            is_weekend = 1 if weekday >= 5 else 0
            rush_hour = 1 if (8 <= hour <= 11) or (17 <= hour <= 20) else 0
            
            # Weather impact mapping
            weather_impact_score = 0.0
            c = event_cause_choice.lower()
            if 'water_logging' in c:
                weather_impact_score = 2.5
            elif 'tree_fall' in c:
                weather_impact_score = 2.0
            elif 'fog' in c or 'visibility' in c:
                weather_impact_score = 1.5
            elif 'rain' in c:
                weather_impact_score = 1.5
            
            # Estimated traffic pressure and density
            corr_hist = df[df['corridor'] == corridor_choice]
            est_pressure = int(corr_hist['traffic_pressure_score'].median()) if len(corr_hist) > 0 else 1
            est_density = int(df[df['police_station'] == police_station_choice].shape[0])
            
            # 3. Label encoding
            event_type_enc = encoder_dict['event_type'].transform([event_type_choice])[0]
            event_cause_enc = encoder_dict['event_cause'].transform([event_cause_choice])[0]
            veh_type_enc = encoder_dict['veh_type'].transform([veh_type_choice])[0]
            corridor_enc = encoder_dict['corridor'].transform([corridor_choice])[0]
            ps_enc = encoder_dict['police_station'].transform([police_station_choice])[0]
            zone_enc = encoder_dict['zone'].transform([zone_choice])[0]
            gba_enc = encoder_dict['gba_identifier'].transform([gba_choice])[0]
            junction_enc = encoder_dict['junction'].transform([junction_choice])[0]
            
            # 4. Formulate input row
            requires_closure_val = 1 if requires_closure_choice == "Yes" else 0
            model_feats = [
                lat_input, lon_input, requires_closure_val,
                event_type_enc, event_cause_enc, veh_type_enc,
                corridor_enc, ps_enc, zone_enc,
                gba_enc, junction_enc,
                hour, weekday, month, is_weekend, rush_hour,
                weather_impact_score, est_pressure, est_density
            ]
            
            # Formulate feature list matching model columns
            features_list = [
                'latitude', 'longitude', 'requires_road_closure', 
                'event_type_encoded', 'event_cause_encoded', 'veh_type_encoded', 
                'corridor_encoded', 'police_station_encoded', 'zone_encoded', 
                'gba_identifier_encoded', 'junction_encoded',
                'hour', 'weekday', 'month', 'is_weekend', 'rush_hour',
                'weather_impact_score', 'traffic_pressure_score', 'event_density_score'
            ]
            input_df = pd.DataFrame([model_feats], columns=features_list)
            
            # 5. Run ML predictions
            severity_prob = severity_model.predict_proba(input_df)[0][1]
            spread_prob = spread_model.predict_proba(input_df)[0][1]
            
            # 6. Event Impact Score Calculation (Phase 3)
            prio_pts = 25 if priority_choice == "High" else 5
            closure_pts = 20 if requires_closure_choice == "Yes" else 0
            dur_pts = min(duration_input, 180) / 180 * 20
            type_pts = 10 if event_type_choice.lower() == "unplanned" else 5
            
            zone_events_cnt = df[df['zone'] == zone_choice].shape[0]
            density_pts = min(zone_events_cnt, 1000) / 1000 * 10
            
            zone_high_cnt = df[(df['zone'] == zone_choice) & (df['priority'].str.lower() == 'high')].shape[0]
            hist_sev_ratio = zone_high_cnt / zone_events_cnt if zone_events_cnt > 0 else 0.5
            hist_sev_pts = hist_sev_ratio * 15
            
            impact_score = int(prio_pts + closure_pts + dur_pts + type_pts + density_pts + hist_sev_pts)
            impact_score = min(max(impact_score, 0), 100)
            
            if impact_score <= 30:
                impact_cat = "Low"
                impact_color = "#10b981"
            elif impact_score <= 70:
                impact_cat = "Medium"
                impact_color = "#f59e0b"
            else:
                impact_cat = "High"
                impact_color = "#ef4444"
                
            # Circular progress SVG offset
            offset = int(377 * (1 - impact_score / 100.0))
            
            # 7. Congestion Risk Calculation (Phase 4)
            risk_score = (severity_prob * 60) + (spread_prob * 25) + (requires_closure_val * 15)
            
            if risk_score < 30:
                risk_level = "LOW"
                risk_class = "risk-low"
                risk_color = "#10b981"
                confidence = (1 - severity_prob) * 100
            elif risk_score < 60:
                risk_level = "MEDIUM"
                risk_class = "risk-medium"
                risk_color = "#f59e0b"
                confidence = max(severity_prob, 1 - severity_prob) * 100
            elif risk_score < 85:
                risk_level = "HIGH"
                risk_class = "risk-high"
                risk_color = "#ef4444"
                confidence = severity_prob * 100
            else:
                risk_level = "CRITICAL"
                risk_class = "risk-critical"
                risk_color = "#dc2626"
                confidence = severity_prob * 100
                
            confidence = int(confidence)
            
            # 8. Police Action Recommendations (Phase 5)
            recs = []
            if risk_level == "LOW":
                recs.append(("🔍 Deploy 2 Patrol Officers", "Verify clearing times and ensure adjacent signal junctions remain clear."))
                recs.append(("📡 CCTV Room Monitoring", "Instruct CCTV operator to keep camera feed in the active monitoring cycle."))
            elif risk_level == "MEDIUM":
                recs.append(("👮 Deploy 5 Traffic Wardens", "Deploy officers to guide manual traffic flow at the immediate junction."))
                recs.append(("⚠️ Advance Warning Signage", "Deploy digital messaging boards 500m upstream warning commuters to slow down."))
                recs.append(("🚦 Signal Timing Adjustments", "Increase green-phase window by 10% on the outflow route."))
            elif risk_level == "HIGH":
                recs.append(("👮 Deploy 15 Traffic Wardens", "Deploy heavy manual traffic coordination to flush gridlocked lines."))
                recs.append(("🔄 Open Diversion Routes", "Signal upstream intersections to divert traffic to parallel secondary roads."))
                recs.append(("🚦 Increase Signal Timing (+15s)", "Adjust signal controllers to hold green phase longer on the affected corridor."))
            elif risk_level == "CRITICAL":
                recs.append(("🚨 Emergency Traffic Control Team", "Dispatch rapid response command team to take over manual junction override."))
                recs.append(("⛔ Temporary Road / Lane Closure", "Close lanes around the coordinates immediately for clearance crews."))
                recs.append(("📢 Hold Upstream Junction Traffic", "Hold traffic signals at all intersections 1km upstream to prevent total locking."))
                
            # Cause recommendations
            if event_cause_choice == "water_logging":
                recs.append(("🌊 BBMP Pumping Team", "Dispatch emergency drainage pumps to clear waterlog bottleneck."))
            elif event_cause_choice == "vehicle_breakdown":
                recs.append(("🚚 Heavy Hyd Tow Truck", "Dispatch heavy tow truck crane from depot to clear blocked lane."))
            elif event_cause_choice == "accident":
                recs.append(("🚑 Emergency Ambulance & Patrol", "Dispatch medical units and accident clearance crews."))
            
            # Explainable AI list (Phase 7)
            exp_list = [
                ("Priority Factor", f"+{int(prio_pts)}" if priority_choice == "High" else f"+{int(prio_pts)}"),
                ("Requires Road Closure", f"+{int(closure_pts)}"),
                ("Est. Event Duration", f"+{int(dur_pts)}"),
                ("Event Type", f"+{int(type_pts)}"),
                ("Zone Density Factor", f"+{int(density_pts)}"),
                ("Historical Severity Ratio", f"+{int(hist_sev_pts)}")
            ]
            
            # Render Layout
            st.write("---")
            st.markdown("### 🚨 AI Decision Support Output")
            
            c_out1, c_out2, c_out3 = st.columns([1, 1.2, 1.8])
            
            with c_out1:
                # Circular progress for impact score (Phase 3)
                st.markdown(f"""
                    <div class="card-panel" style="text-align: center;">
                        <h5 style="margin-top:0;">⚡ Event Impact Score</h5>
                        <div style="display: flex; justify-content: center; margin: 15px 0;">
                            <svg width="150" height="150" viewBox="0 0 150 150">
                                <circle cx="75" cy="75" r="60" stroke="#1e293b" stroke-width="12" fill="transparent" />
                                <circle cx="75" cy="75" r="60" stroke="{impact_color}" stroke-width="12" fill="transparent"
                                        stroke-dasharray="377" stroke-dashoffset="{offset}" stroke-linecap="round"
                                        transform="rotate(-90 75 75)" style="transition: stroke-dashoffset 1s ease-out;" />
                                <text x="75" y="80" text-anchor="middle" font-size="24" font-weight="bold" fill="#ffffff" font-family="'Outfit', sans-serif">{impact_score}</text>
                                <text x="75" y="105" text-anchor="middle" font-size="12" fill="#94a3b8" font-family="'Outfit', sans-serif">/ 100</text>
                            </svg>
                        </div>
                        <div style="font-weight: bold; color: {impact_color}; text-transform: uppercase; letter-spacing: 1px; font-size:16px;">
                            {impact_cat} Impact
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Congestion Risk Badges (Phase 4)
                st.markdown(f"""
                    <div class="card-panel">
                        <h5 style="margin-top:0;">📈 Congestion Risk Profile</h5>
                        <div class="{risk_class}">{risk_level}</div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; margin-top: 15px; margin-bottom: 5px;">
                            <span>Model Confidence</span>
                            <span style="font-weight: bold; color: {risk_color};">{confidence}%</span>
                        </div>
                        <div style="width: 100%; bg-color: #1e293b; border-radius: 4px; height: 6px; overflow: hidden; background: #1e293b;">
                            <div style="width: {confidence}%; background: {risk_color}; height: 100%; border-radius: 4px;"></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
            with c_out2:
                # Explainable AI (Phase 7)
                st.markdown("<div class=\"card-panel\">", unsafe_allow_html=True)
                st.markdown("<h5 style='margin-top:0;'>🔍 Why this prediction?</h5>", unsafe_allow_html=True)
                st.markdown("**Prediction Reason Drivers:**")
                for factor, weight in exp_list:
                    st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(30, 41, 59, 0.4); border-radius: 6px; margin-bottom: 8px; border: 1px solid rgba(255, 255, 255, 0.02);">
                            <span style="font-size: 13px; color: #cbd5e1;">{factor}</span>
                            <span style="font-weight: bold; color: #38bdf8;">{weight}</span>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Geofencing Location details
                st.markdown(f"""
                    <div class="card-panel">
                        <h5 style="margin-top:0;">📍 Corridor Geofencing</h5>
                        <div style="font-size: 13px;">
                            <p><b>Geofenced Corridor:</b> {corridor_choice}</p>
                            <p><b>Police Station:</b> {police_station_choice}</p>
                            <p><b>Municipal Zone:</b> {zone_choice}</p>
                            <p><b>Coordinates:</b> {lat_input:.5f}, {lon_input:.5f}</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
            with c_out3:
                # Police Action Recommendations Cards (Phase 5)
                st.markdown("<div class=\"card-panel\" style='height: 100%;'>", unsafe_allow_html=True)
                st.markdown("<h5 style='margin-top:0;'>👮 AI Recommendation & Action Plan</h5>", unsafe_allow_html=True)
                for title, desc in recs:
                    st.markdown(f"""
                        <div class="rec-item" style="border-left-color: {risk_color};">
                            <div style="font-weight: 700; color: #ffffff; font-size:14px;">{title}</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">{desc}</div>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            # Geolocation map showing simulated incident and historical context
            st.markdown("---")
            st.markdown("### 🗺️ Incident Location & Surrounding Congestion Spots")
            m = folium.Map(location=[lat_input, lon_input], zoom_start=14, tiles="CartoDB dark_matter")
            # Highlight simulated incident
            folium.Marker(
                location=[lat_input, lon_input],
                popup=folium.Popup(f"<b>SIMULATED EVENT</b><br>Cause: {event_cause_choice}<br>Zone: {zone_choice}<br>Corridor: {corridor_choice}", max_width=300),
                icon=folium.Icon(color='red', icon='warning', prefix='fa')
            ).add_to(m)
            
            # Show historical events in same zone
            zone_events = df[df['zone'] == zone_choice].dropna(subset=['latitude', 'longitude']).head(40)
            for idx, row in zone_events.iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=5,
                    color='#818cf8',
                    fill=True,
                    fill_color='#818cf8',
                    popup=f"Historical incident: {row['event_cause']} ({row['priority']})"
                ).add_to(m)
                
            folium_static(m, width=1100, height=450)

# ---------------------------------------------------------
# Page 3: 🗺 Geospatial Map
# ---------------------------------------------------------
elif page == "🗺 Geospatial Map":
    st.markdown("### 🗺️ Geospatial Traffic Hotspots Map")
    st.write("Full-screen diagnostic map centered on Bengaluru's coordinates. Customize filters on the panel below:")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        cause_filter = st.multiselect("Filter by Event Cause", sorted(df['event_cause'].unique()))
    with c2:
        priority_filter = st.multiselect("Filter by Priority", sorted(df['priority'].unique()))
    with c3:
        corridor_filter = st.multiselect("Filter by Corridor", sorted(df['corridor'].unique()))
        
    filtered_df = df.copy()
    if cause_filter:
        filtered_df = filtered_df[filtered_df['event_cause'].isin(cause_filter)]
    if priority_filter:
        filtered_df = filtered_df[filtered_df['priority'].isin(priority_filter)]
    if corridor_filter:
        filtered_df = filtered_df[filtered_df['corridor'].isin(corridor_filter)]
        
    map_sample = filtered_df.dropna(subset=['latitude', 'longitude'])
    if len(map_sample) > 1500:
        map_sample = map_sample.sample(1500, random_state=42)
        st.info(f"Displaying a representative sample of 1,500 active/historical points out of {len(filtered_df):,} total filtered rows.")
    else:
        st.info(f"Displaying all {len(map_sample):,} filtered incidents.")
        
    if len(map_sample) > 0:
        avg_lat = map_sample['latitude'].mean()
        avg_lon = map_sample['longitude'].mean()
        
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=11, tiles="CartoDB dark_matter")
        
        # Heatmap Layer
        heat_data = [[row['latitude'], row['longitude']] for idx, row in map_sample.iterrows()]
        HeatMap(heat_data, radius=10, blur=15, name="Heatmap").add_to(m)
        
        # Marker Cluster Layer
        marker_cluster = MarkerCluster(name="Cluster Markers").add_to(m)
        for idx, row in map_sample.head(300).iterrows(): # Show top 300 markers
            color = 'red' if str(row['priority']).lower() == 'high' else 'blue'
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(f"<b>Cause:</b> {row['event_cause']}<br><b>Corridor:</b> {row['corridor']}<br><b>Junction:</b> {row['junction']}", max_width=300),
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(marker_cluster)
            
        folium.LayerControl().add_to(m)
        folium_static(m, width=1100, height=600)
    else:
        st.warning("No records match the selected filters.")

# ---------------------------------------------------------
# Page 4: 📊 Analytics
# ---------------------------------------------------------
elif page == "📊 Analytics":
    st.markdown("### 📊 Enterprise Analytics & Diagnostics Panel")
    
    tab1, tab2 = st.tabs(["📊 Spatial & Municipal Analytics", "🧠 Model Diagnostics"])
    
    with tab1:
        st.markdown("#### Congested Zones & Top Junctions")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("##### 🏢 Most Congested Zones")
            zone_counts = df['zone'].value_counts().reset_index()
            zone_counts.columns = ['Municipal Zone', 'Total Incidents']
            fig_zone = px.bar(zone_counts, x='Municipal Zone', y='Total Incidents', color='Total Incidents', color_continuous_scale='Blues', template='plotly_dark')
            fig_zone.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
            st.plotly_chart(fig_zone, use_container_width=True)
            
            st.markdown("##### 🚧 Road Closure Stats")
            closure_counts = df['requires_road_closure'].value_counts().reset_index()
            closure_counts.columns = ['Requires Road Closure', 'Count']
            closure_counts['Requires Road Closure'] = closure_counts['Requires Road Closure'].map({True: 'Closure Required', False: 'Open Lanes'})
            fig_closure = px.pie(closure_counts, values='Count', names='Requires Road Closure', color_discrete_sequence=['#10b981', '#ef4444'], template='plotly_dark')
            fig_closure.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
            st.plotly_chart(fig_closure, use_container_width=True)
            
        with col_chart2:
            st.markdown("##### 📍 Top Affected Junctions")
            junc_counts = df['junction'].value_counts().head(15).reset_index()
            junc_counts.columns = ['Junction Name', 'Total Incidents']
            fig_junc = px.bar(junc_counts, x='Total Incidents', y='Junction Name', orientation='h', color='Total Incidents', color_continuous_scale='Oranges', template='plotly_dark')
            fig_junc.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
            st.plotly_chart(fig_junc, use_container_width=True)
            
            st.markdown("##### 🕒 Hourly Incident Peaks")
            df_hour = df.groupby('hour').size().reset_index(name='Total Incidents')
            fig_hour = px.line(df_hour, x='hour', y='Total Incidents', color_discrete_sequence=['#38bdf8'], markers=True, template='plotly_dark')
            fig_hour.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
            st.plotly_chart(fig_hour, use_container_width=True)
            
    with tab2:
        st.markdown("#### Model Performance Diagnostics")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("##### Accuracy & ROC-AUC Comparison")
            if os.path.exists("plots/model_comparison.png"):
                st.image("plots/model_comparison.png", use_container_width=True)
            else:
                st.warning("Model comparison plot not found.")
                
            st.markdown("##### Test Set Confusion Matrix")
            if os.path.exists("plots/confusion_matrix.png"):
                st.image("plots/confusion_matrix.png", use_container_width=True)
            else:
                st.warning("Confusion matrix plot not found.")
                
        with col_p2:
            st.markdown("##### Classifier Feature Importance")
            if os.path.exists("plots/feature_importance.png"):
                st.image("plots/feature_importance.png", use_container_width=True)
            else:
                st.warning("Feature importance plot not found.")
                
            st.markdown("##### ROC Curves (Held-out Test)")
            if os.path.exists("plots/roc_curves.png"):
                st.image("plots/roc_curves.png", use_container_width=True)
            else:
                st.warning("ROC curves plot not found.")

# ---------------------------------------------------------
# Page 5: ⚙ AI Recommendations
# ---------------------------------------------------------
elif page == "⚙ AI Recommendations":
    st.markdown("### ⚙️ Bengaluru Traffic Control SOP Engine")
    st.write("This section details the automated SOP guidelines generated for BTP (Bengaluru Traffic Police) based on predicted congestion states.")
    
    col_rec1, col_rec2 = st.columns(2)
    
    with col_rec1:
        st.markdown("<div class='card-panel'>", unsafe_allow_html=True)
        st.markdown("#### 🚨 SOP Level 4: CRITICAL CONGESTION RISK")
        st.markdown("""
        * **Personnel Deployment**: Minimum 25 officers (including 2 inspectors) dispatched within 10 minutes.
        * **Lane Control**: Complete closure of affected lane. Active diversion boards 1.5km ahead.
        * **Signal Priority**: Hold signal cycle to RED at all incoming feeder branches. Increase green phase on outward exit lanes to 90 seconds.
        * **Public Notice**: Trigger automated broadcast to Google Maps/Waze, local FM, and traffic police mobile alerts.
        """)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card-panel'>", unsafe_allow_html=True)
        st.markdown("#### 🔴 SOP Level 3: HIGH CONGESTION RISK")
        st.markdown("""
        * **Personnel Deployment**: Minimum 15 wardens deployed to key junction and nearest exit points.
        * **Lane Control**: Set up warning cones 500m upstream. Keep shoulder open for breakdown/debris clearance.
        * **Signal Priority**: Adjust signal timing at the immediate junction (+15s green duration on affected corridor).
        * **Coordination**: Alert adjacent traffic stations (upstream and downstream) to hold traffic.
        """)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_rec2:
        st.markdown("<div class='card-panel'>", unsafe_allow_html=True)
        st.markdown("#### 🟡 SOP Level 2: MEDIUM CONGESTION RISK")
        st.markdown("""
        * **Personnel Deployment**: Deploy 5 wardens to coordinate bottlenecks at the intersection.
        * **Lane Control**: Keep lane open but set up slow-down alerts on digital signages.
        * **Signal Priority**: Increase green phase slightly (+10% duration) during rush hours.
        """)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card-panel'>", unsafe_allow_html=True)
        st.markdown("#### 🟢 SOP Level 1: LOW CONGESTION RISK")
        st.markdown("""
        * **Personnel Deployment**: Deploy 2 patrol officers for clearing verification.
        * **Lane Control**: Keep standard operational lanes open.
        * **Signal Priority**: Standard automated adaptive signal plans.
        """)
        st.markdown("</div>", unsafe_allow_html=True)

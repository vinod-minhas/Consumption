#!/usr/bin/env python
# coding: utf-8

# In[4]:


"""
Pan-India Site Consumption Dashboard - Complete Version with STP Charts
========================================================================
Author: VINOD
Date: 17/04/2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==================== PAGE CONFIGURATION ====================

st.set_page_config(
    page_title="Pan-India Consumption Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #333;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.3rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== DATABASE / CSV CONNECTION ====================

@st.cache_resource
def get_database_connection():
    """Create database connection - supports both SQLite and CSV"""
    import os
    # Hardcoded path for local use
    db_path = r'C:\Users\vmminhas\Desktop\Python\Machine Learning\master_consumption.db'
    if os.path.exists(db_path):
        return sqlite3.connect(db_path, check_same_thread=False), 'sqlite'
    return None, 'csv'


@st.cache_data(ttl=300)
def load_consumption_data():
    """Load consumption data - from SQLite or CSV"""
    conn, mode = get_database_connection()

    if mode == 'sqlite' and conn:
        query = """
            SELECT c.*, s.site_name, s.region, s.business_unit, s.capacity_gsf
            FROM consumption_data c
            LEFT JOIN site_master s ON c.site_code = s.site_code
            ORDER BY c.date DESC, c.site_code
        """
        df = pd.read_sql(query, conn)
    else:
        # Fallback to CSV
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consumption_data.csv')
        site_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site_master.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if os.path.exists(site_path):
                sites = pd.read_csv(site_path)
                df = df.merge(sites, on='site_code', how='left')
        else:
            return pd.DataFrame()

    df['date'] = pd.to_datetime(df['date'])
    return df

@st.cache_data(ttl=300)
def load_site_master():
    """Load site master data"""
    conn, mode = get_database_connection()
    if mode == 'sqlite' and conn:
        return pd.read_sql("SELECT * FROM site_master", conn)
    else:
        site_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site_master.csv')
        if os.path.exists(site_path):
            return pd.read_csv(site_path)
    return pd.DataFrame()

@st.cache_data(ttl=300)
def load_processing_logs():
    """Load processing logs"""
    conn, mode = get_database_connection()
    if mode == 'sqlite' and conn:
        return pd.read_sql("SELECT * FROM processing_logs ORDER BY processing_timestamp DESC LIMIT 50", conn)
    else:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processing_logs.csv')
        if os.path.exists(log_path):
            return pd.read_csv(log_path)
    return pd.DataFrame()

# ==================== HELPER FUNCTIONS ====================

def calculate_kpis(df):
    total_eb = df['eb_consumption'].sum()
    total_dg = df['dg_consumption'].sum()
    total_solar = (df['solar1_consumption'] + df['solar2_consumption']).sum()
    total_power = total_eb + total_dg + total_solar
    solar_pct = (total_solar / total_power * 100) if total_power > 0 else 0

    # STP KPIs
    total_stp_inlet = df['stp_inlet'].sum() if 'stp_inlet' in df.columns else 0
    total_stp_outlet = df['stp_outlet'].sum() if 'stp_outlet' in df.columns else 0
    stp_efficiency = (total_stp_outlet / total_stp_inlet * 100) if total_stp_inlet > 0 else 0

    return {
        'total_eb': total_eb,
        'total_dg': total_dg,
        'total_solar': total_solar,
        'total_power': total_power,
        'solar_percentage': solar_pct,
        'avg_eui': df['eui_daily'].mean(),
        'avg_quality': df['data_quality_score'].mean(),
        'total_water': df['water_consumption'].sum(),
        'active_sites': df['site_code'].nunique(),
        'total_stp_inlet': total_stp_inlet,
        'total_stp_outlet': total_stp_outlet,
        'stp_efficiency': stp_efficiency,
        'total_borewell': df['borewell'].sum() if 'borewell' in df.columns else 0,
        'total_food_waste': df['canteen_food_waste'].sum() if 'canteen_food_waste' in df.columns else 0,
    }

def safe_get_site_details(site_info, selected_site):
    """Safely get site details with fallback"""
    site_match = site_info[site_info['site_code'] == selected_site]
    if not site_match.empty:
        return site_match.iloc[0]
    return pd.Series({
        'site_name': selected_site,
        'region': 'N/A',
        'business_unit': 'N/A',
        'capacity_gsf': 0
    })

# ==================== SIDEBAR ====================

with st.sidebar:
    st.title("⚡ Navigation")

    page = st.radio(
        "Select Page",
        ["📊 Executive Overview", "🏢 Site Analysis", "💧 STP Analysis",
         "📈 Comparative Analysis", "🔍 Data Explorer", "📑 Reports", "⚙️ System Status"]
    )

    st.markdown("---")

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    df_all = load_consumption_data()

    if not df_all.empty:
        st.subheader("📅 Date Filter")
        min_date = df_all['date'].min().date()
        max_date = df_all['date'].max().date()

        date_range = st.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if len(date_range) == 2:
            start_date, end_date = date_range
            df_filtered = df_all[
                (df_all['date'].dt.date >= start_date) &
                (df_all['date'].dt.date <= end_date)
            ]
        else:
            df_filtered = df_all

        st.markdown("---")
        st.subheader("🏢 Site Filter")
        all_sites = ['All Sites'] + sorted(df_filtered['site_code'].unique().tolist())
        selected_sites = st.multiselect("Select Sites", options=all_sites, default=['All Sites'])

        if 'All Sites' not in selected_sites and selected_sites:
            df_filtered = df_filtered[df_filtered['site_code'].isin(selected_sites)]
    else:
        df_filtered = df_all
        st.warning("No data available")

    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# ==================== PAGE 1: EXECUTIVE OVERVIEW ====================

if page == "📊 Executive Overview":
    st.markdown('<p class="main-header">⚡ Pan-India Consumption Dashboard</p>', unsafe_allow_html=True)

    if df_filtered.empty:
        st.warning("No data available for the selected filters")
    else:
        kpis = calculate_kpis(df_filtered)

        # Row 1: Power KPIs
        st.subheader("⚡ Power Metrics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Power", f"{kpis['total_power']:,.0f} kWh")
        with col2:
            delta_eui = round(kpis['avg_eui'] - 1.0, 3)
            st.metric("Average EUI", f"{kpis['avg_eui']:.3f}", delta=f"{delta_eui}", delta_color="inverse")
        with col3:
            st.metric("Solar Contribution", f"{kpis['solar_percentage']:.1f}%")
        with col4:
            st.metric("Active Sites", f"{kpis['active_sites']}")

        # Row 2: Water & STP KPIs
        st.subheader("💧 Water & STP Metrics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Water", f"{kpis['total_water']:,.0f} Kl")
        with col2:
            st.metric("STP Inlet", f"{kpis['total_stp_inlet']:,.0f} Kl")
        with col3:
            st.metric("STP Outlet", f"{kpis['total_stp_outlet']:,.0f} Kl")
        with col4:
            st.metric("STP Efficiency", f"{kpis['stp_efficiency']:.1f}%")

        st.markdown("---")

        # Charts Row 1
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 Daily Power Consumption Trend")
            df_daily = df_filtered.groupby('date')['total_power_consumption'].sum().reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_daily['date'], y=df_daily['total_power_consumption'],
                mode='lines+markers', name='Total Power',
                line=dict(color='#1f77b4', width=2), marker=dict(size=5)
            ))
            fig.update_layout(xaxis_title="Date", yaxis_title="kWh", hovermode='x unified', height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("🔋 Power Source Distribution")
            fig = go.Figure(data=[go.Pie(
                labels=['EB', 'DG', 'Solar'],
                values=[kpis['total_eb'], kpis['total_dg'], kpis['total_solar']],
                hole=0.4,
                marker_colors=['#1f77b4', '#ff7f0e', '#2ca02c']
            )])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        # Charts Row 2
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏢 Site-wise Consumption")
            site_summary = df_filtered.groupby('site_code').agg({
                'eb_consumption': 'sum',
                'dg_consumption': 'sum',
                'solar1_consumption': 'sum',
                'solar2_consumption': 'sum'
            }).reset_index()
            site_summary['total_solar'] = site_summary['solar1_consumption'] + site_summary['solar2_consumption']

            fig = go.Figure()
            fig.add_trace(go.Bar(name='EB', x=site_summary['site_code'], y=site_summary['eb_consumption'], marker_color='#1f77b4'))
            fig.add_trace(go.Bar(name='DG', x=site_summary['site_code'], y=site_summary['dg_consumption'], marker_color='#ff7f0e'))
            fig.add_trace(go.Bar(name='Solar', x=site_summary['site_code'], y=site_summary['total_solar'], marker_color='#2ca02c'))
            fig.update_layout(barmode='stack', xaxis_title="Site", yaxis_title="kWh", height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("💧 STP Inlet vs Outlet by Site")
            if 'stp_inlet' in df_filtered.columns and 'stp_outlet' in df_filtered.columns:
                stp_site = df_filtered.groupby('site_code').agg({
                    'stp_inlet': 'sum',
                    'stp_outlet': 'sum'
                }).reset_index()

                fig = go.Figure()
                fig.add_trace(go.Bar(name='STP Inlet', x=stp_site['site_code'], y=stp_site['stp_inlet'], marker_color='#17becf'))
                fig.add_trace(go.Bar(name='STP Outlet', x=stp_site['site_code'], y=stp_site['stp_outlet'], marker_color='#9edae5'))
                fig.update_layout(barmode='group', xaxis_title="Site", yaxis_title="Kl", height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("STP data not available in database")

# ==================== PAGE 2: SITE ANALYSIS ====================

elif page == "🏢 Site Analysis":
    st.title("🏢 Site-Level Analysis")

    if df_filtered.empty:
        st.warning("No data available for the selected filters")
    else:
        site_list = sorted(df_filtered['site_code'].unique())
        selected_site = st.selectbox("Select Site", site_list)

        site_df = df_filtered[df_filtered['site_code'] == selected_site].copy().sort_values('date')
        site_info = load_site_master()
        site_details = safe_get_site_details(site_info, selected_site)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Site Name", str(site_details.get('site_name', 'N/A')))
        with col2:
            st.metric("Region", str(site_details.get('region', 'N/A')))
        with col3:
            st.metric("Business Unit", str(site_details.get('business_unit', 'N/A')))
        with col4:
            gsf = site_details.get('capacity_gsf', 0)
            st.metric("Capacity (GSF)", f"{float(gsf):,.0f}" if gsf else "N/A")

        st.markdown("---")

        # Power breakdown
        st.subheader("📊 Power Consumption Breakdown")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=site_df['date'], y=site_df['eb_consumption'], name='EB', stackgroup='one', fillcolor='#1f77b4'))
        fig.add_trace(go.Scatter(x=site_df['date'], y=site_df['dg_consumption'], name='DG', stackgroup='one', fillcolor='#ff7f0e'))
        fig.add_trace(go.Scatter(x=site_df['date'], y=site_df['solar1_consumption'], name='Solar-1', stackgroup='one', fillcolor='#2ca02c'))
        fig.add_trace(go.Scatter(x=site_df['date'], y=site_df['solar2_consumption'], name='Solar-2', stackgroup='one', fillcolor='#98df8a'))
        fig.update_layout(xaxis_title="Date", yaxis_title="kWh", hovermode='x unified', height=380)
        st.plotly_chart(fig, use_container_width=True)

        # EUI and Water
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 EUI Trend")
            fig_eui = go.Figure()
            fig_eui.add_trace(go.Scatter(x=site_df['date'], y=site_df['eui_daily'], mode='lines+markers', name='EUI', line=dict(color='blue', width=2)))
            fig_eui.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Target = 1.0")
            fig_eui.update_layout(xaxis_title="Date", yaxis_title="EUI", height=300)
            st.plotly_chart(fig_eui, use_container_width=True)

        with col2:
            st.subheader("💧 Total Water Consumption")
            fig_water = go.Figure()
            fig_water.add_trace(go.Bar(x=site_df['date'], y=site_df['water_consumption'], name='Water', marker_color='lightblue'))
            fig_water.update_layout(xaxis_title="Date", yaxis_title="Kl", height=300)
            st.plotly_chart(fig_water, use_container_width=True)

        # STP Charts
        st.markdown("---")
        st.subheader("🔬 STP (Sewage Treatment Plant) Analysis")

        if 'stp_inlet' in site_df.columns and 'stp_outlet' in site_df.columns:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**STP Inlet vs Outlet Daily Trend**")
                fig_stp = go.Figure()
                fig_stp.add_trace(go.Scatter(
                    x=site_df['date'], y=site_df['stp_inlet'],
                    mode='lines+markers', name='STP Inlet',
                    line=dict(color='#17becf', width=2)
                ))
                fig_stp.add_trace(go.Scatter(
                    x=site_df['date'], y=site_df['stp_outlet'],
                    mode='lines+markers', name='STP Outlet',
                    line=dict(color='#9edae5', width=2, dash='dash')
                ))
                fig_stp.update_layout(
                    xaxis_title="Date", yaxis_title="Volume (Kl)",
                    hovermode='x unified', height=320
                )
                st.plotly_chart(fig_stp, use_container_width=True)

            with col2:
                st.markdown("**STP Treatment Efficiency (%)**")
                site_df['stp_efficiency'] = (
                    site_df['stp_outlet'] / site_df['stp_inlet'] * 100
                ).where(site_df['stp_inlet'] > 0, 0)

                fig_eff = go.Figure()
                fig_eff.add_trace(go.Bar(
                    x=site_df['date'],
                    y=site_df['stp_efficiency'],
                    name='STP Efficiency',
                    marker_color=['green' if x >= 80 else 'orange' if x >= 60 else 'red'
                                  for x in site_df['stp_efficiency']]
                ))
                fig_eff.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Target 80%")
                fig_eff.update_layout(
                    xaxis_title="Date", yaxis_title="Efficiency (%)",
                    height=320
                )
                st.plotly_chart(fig_eff, use_container_width=True)

            # STP Summary KPIs
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total STP Inlet", f"{site_df['stp_inlet'].sum():,.0f} Kl")
            with col2:
                st.metric("Total STP Outlet", f"{site_df['stp_outlet'].sum():,.0f} Kl")
            with col3:
                avg_eff = site_df['stp_efficiency'].mean()
                st.metric("Avg STP Efficiency", f"{avg_eff:.1f}%")
            with col4:
                water_recycled = site_df['stp_outlet'].sum()
                st.metric("Water Recycled", f"{water_recycled:,.0f} Kl")
        else:
            st.info("STP data columns (stp_inlet, stp_outlet) not found in database. Please check ETL script.")

        # Borewell and Food Waste
        if 'borewell' in site_df.columns or 'canteen_food_waste' in site_df.columns:
            st.markdown("---")
            st.subheader("🌊 Borewell & Canteen Waste")
            col1, col2 = st.columns(2)

            with col1:
                if 'borewell' in site_df.columns:
                    st.markdown("**Borewell Consumption (Kl)**")
                    fig_bw = go.Figure()
                    fig_bw.add_trace(go.Bar(x=site_df['date'], y=site_df['borewell'], marker_color='#aec7e8'))
                    fig_bw.update_layout(xaxis_title="Date", yaxis_title="Kl", height=280)
                    st.plotly_chart(fig_bw, use_container_width=True)

            with col2:
                if 'canteen_food_waste' in site_df.columns:
                    st.markdown("**Canteen Food Waste (kg)**")
                    fig_fw = go.Figure()
                    fig_fw.add_trace(go.Bar(x=site_df['date'], y=site_df['canteen_food_waste'], marker_color='#ffbb78'))
                    fig_fw.update_layout(xaxis_title="Date", yaxis_title="kg", height=280)
                    st.plotly_chart(fig_fw, use_container_width=True)

        # Daily data table
        st.markdown("---")
        st.subheader("📋 Daily Data Table")

        cols_to_show = ['date', 'eb_consumption', 'dg_consumption', 'solar1_consumption',
                        'solar2_consumption', 'total_power_consumption', 'water_consumption',
                        'stp_inlet', 'stp_outlet', 'borewell', 'eui_daily', 'data_quality_score']
        cols_available = [c for c in cols_to_show if c in site_df.columns]

        display_df = site_df[cols_available].copy()
        display_df['date'] = display_df['date'].dt.strftime('%d/%m/%Y')
        st.dataframe(display_df, use_container_width=True, height=400)

# ==================== PAGE 3: STP ANALYSIS ====================

elif page == "💧 STP Analysis":
    st.title("💧 STP (Sewage Treatment Plant) Analysis")
    st.markdown("*Dedicated STP monitoring across all pan-India sites*")

    if df_filtered.empty:
        st.warning("No data available for the selected filters")
    elif 'stp_inlet' not in df_filtered.columns or 'stp_outlet' not in df_filtered.columns:
        st.error("STP data columns not found. Please verify ETL script loaded stp_inlet and stp_outlet columns.")
    else:
        # STP KPIs
        total_inlet = df_filtered['stp_inlet'].sum()
        total_outlet = df_filtered['stp_outlet'].sum()
        overall_efficiency = (total_outlet / total_inlet * 100) if total_inlet > 0 else 0
        water_saved = total_outlet  # Recycled water

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total STP Inlet", f"{total_inlet:,.0f} Kl")
        with col2:
            st.metric("Total STP Outlet", f"{total_outlet:,.0f} Kl")
        with col3:
            st.metric("Overall STP Efficiency", f"{overall_efficiency:.1f}%")
        with col4:
            st.metric("Water Recycled", f"{water_saved:,.0f} Kl")

        st.markdown("---")

        # Network-level STP trend
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 Network STP Daily Trend")
            stp_daily = df_filtered.groupby('date').agg({
                'stp_inlet': 'sum',
                'stp_outlet': 'sum'
            }).reset_index()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=stp_daily['date'], y=stp_daily['stp_inlet'],
                mode='lines+markers', name='STP Inlet',
                line=dict(color='#17becf', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=stp_daily['date'], y=stp_daily['stp_outlet'],
                mode='lines+markers', name='STP Outlet',
                line=dict(color='#1f77b4', width=2, dash='dash')
            ))
            fig.update_layout(
                xaxis_title="Date", yaxis_title="Volume (Kl)",
                hovermode='x unified', height=380
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("🏢 STP Performance by Site")
            stp_site = df_filtered.groupby('site_code').agg({
                'stp_inlet': 'sum',
                'stp_outlet': 'sum'
            }).reset_index()
            stp_site['efficiency'] = (stp_site['stp_outlet'] / stp_site['stp_inlet'] * 100).where(stp_site['stp_inlet'] > 0, 0)

            fig = go.Figure()
            fig.add_trace(go.Bar(name='STP Inlet', x=stp_site['site_code'], y=stp_site['stp_inlet'], marker_color='#17becf'))
            fig.add_trace(go.Bar(name='STP Outlet', x=stp_site['site_code'], y=stp_site['stp_outlet'], marker_color='#1f77b4'))
            fig.update_layout(barmode='group', xaxis_title="Site", yaxis_title="Kl", height=380)
            st.plotly_chart(fig, use_container_width=True)

        # STP Efficiency trend
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("⚡ Daily STP Efficiency Trend")
            stp_daily['efficiency'] = (stp_daily['stp_outlet'] / stp_daily['stp_inlet'] * 100).where(stp_daily['stp_inlet'] > 0, 0)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=stp_daily['date'], y=stp_daily['efficiency'],
                mode='lines+markers', name='STP Efficiency',
                line=dict(color='green', width=2),
                fill='tozeroy', fillcolor='rgba(0,128,0,0.1)'
            ))
            fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Target 80%")
            fig.update_layout(
                xaxis_title="Date", yaxis_title="Efficiency (%)",
                yaxis=dict(range=[0, 110]), height=350
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("🏆 Site STP Efficiency Ranking")
            stp_site_sorted = stp_site.sort_values('efficiency', ascending=False)

            colors = ['green' if x >= 80 else 'orange' if x >= 60 else 'red' for x in stp_site_sorted['efficiency']]

            fig = go.Figure(go.Bar(
                x=stp_site_sorted['site_code'],
                y=stp_site_sorted['efficiency'],
                marker_color=colors,
                text=stp_site_sorted['efficiency'].round(1).astype(str) + '%',
                textposition='outside'
            ))
            fig.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Target 80%")
            fig.update_layout(
                xaxis_title="Site", yaxis_title="Efficiency (%)",
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

        # STP Data Table
        st.markdown("---")
        st.subheader("📋 STP Daily Data")
        stp_cols = ['date', 'site_code', 'stp_inlet', 'stp_outlet']
        stp_cols_available = [c for c in stp_cols if c in df_filtered.columns]
        stp_display = df_filtered[stp_cols_available].copy()
        stp_display['date'] = stp_display['date'].dt.strftime('%d/%m/%Y')
        if 'stp_inlet' in stp_display.columns and 'stp_outlet' in stp_display.columns:
            stp_display['efficiency_%'] = (
                stp_display['stp_outlet'] / stp_display['stp_inlet'] * 100
            ).where(stp_display['stp_inlet'] > 0, 0).round(1)
        st.dataframe(stp_display, use_container_width=True, height=400)

# ==================== PAGE 4: COMPARATIVE ANALYSIS ====================

elif page == "📈 Comparative Analysis":
    st.title("📈 Comparative Analysis")

    if df_filtered.empty:
        st.warning("No data available for the selected filters")
    else:
        site_summary = df_filtered.groupby('site_code').agg({
            'eb_consumption': 'sum',
            'dg_consumption': 'sum',
            'solar1_consumption': 'sum',
            'solar2_consumption': 'sum',
            'water_consumption': 'sum',
            'eui_daily': 'mean',
            'data_quality_score': 'mean'
        }).reset_index()

        site_summary['total_power'] = (
            site_summary['eb_consumption'] + site_summary['dg_consumption'] +
            site_summary['solar1_consumption'] + site_summary['solar2_consumption']
        )
        site_summary['solar_percentage'] = (
            (site_summary['solar1_consumption'] + site_summary['solar2_consumption']) /
            site_summary['total_power'] * 100
        )

        if 'stp_inlet' in df_filtered.columns:
            stp_agg = df_filtered.groupby('site_code').agg({
                'stp_inlet': 'sum', 'stp_outlet': 'sum'
            }).reset_index()
            stp_agg['stp_efficiency'] = (stp_agg['stp_outlet'] / stp_agg['stp_inlet'] * 100).where(stp_agg['stp_inlet'] > 0, 0)
            site_summary = site_summary.merge(stp_agg, on='site_code', how='left')

        tab1, tab2, tab3, tab4 = st.tabs(["⚡ Power", "⚡ EUI", "☀️ Solar %", "💧 STP"])

        with tab1:
            top_power = site_summary.nlargest(10, 'total_power')[['site_code', 'total_power', 'eb_consumption', 'dg_consumption']].copy()
            top_power.columns = ['Site', 'Total Power (kWh)', 'EB (kWh)', 'DG (kWh)']
            st.dataframe(top_power, use_container_width=True)

        with tab2:
            top_eui = site_summary.nsmallest(10, 'eui_daily')[['site_code', 'eui_daily', 'total_power']].copy()
            top_eui.columns = ['Site', 'Average EUI', 'Total Power (kWh)']
            st.dataframe(top_eui, use_container_width=True)

        with tab3:
            top_solar = site_summary.nlargest(10, 'solar_percentage')[['site_code', 'solar_percentage', 'solar1_consumption', 'solar2_consumption']].copy()
            top_solar.columns = ['Site', 'Solar %', 'Solar-1 (kWh)', 'Solar-2 (kWh)']
            st.dataframe(top_solar, use_container_width=True)

        with tab4:
            if 'stp_efficiency' in site_summary.columns:
                top_stp = site_summary.nlargest(10, 'stp_efficiency')[['site_code', 'stp_efficiency', 'stp_inlet', 'stp_outlet']].copy()
                top_stp.columns = ['Site', 'STP Efficiency %', 'STP Inlet (Kl)', 'STP Outlet (Kl)']
                st.dataframe(top_stp, use_container_width=True)
            else:
                st.info("STP data not available")

        st.markdown("---")
        st.subheader("📊 Complete Site Comparison")
        comparison_df = site_summary[['site_code', 'total_power', 'eui_daily', 'solar_percentage', 'water_consumption', 'data_quality_score']].copy()
        comparison_df.columns = ['Site', 'Total Power (kWh)', 'Avg EUI', 'Solar %', 'Water (Kl)', 'Quality Score']
        st.dataframe(comparison_df, use_container_width=True)

# ==================== PAGE 5: DATA EXPLORER ====================

elif page == "🔍 Data Explorer":
    st.title("🔍 Data Explorer")

    if df_filtered.empty:
        st.warning("No data available for the selected filters")
    else:
        all_columns = df_filtered.columns.tolist()
        default_columns = [
            'site_code', 'date', 'eb_consumption', 'dg_consumption',
            'solar1_consumption', 'solar2_consumption', 'total_power_consumption',
            'water_consumption', 'stp_inlet', 'stp_outlet', 'borewell',
            'eui_daily', 'data_quality_score'
        ]
        selected_columns = st.multiselect(
            "Select Columns to Display",
            options=all_columns,
            default=[col for col in default_columns if col in all_columns]
        )

        if selected_columns:
            display_df = df_filtered[selected_columns].copy()
            if 'date' in display_df.columns:
                display_df['date'] = display_df['date'].dt.strftime('%d/%m/%Y')
            st.dataframe(display_df, use_container_width=True, height=500)

            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"consumption_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        st.markdown("---")
        st.subheader("📊 Statistical Summary")
        numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns
        st.dataframe(df_filtered[numeric_cols].describe().T, use_container_width=True)

# ==================== PAGE 6: REPORTS ====================

elif page == "📑 Reports":
    st.title("📑 Reports & Export")

    if df_filtered.empty:
        st.warning("No data available for the selected filters")
    else:
        report_type = st.selectbox("Select Report Type", ["Summary Report", "Site-wise Detailed Report", "STP Report"])

        if st.button("Generate Report", type="primary"):
            kpis = calculate_kpis(df_filtered)

            if report_type == "Summary Report":
                st.markdown("### Summary Report")
                st.markdown(f"**Date Range:** {df_filtered['date'].min().strftime('%d/%m/%Y')} to {df_filtered['date'].max().strftime('%d/%m/%Y')}")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Power Consumption**")
                    st.write(f"- Total: {kpis['total_power']:,.0f} kWh")
                    st.write(f"- EB: {kpis['total_eb']:,.0f} kWh")
                    st.write(f"- DG: {kpis['total_dg']:,.0f} kWh")
                    st.write(f"- Solar: {kpis['total_solar']:,.0f} kWh ({kpis['solar_percentage']:.1f}%)")
                with col2:
                    st.markdown("**Water & STP**")
                    st.write(f"- Total Water: {kpis['total_water']:,.0f} Kl")
                    st.write(f"- STP Inlet: {kpis['total_stp_inlet']:,.0f} Kl")
                    st.write(f"- STP Outlet: {kpis['total_stp_outlet']:,.0f} Kl")
                    st.write(f"- STP Efficiency: {kpis['stp_efficiency']:.1f}%")

            elif report_type == "Site-wise Detailed Report":
                st.markdown("### Site-wise Detailed Report")
                site_summary = df_filtered.groupby('site_code').agg({
                    'eb_consumption': 'sum', 'dg_consumption': 'sum',
                    'solar1_consumption': 'sum', 'solar2_consumption': 'sum',
                    'water_consumption': 'sum', 'eui_daily': 'mean',
                    'data_quality_score': 'mean'
                }).reset_index()
                st.dataframe(site_summary, use_container_width=True)

            elif report_type == "STP Report":
                st.markdown("### STP Performance Report")
                if 'stp_inlet' in df_filtered.columns:
                    stp_summary = df_filtered.groupby('site_code').agg({
                        'stp_inlet': 'sum', 'stp_outlet': 'sum'
                    }).reset_index()
                    stp_summary['efficiency_%'] = (stp_summary['stp_outlet'] / stp_summary['stp_inlet'] * 100).round(1)
                    stp_summary['water_recycled_Kl'] = stp_summary['stp_outlet']
                    st.dataframe(stp_summary, use_container_width=True)
                else:
                    st.info("STP data not available")

        st.markdown("---")
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download Complete Data as CSV",
            data=csv,
            file_name=f"consumption_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ==================== PAGE 7: SYSTEM STATUS ====================

elif page == "⚙️ System Status":
    st.title("⚙️ System Status")

    logs_df = load_processing_logs()

    if not logs_df.empty:
        st.subheader("📋 Recent Processing Logs")
        display_logs = logs_df.copy()
        if 'processing_timestamp' in display_logs.columns:
            display_logs = display_logs.sort_values('processing_timestamp', ascending=False)
        st.dataframe(display_logs, use_container_width=True, height=400)
    else:
        st.info("No processing logs available")

    st.markdown("---")
    st.subheader("📊 Database Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records", len(df_all))
    with col2:
        st.metric("Total Sites", df_all['site_code'].nunique() if not df_all.empty else 0)
    with col3:
        st.metric("Date Range", f"{df_all['date'].nunique()} days" if not df_all.empty else "N/A")



# In[ ]:





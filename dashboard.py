#!/usr/bin/env python
# coding: utf-8

# In[1]:


"""
Pan-India Site Consumption Dashboard
=====================================
Interactive Streamlit dashboard for visualizing and analyzing consumption data
across multiple sites

Author: VINOD
Date: 14/04/2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

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
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== DATABASE CONNECTION ====================

@st.cache_resource
def get_database_connection():
    """Create database connection"""
    import os
    # Use relative path for cloud deployment
    db_path = os.path.join(os.path.dirname(__file__), 'master_consumption.db')
    return sqlite3.connect(db_path, check_same_thread=False)



@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_consumption_data():
    """Load consumption data from database"""
    conn = get_database_connection()
    query = """
        SELECT 
            c.*,
            s.site_name,
            s.region,
            s.business_unit,
            s.capacity_gsf
        FROM consumption_data c
        LEFT JOIN site_master s ON c.site_code = s.site_code
        ORDER BY c.date DESC, c.site_code
    """
    df = pd.read_sql(query, conn)
    df['date'] = pd.to_datetime(df['date'])
    return df

@st.cache_data(ttl=300)
def load_site_master():
    """Load site master data"""
    conn = get_database_connection()
    df = pd.read_sql("SELECT * FROM site_master", conn)
    return df

@st.cache_data(ttl=300)
def load_processing_logs():
    """Load processing logs"""
    conn = get_database_connection()
    df = pd.read_sql("SELECT * FROM processing_logs ORDER BY processing_timestamp DESC LIMIT 50", conn)
    return df

# ==================== HELPER FUNCTIONS ====================

def calculate_kpis(df):
    """Calculate key performance indicators"""
    total_eb = df['eb_consumption'].sum()
    total_dg = df['dg_consumption'].sum()
    total_solar = (df['solar1_consumption'] + df['solar2_consumption']).sum()
    total_power = total_eb + total_dg + total_solar
    
    solar_percentage = (total_solar / total_power * 100) if total_power > 0 else 0
    avg_eui = df['eui_daily'].mean()
    avg_quality = df['data_quality_score'].mean()
    
    return {
        'total_eb': total_eb,
        'total_dg': total_dg,
        'total_solar': total_solar,
        'total_power': total_power,
        'solar_percentage': solar_percentage,
        'avg_eui': avg_eui,
        'avg_quality': avg_quality,
        'total_water': df['water_consumption'].sum(),
        'active_sites': df['site_code'].nunique()
    }

# ==================== SIDEBAR ====================

with st.sidebar:
    st.title("⚡ Navigation")
    
    page = st.radio(
        "Select Page",
        ["📊 Executive Overview", "🏢 Site Analysis", "📈 Comparative Analysis", 
         "🔍 Data Explorer", "📑 Reports", "⚙️ System Status"]
    )
    
    st.markdown("---")
    
    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # Load data
    df_all = load_consumption_data()
    
    if not df_all.empty:
        # Date range filter
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
            df_filtered = df_all[(df_all['date'].dt.date >= start_date) & 
                                 (df_all['date'].dt.date <= end_date)]
        else:
            df_filtered = df_all
        
        st.markdown("---")
        
        # Site filter
        st.subheader("🏢 Site Filter")
        all_sites = ['All Sites'] + sorted(df_filtered['site_code'].unique().tolist())
        selected_sites = st.multiselect(
            "Select Sites",
            options=all_sites,
            default=['All Sites']
        )
        
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
    st.markdown("### Executive Overview")
    
    if df_filtered.empty:
        st.warning("⚠️ No data available for the selected filters")
    else:
        # Calculate KPIs
        kpis = calculate_kpis(df_filtered)
        
        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Power Consumption",
                f"{kpis['total_power']:,.0f} kWh",
                delta=None
            )
        
        with col2:
            delta_eui = kpis['avg_eui'] - 1.0 if kpis['avg_eui'] else None
            st.metric(
                "Average EUI",
                f"{kpis['avg_eui']:.3f}",
                delta=f"{delta_eui:.3f}" if delta_eui else None,
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                "Solar Contribution",
                f"{kpis['solar_percentage']:.1f}%",
                delta=None
            )
        
        with col4:
            st.metric(
                "Active Sites",
                f"{kpis['active_sites']}",
                delta=None
            )
        
        st.markdown("---")
        
        # Charts Row 1
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Daily Power Consumption Trend")
            df_daily = df_filtered.groupby('date')['total_power_consumption'].sum().reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_daily['date'],
                y=df_daily['total_power_consumption'],
                mode='lines+markers',
                name='Total Power',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Consumption (kWh)",
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🔋 Power Source Distribution")
            
            fig = go.Figure(data=[go.Pie(
                labels=['EB', 'DG', 'Solar'],
                values=[kpis['total_eb'], kpis['total_dg'], kpis['total_solar']],
                hole=0.4,
                marker_colors=['#1f77b4', '#ff7f0e', '#2ca02c']
            )])
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Charts Row 2
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏢 Site-wise Total Consumption")
            site_summary = df_filtered.groupby('site_code').agg({
                'eb_consumption': 'sum',
                'dg_consumption': 'sum',
                'solar1_consumption': 'sum',
                'solar2_consumption': 'sum'
            }).reset_index()
            
            site_summary['total_solar'] = site_summary['solar1_consumption'] + site_summary['solar2_consumption']
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='EB',
                x=site_summary['site_code'],
                y=site_summary['eb_consumption'],
                marker_color='#1f77b4'
            ))
            
            fig.add_trace(go.Bar(
                name='DG',
                x=site_summary['site_code'],
                y=site_summary['dg_consumption'],
                marker_color='#ff7f0e'
            ))
            
            fig.add_trace(go.Bar(
                name='Solar',
                x=site_summary['site_code'],
                y=site_summary['total_solar'],
                marker_color='#2ca02c'
            ))
            
            fig.update_layout(
                xaxis_title="Site Code",
                yaxis_title="Consumption (kWh)",
                barmode='stack',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("⚡ EUI Comparison by Site")
            site_eui = df_filtered.groupby('site_code')['eui_daily'].mean().reset_index()
            site_eui = site_eui.sort_values('eui_daily')
            
            colors = ['green' if x <= 1.0 else 'red' for x in site_eui['eui_daily']]
            
            fig = go.Figure(go.Bar(
                x=site_eui['site_code'],
                y=site_eui['eui_daily'],
                marker_color=colors,
                text=site_eui['eui_daily'].round(3),
                textposition='outside'
            ))
            
            fig.add_hline(y=1.0, line_dash="dash", line_color="blue", 
                          annotation_text="Target EUI = 1.0")
            
            fig.update_layout(
                xaxis_title="Site Code",
                yaxis_title="EUI (Energy Use Intensity)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Summary Statistics
        st.markdown("---")
        st.subheader("📊 Summary Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Power Consumption**")
            st.write(f"• EB: {kpis['total_eb']:,.0f} kWh")
            st.write(f"• DG: {kpis['total_dg']:,.0f} kWh")
            st.write(f"• Solar: {kpis['total_solar']:,.0f} kWh")
            st.write(f"• Total: {kpis['total_power']:,.0f} kWh")
        
        with col2:
            st.markdown("**Resources & Quality**")
            st.write(f"• Water: {kpis['total_water']:,.0f} Kl")
            st.write(f"• Avg Quality Score: {kpis['avg_quality']:.1f}/100")
            st.write(f"• Active Sites: {kpis['active_sites']}")
        
        with col3:
            st.markdown("**Date Range**")
            st.write(f"• From: {df_filtered['date'].min().strftime('%d/%m/%Y')}")
            st.write(f"• To: {df_filtered['date'].max().strftime('%d/%m/%Y')}")
            st.write(f"• Total Days: {df_filtered['date'].nunique()}")

# ==================== PAGE 2: SITE ANALYSIS ====================

elif page == "🏢 Site Analysis":
    st.title("🏢 Site-Level Analysis")
    
    if df_filtered.empty:
        st.warning("⚠️ No data available for the selected filters")
    else:
        # Site selector
        site_list = sorted(df_filtered['site_code'].unique())
        selected_site = st.selectbox("Select Site", site_list)
        
        # Filter data for selected site
        site_df = df_filtered[df_filtered['site_code'] == selected_site].copy()
        site_df = site_df.sort_values('date')
        
        # Site information
        site_info = load_site_master()
        # Safely get site details with fallback
        site_match = site_info[site_info['site_code'] == selected_site]
        if not site_match.empty:
            site_details = site_match.iloc
        else:
            # Create default site details if not found
            site_details = pd.Series({
                'site_name': selected_site,
                'region': 'N/A',
                'business_unit': 'N/A',
                'capacity_gsf': 0
            })

        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Site Name", site_details['site_name'])
        
        with col2:
            st.metric("Region", site_details['region'])
        
        with col3:
            st.metric("Business Unit", site_details['business_unit'])
        
        with col4:
            st.metric("Capacity (GSF)", f"{site_details['capacity_gsf']:,.0f}")
        
        st.markdown("---")
        
        # Consumption breakdown
        st.subheader("📊 Power Consumption Breakdown")
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=site_df['date'],
            y=site_df['eb_consumption'],
            name='EB',
            stackgroup='one',
            fillcolor='#1f77b4'
        ))
        
        fig.add_trace(go.Scatter(
            x=site_df['date'],
            y=site_df['dg_consumption'],
            name='DG',
            stackgroup='one',
            fillcolor='#ff7f0e'
        ))
        
        fig.add_trace(go.Scatter(
            x=site_df['date'],
            y=site_df['solar1_consumption'],
            name='Solar-1',
            stackgroup='one',
            fillcolor='#2ca02c'
        ))
        
        fig.add_trace(go.Scatter(
            x=site_df['date'],
            y=site_df['solar2_consumption'],
            name='Solar-2',
            stackgroup='one',
            fillcolor='#98df8a'
        ))
        
        fig.update_layout(
            title=f"Daily Power Consumption - {selected_site}",
            xaxis_title="Date",
            yaxis_title="Consumption (kWh)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # EUI and Water
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 EUI Trend")
            
            fig_eui = go.Figure()
            
            fig_eui.add_trace(go.Scatter(
                x=site_df['date'],
                y=site_df['eui_daily'],
                mode='lines+markers',
                name='EUI',
                line=dict(color='blue', width=2)
            ))
            
            fig_eui.add_hline(y=1.0, line_dash="dash", line_color="red",
                             annotation_text="Target = 1.0")
            
            fig_eui.update_layout(
                xaxis_title="Date",
                yaxis_title="EUI",
                height=300
            )
            
            st.plotly_chart(fig_eui, use_container_width=True)
        
        with col2:
            st.subheader("💧 Water Consumption")
            
            fig_water = go.Figure()
            
            fig_water.add_trace(go.Bar(
                x=site_df['date'],
                y=site_df['water_consumption'],
                name='Water',
                marker_color='lightblue'
            ))
            
            fig_water.update_layout(
                xaxis_title="Date",
                yaxis_title="Water (Kl)",
                height=300
            )
            
            st.plotly_chart(fig_water, use_container_width=True)
        
        # Summary table
        st.markdown("---")
        st.subheader("📋 Daily Data")
        
        display_df = site_df[[
            'date', 'eb_consumption', 'dg_consumption',
            'solar1_consumption', 'solar2_consumption',
            'total_power_consumption', 'water_consumption',
            'eui_daily', 'data_quality_score'
        ]].copy()
        
        display_df['date'] = display_df['date'].dt.strftime('%d/%m/%Y')
        display_df.columns = [
            'Date', 'EB (kWh)', 'DG (kWh)', 'Solar-1 (kWh)', 'Solar-2 (kWh)',
            'Total Power (kWh)', 'Water (Kl)', 'EUI', 'Quality Score'
        ]
        
        st.dataframe(display_df, use_container_width=True, height=400)

# ==================== PAGE 3: COMPARATIVE ANALYSIS ====================

elif page == "📈 Comparative Analysis":
    st.title("📈 Comparative Analysis")
    
    if df_filtered.empty:
        st.warning("⚠️ No data available for the selected filters")
    else:
        # Site comparison summary
        st.subheader("🏆 Site Rankings")
        
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
            site_summary['eb_consumption'] +
            site_summary['dg_consumption'] +
            site_summary['solar1_consumption'] +
            site_summary['solar2_consumption']
        )
        
        site_summary['solar_percentage'] = (
            (site_summary['solar1_consumption'] + site_summary['solar2_consumption']) /
            site_summary['total_power'] * 100
        )
        
        # Ranking tabs
        tab1, tab2, tab3 = st.tabs(["⚡ Power Consumption", "⚡ Efficiency (EUI)", "☀️ Solar %"])
        
        with tab1:
            top_power = site_summary.nlargest(10, 'total_power')[
                ['site_code', 'total_power', 'eb_consumption', 'dg_consumption']
            ].copy()
            
            top_power.columns = ['Site', 'Total Power (kWh)', 'EB (kWh)', 'DG (kWh)']
            
            st.dataframe(top_power, use_container_width=True)
        
        with tab2:
            top_eui = site_summary.nsmallest(10, 'eui_daily')[
                ['site_code', 'eui_daily', 'total_power']
            ].copy()
            
            top_eui.columns = ['Site', 'Average EUI', 'Total Power (kWh)']
            
            st.dataframe(top_eui, use_container_width=True)
        
        with tab3:
            top_solar = site_summary.nlargest(10, 'solar_percentage')[
                ['site_code', 'solar_percentage', 'solar1_consumption', 'solar2_consumption']
            ].copy()
            
            top_solar.columns = ['Site', 'Solar %', 'Solar-1 (kWh)', 'Solar-2 (kWh)']
            
            st.dataframe(top_solar, use_container_width=True)
        
        st.markdown("---")
        
        # Detailed comparison table
        st.subheader("📊 Complete Site Comparison")
        
        comparison_df = site_summary[[
            'site_code', 'total_power', 'eui_daily', 'solar_percentage',
            'water_consumption', 'data_quality_score'
        ]].copy()
        
        comparison_df.columns = [
            'Site', 'Total Power (kWh)', 'Avg EUI', 'Solar %',
            'Water (Kl)', 'Quality Score'
        ]
        
        st.dataframe(comparison_df, use_container_width=True)

# ==================== PAGE 4: DATA EXPLORER ====================

elif page == "🔍 Data Explorer":
    st.title("🔍 Data Explorer")
    
    if df_filtered.empty:
        st.warning("⚠️ No data available for the selected filters")
    else:
        st.subheader("📋 Raw Data")
        
        # Column selector
        all_columns = df_filtered.columns.tolist()
        default_columns = [
            'site_code', 'date', 'eb_consumption', 'dg_consumption',
            'solar1_consumption', 'solar2_consumption', 'total_power_consumption',
            'water_consumption', 'eui_daily', 'data_quality_score'
        ]
        
        selected_columns = st.multiselect(
            "Select Columns to Display",
            options=all_columns,
            default=[col for col in default_columns if col in all_columns]
        )
        
        if selected_columns:
            display_df = df_filtered[selected_columns].copy()
            
            # Format date column if present
            if 'date' in display_df.columns:
                display_df['date'] = display_df['date'].dt.strftime('%d/%m/%Y')
            
            st.dataframe(display_df, use_container_width=True, height=500)
            
            # Download button
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"consumption_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        st.markdown("---")
        
        # Statistical summary
        st.subheader("📊 Statistical Summary")
        
        numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns
        summary_df = df_filtered[numeric_cols].describe().T
        
        st.dataframe(summary_df, use_container_width=True)

# ==================== PAGE 5: REPORTS ====================

elif page == "📑 Reports":
    st.title("📑 Reports & Export")
    
    if df_filtered.empty:
        st.warning("⚠️ No data available for the selected filters")
    else:
        st.subheader("📊 Generate Report")
        
        report_type = st.selectbox(
            "Select Report Type",
            ["Summary Report", "Site-wise Detailed Report", "Consumption Trends Report"]
        )
        
        if st.button("Generate Report", type="primary"):
            if report_type == "Summary Report":
                st.markdown("### Summary Report")
                st.markdown(f"**Date Range:** {df_filtered['date'].min().strftime('%d/%m/%Y')} to {df_filtered['date'].max().strftime('%d/%m/%Y')}")
                
                kpis = calculate_kpis(df_filtered)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Power Consumption**")
                    st.write(f"• Total: {kpis['total_power']:,.0f} kWh")
                    st.write(f"• EB: {kpis['total_eb']:,.0f} kWh")
                    st.write(f"• DG: {kpis['total_dg']:,.0f} kWh")
                    st.write(f"• Solar: {kpis['total_solar']:,.0f} kWh ({kpis['solar_percentage']:.1f}%)")
                
                with col2:
                    st.markdown("**Efficiency Metrics**")
                    st.write(f"• Average EUI: {kpis['avg_eui']:.3f}")
                    st.write(f"• Total Water: {kpis['total_water']:,.0f} Kl")
                    st.write(f"• Active Sites: {kpis['active_sites']}")
                    st.write(f"• Avg Quality Score: {kpis['avg_quality']:.1f}/100")
            
            elif report_type == "Site-wise Detailed Report":
                st.markdown("### Site-wise Detailed Report")
                
                site_summary = df_filtered.groupby('site_code').agg({
                    'eb_consumption': 'sum',
                    'dg_consumption': 'sum',
                    'solar1_consumption': 'sum',
                    'solar2_consumption': 'sum',
                    'water_consumption': 'sum',
                    'eui_daily': 'mean',
                    'data_quality_score': 'mean'
                }).reset_index()
                
                st.dataframe(site_summary, use_container_width=True)
        
        st.markdown("---")
        
        # Export options
        st.subheader("📥 Export Data")
        
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="Download Complete Data as CSV",
            data=csv,
            file_name=f"consumption_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ==================== PAGE 6: SYSTEM STATUS ====================

elif page == "⚙️ System Status":
    st.title("⚙️ System Status")
    
    # Processing logs
    st.subheader("📋 Recent Processing Logs")
    
    logs_df = load_processing_logs()
    
    if not logs_df.empty:
        display_logs = logs_df[[
            'file_name', 'site_code', 'processing_timestamp',
            'status', 'records_processed', 'processing_time_seconds'
        ]].copy()
        
        display_logs.columns = [
            'File Name', 'Site', 'Timestamp', 'Status',
            'Records', 'Time (s)'
        ]
        
        st.dataframe(display_logs, use_container_width=True, height=400)
    else:
        st.info("No processing logs available")
    
    st.markdown("---")
    
    # Database statistics
    st.subheader("📊 Database Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Records", len(df_all))
    
    with col2:
        st.metric("Total Sites", df_all['site_code'].nunique())
    
    with col3:
        st.metric("Date Range", f"{df_all['date'].nunique()} days")



# In[ ]:





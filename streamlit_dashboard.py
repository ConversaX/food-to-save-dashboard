"""
FOOD TO SAVE - Dashboard de Análise Logística
Autor: Claude AI + Engenharia Reversa Galgus AI
Stack: Streamlit + Plotly + Supabase Realtime
Tema: Dark Mode profissional estilo Power BI
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from supabase import create_client, Client
import folium
from streamlit_folium import st_folium
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ============================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================
st.set_page_config(
    page_title="Food To Save - Logística",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# TEMA DARK MODE PERSONALIZADO
# ============================================
st.markdown("""
<style>
    /* Importar fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    /* Tema global */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Cards de métricas */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
    }
    
    /* Labels das métricas */
    div[data-testid="metric-container"] label {
        color: #a0aec0 !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    
    /* Valores das métricas */
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Botões */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
    }
    
    /* Gráficos */
    .js-plotly-plot {
        border-radius: 15px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# CONEXÃO SUPABASE
# ============================================
@st.cache_resource
def init_supabase():
    """Inicializa cliente Supabase com cache"""
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://seu-projeto.supabase.co")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sua-chave-anon")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# ============================================
# FUNÇÕES DE CARREGAMENTO DE DADOS
# ============================================
@st.cache_data(ttl=60)  # Cache de 1 minuto
def load_entregas_data(data_inicio, data_fim, parceiro=None, cidade=None):
    """Carrega dados de entregas com filtros"""
    query = supabase.table('entregas').select('*')
    query = query.gte('data_hora', data_inicio.isoformat())
    query = query.lte('data_hora', data_fim.isoformat())
    
    if parceiro and parceiro != "Todos":
        query = query.eq('parceiro', parceiro)
    
    if cidade and cidade != "Todas":
        query = query.eq('cidade', cidade)
    
    response = query.execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        df['data_hora'] = pd.to_datetime(df['data_hora'])
        df['data'] = df['data_hora'].dt.date
        df['hora'] = df['data_hora'].dt.hour
        df['dia_semana'] = df['data_hora'].dt.day_name()
    
    return df

@st.cache_data(ttl=300)  # Cache de 5 minutos
def load_ranking_parceiros():
    """Carrega ranking de parceiros por cidade"""
    response = supabase.table('ranking_parceiros_cidade').select('*').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def load_analise_picos():
    """Carrega análise de picos de cancelamento"""
    response = supabase.from_('analise_picos_cancelamento').select('*').execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def load_analise_distancia():
    """Carrega análise de distância vs performance"""
    response = supabase.from_('analise_distancia_performance').select('*').execute()
    return pd.DataFrame(response.data)

# ============================================
# SIDEBAR - FILTROS
# ============================================
with st.sidebar:
    st.title("⚙️ Filtros")
    
    # Filtro de data
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=30)
    
    date_range = st.date_input(
        "Período",
        value=(data_inicio, data_fim),
        max_value=datetime.now()
    )
    
    if len(date_range) == 2:
        data_inicio, data_fim = date_range
    
    # Filtro de parceiro
    parceiro_filtro = st.selectbox(
        "Parceiro",
        ["Todos", "Uber", "99"]
    )
    
    # Filtro de cidade (carrega dinamicamente)
    cidades_query = supabase.table('entregas').select('cidade').execute()
    cidades = ["Todas"] + sorted(list(set([c['cidade'] for c in cidades_query.data])))
    cidade_filtro = st.selectbox("Cidade", cidades)
    
    st.markdown("---")
    st.markdown("### 📊 Sobre o Dashboard")
    st.info("""
    **Dados em tempo real** via Google Sheets  
    Atualização: a cada 1 minuto  
    Fonte: Operações Food To Save
    """)
    
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

# ============================================
# CARREGAR DADOS
# ============================================
df_entregas = load_entregas_data(
    pd.to_datetime(data_inicio),
    pd.to_datetime(data_fim),
    parceiro_filtro,
    cidade_filtro
)

df_ranking = load_ranking_parceiros()
df_picos = load_analise_picos()
df_distancia = load_analise_distancia()

# ============================================
# HEADER
# ============================================
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title("🚚 Food To Save - Logística")
with col2:
    st.markdown(f"**Período:** {data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}")
with col3:
    st.markdown(f"**Última atualização:** {datetime.now().strftime('%H:%M:%S')}")

st.markdown("---")

# ============================================
# KPIs PRINCIPAIS
# ============================================
if not df_entregas.empty:
    total_entregas = len(df_entregas)
    total_cancelamentos = len(df_entregas[df_entregas['status_entrega'] == 'cancelado'])
    taxa_cancelamento = (total_cancelamentos / total_entregas * 100) if total_entregas > 0 else 0
    sla_medio = df_entregas['sla_minutos'].mean()
    taxa_sla_cumprido = (df_entregas['cumpriu_sla'].sum() / total_entregas * 100) if total_entregas > 0 else 0
    
    # Melhor parceiro global
    melhor_parceiro_df = df_entregas[df_entregas['status_entrega'] == 'entregue'].groupby('parceiro').size()
    melhor_parceiro = melhor_parceiro_df.idxmax() if not melhor_parceiro_df.empty else "N/A"
    
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    
    with kpi1:
        st.metric("📦 Total Entregas", f"{total_entregas:,}")
    
    with kpi2:
        delta_color = "inverse" if taxa_cancelamento > 5 else "normal"
        st.metric(
            "❌ Taxa Cancelamento",
            f"{taxa_cancelamento:.1f}%",
            delta=f"{total_cancelamentos} cancelados",
            delta_color=delta_color
        )
    
    with kpi3:
        st.metric("⏱️ SLA Médio", f"{sla_medio:.0f} min")
    
    with kpi4:
        st.metric("✅ Cumprimento SLA", f"{taxa_sla_cumprido:.1f}%")
    
    with kpi5:
        st.metric("🏆 Melhor Parceiro", melhor_parceiro)
    
    with kpi6:
        distancia_media = df_entregas['distancia_km'].mean()
        st.metric("🗺️ Distância Média", f"{distancia_media:.1f} km")
    
    st.markdown("---")
    
    # ============================================
    # LAYOUT PRINCIPAL: MAPA + INDICADORES
    # ============================================
    col_mapa, col_indicadores = st.columns([2, 1])
    
    with col_mapa:
        st.subheader("🗺️ Mapa de Calor - Performance por Cidade")
        
        # Agregar dados por cidade
        mapa_dados = df_entregas.groupby('cidade').agg({
            'id': 'count',
            'status_entrega': lambda x: (x == 'cancelado').sum(),
            'distancia_km': 'mean',
            'sla_minutos': 'mean',
            'latitude': 'first',
            'longitude': 'first'
        }).reset_index()
        
        mapa_dados.columns = ['cidade', 'total_entregas', 'cancelamentos', 'dist_media', 'sla_medio', 'lat', 'lon']
        mapa_dados['taxa_cancelamento'] = (mapa_dados['cancelamentos'] / mapa_dados['total_entregas'] * 100).round(2)
        
        # Determinar melhor parceiro por cidade
        melhor_parceiro_cidade = df_entregas[df_entregas['status_entrega'] == 'entregue'].groupby(['cidade', 'parceiro']).size().reset_index(name='entregas_sucesso')
        melhor_parceiro_cidade = melhor_parceiro_cidade.loc[melhor_parceiro_cidade.groupby('cidade')['entregas_sucesso'].idxmax()]
        mapa_dados = mapa_dados.merge(melhor_parceiro_cidade[['cidade', 'parceiro']], on='cidade', how='left')
        
        # Criar mapa com Folium
        if not mapa_dados.empty and mapa_dados['lat'].notna().any():
            center_lat = mapa_dados['lat'].mean()
            center_lon = mapa_dados['lon'].mean()
            
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles='CartoDB dark_matter'
            )
            
            for _, row in mapa_dados.iterrows():
                # Cor baseada na taxa de cancelamento
                if row['taxa_cancelamento'] < 3:
                    color = 'green'
                elif row['taxa_cancelamento'] < 7:
                    color = 'orange'
                else:
                    color = 'red'
                
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=min(row['total_entregas'] / 10, 30),
                    popup=folium.Popup(f"""
                        <b>{row['cidade']}</b><br>
                        Total: {row['total_entregas']}<br>
                        Cancelamentos: {row['taxa_cancelamento']:.1f}%<br>
                        SLA Médio: {row['sla_medio']:.0f} min<br>
                        Melhor Parceiro: {row['parceiro']}
                    """, max_width=250),
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7
                ).add_to(m)
            
            st_folium(m, width=700, height=500)
        else:
            st.warning("Dados de geolocalização não disponíveis para o período selecionado.")
    
    with col_indicadores:
        st.subheader("📍 Top Cidades - Taxa de Cancelamento")
        
        top_cancelamentos = mapa_dados.sort_values('taxa_cancelamento', ascending=False).head(5)
        
        fig_top = go.Figure(go.Bar(
            y=top_cancelamentos['cidade'],
            x=top_cancelamentos['taxa_cancelamento'],
            orientation='h',
            marker=dict(
                color=top_cancelamentos['taxa_cancelamento'],
                colorscale='RdYlGn_r',
                showscale=False
            ),
            text=top_cancelamentos['taxa_cancelamento'].apply(lambda x: f"{x:.1f}%"),
            textposition='outside'
        ))
        
        fig_top.update_layout(
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False),
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        st.plotly_chart(fig_top, use_container_width=True)
        
        st.markdown("---")
        
        st.subheader("🏆 Ranking de Parceiros")
        
        for _, row in df_ranking.head(6).iterrows():
            emoji = "🥇" if row['ranking'] == 1 else "🥈" if row['ranking'] == 2 else "🥉" if row['ranking'] == 3 else "📍"
            st.markdown(f"""
            **{emoji} {row['cidade']} - {row['parceiro']}**  
            Taxa SLA: {row['taxa_sla']:.1f}% | Cancelamentos: {row['taxa_cancelamento']:.1f}%
            """)
    
    st.markdown("---")
    
    # ============================================
    # GRÁFICOS DE ANÁLISE
    # ============================================
    col_grafico1, col_grafico2 = st.columns(2)
    
    with col_grafico1:
        st.subheader("📊 Evolução Temporal - Cancelamentos")
        
        cancelamentos_tempo = df_entregas[df_entregas['status_entrega'] == 'cancelado'].groupby('data').size().reset_index(name='cancelamentos')
        
        fig_tempo = px.line(
            cancelamentos_tempo,
            x='data',
            y='cancelamentos',
            markers=True,
            template='plotly_dark'
        )
        
        fig_tempo.update_traces(
            line=dict(color='#ff6b6b', width=3),
            marker=dict(size=8)
        )
        
        fig_tempo.update_layout(
            height=400,
            xaxis_title="Data",
            yaxis_title="Cancelamentos",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_tempo, use_container_width=True)
    
    with col_grafico2:
        st.subheader("🕐 Picos de Cancelamento por Hora")
        
        cancelamentos_hora = df_entregas[df_entregas['status_entrega'] == 'cancelado'].groupby('hora').size().reset_index(name='cancelamentos')
        
        fig_hora = px.bar(
            cancelamentos_hora,
            x='hora',
            y='cancelamentos',
            color='cancelamentos',
            color_continuous_scale='Reds',
            template='plotly_dark'
        )
        
        fig_hora.update_layout(
            height=400,
            xaxis_title="Hora do Dia",
            yaxis_title="Cancelamentos",
            showlegend=False
        )
        
        st.plotly_chart(fig_hora, use_container_width=True)
    
    # ============================================
    # ANÁLISE DE DISTÂNCIA VS PERFORMANCE
    # ============================================
    st.markdown("---")
    st.subheader("📏 Análise: Distância x Performance por Parceiro")
    
    col_dist1, col_dist2 = st.columns(2)
    
    with col_dist1:
        if not df_distancia.empty:
            fig_dist = px.bar(
                df_distancia,
                x='faixa_distancia',
                y='taxa_cancelamento',
                color='parceiro',
                barmode='group',
                template='plotly_dark',
                labels={'taxa_cancelamento': 'Taxa de Cancelamento (%)', 'faixa_distancia': 'Faixa de Distância'}
            )
            
            fig_dist.update_layout(height=400)
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info("Dados de análise de distância não disponíveis.")
    
    with col_dist2:
        if not df_distancia.empty:
            fig_sla_dist = px.line(
                df_distancia,
                x='faixa_distancia',
                y='taxa_sla',
                color='parceiro',
                markers=True,
                template='plotly_dark',
                labels={'taxa_sla': 'Taxa de Cumprimento SLA (%)', 'faixa_distancia': 'Faixa de Distância'}
            )
            
            fig_sla_dist.update_layout(height=400)
            st.plotly_chart(fig_sla_dist, use_container_width=True)
        else:
            st.info("Dados de análise de SLA por distância não disponíveis.")
    
    # ============================================
    # INSIGHTS AUTOMÁTICOS (IA)
    # ============================================
    st.markdown("---")
    st.subheader("🧠 Insights Automáticos")
    
    insights_col1, insights_col2, insights_col3 = st.columns(3)
    
    with insights_col1:
        # Detectar anomalias na taxa de cancelamento
        if not df_entregas.empty and len(df_entregas) > 7:
            cancelamentos_diarios = df_entregas.groupby('data').apply(lambda x: (x['status_entrega'] == 'cancelado').sum() / len(x) * 100).reset_index(name='taxa')
            
            if len(cancelamentos_diarios) > 2:
                z_scores = np.abs(stats.zscore(cancelamentos_diarios['taxa']))
                anomalias = cancelamentos_diarios[z_scores > 2]
                
                if not anomalias.empty:
                    st.warning(f"""
                    **⚠️ Anomalia Detectada**  
                    {len(anomalias)} dia(s) com taxa de cancelamento anormal:  
                    {', '.join(anomalias['data'].astype(str))}
                    """)
                else:
                    st.success("✅ Nenhuma anomalia detectada no período.")
    
    with insights_col2:
        # Melhor horário para entregas
        if not df_entregas.empty:
            sucesso_por_hora = df_entregas[df_entregas['status_entrega'] == 'entregue'].groupby('hora').size()
            melhor_hora = sucesso_por_hora.idxmax() if not sucesso_por_hora.empty else "N/A"
            
            st.info(f"""
            **⏰ Melhor Horário para Entregas**  
            {melhor_hora}h com maior taxa de sucesso
            """)
    
    with insights_col3:
        # Recomendação de parceiro por distância
        if not df_distancia.empty:
            uber_longa = df_distancia[(df_distancia['parceiro'] == 'Uber') & (df_distancia['faixa_distancia'].isin(['4-6km', '6-10km', '10km+']))]['taxa_cancelamento'].mean()
            nove_nove_longa = df_distancia[(df_distancia['parceiro'] == '99') & (df_distancia['faixa_distancia'].isin(['4-6km', '6-10km', '10km+']))]['taxa_cancelamento'].mean()
            
            if uber_longa < nove_nove_longa:
                recomendacao = "Uber para entregas > 4km"
            else:
                recomendacao = "99 para entregas > 4km"
            
            st.success(f"""
            **🎯 Recomendação Automática**  
            {recomendacao}
            """)
    
    # ============================================
    # TABELA DE DADOS DETALHADOS
    # ============================================
    st.markdown("---")
    st.subheader("📋 Dados Detalhados")
    
    with st.expander("Ver dados brutos das entregas"):
        st.dataframe(
            df_entregas[['data_hora', 'parceiro', 'cidade', 'status_entrega', 'motivo_cancelamento', 'distancia_km', 'tempo_entrega_minutos']].sort_values('data_hora', ascending=False),
            use_container_width=True
        )

else:
    st.warning("⚠️ Nenhum dado disponível para o período selecionado. Ajuste os filtros.")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #a0aec0; padding: 20px;'>
    <p><b>Food To Save - Dashboard de Logística</b></p>
    <p>Powered by n8n + Supabase + Streamlit | Atualização em tempo real</p>
</div>
""", unsafe_allow_html=True)

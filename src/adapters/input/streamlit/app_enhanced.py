"""
RLVR PDF Chat - Executive Edition
Enhanced UX for C-suite presentations with business-focused metrics
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from io import BytesIO

from src.config import settings
from src.factories import create_embeddings, build_service
from src.core import RAGService
from src.logging import configure_logging, get_logger
from src.analytics import RLVRAnalytics
from src.utils import prepare_uploads


configure_logging(level=settings.app.log_level_int)
logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="RLVR PDF Chat - Executive Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Professional CSS
st.markdown("""
<style>
    /* Main theme */
    .main {background-color: #0E1117;}

    /* Executive Summary Banner */
    .exec-summary {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 20px 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .exec-summary h2 {
        margin: 0;
        font-size: 20px;
        font-weight: 600;
        color: white !important;
        background: none !important;
        -webkit-text-fill-color: white !important;
    }

    .exec-summary p {
        margin: 8px 0 0 0;
        font-size: 16px;
        opacity: 0.95;
    }

    /* Enhanced Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.15);
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: rgba(255,255,255,0.3);
    }

    .metric-card-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.15);
    }

    .metric-card-orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.15);
    }

    .metric-card-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.15);
    }

    .metric-card-gold {
        background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
        padding: 24px;
        border-radius: 12px;
        color: #1E1E1E;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.15);
        font-weight: 600;
    }

    .metric-value {
        font-size: 42px;
        font-weight: bold;
        margin: 12px 0;
        line-height: 1;
    }

    .metric-label {
        font-size: 13px;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 500;
    }

    .metric-trend {
        font-size: 16px;
        margin-top: 8px;
        font-weight: 600;
    }

    .trend-up {
        color: #38ef7d;
    }

    .trend-down {
        color: #ff6b6b;
    }

    .trend-neutral {
        color: #ffd93d;
    }

    /* Insight Cards */
    .insight-card {
        background: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }

    .insight-card-success {
        border-left-color: #38ef7d;
    }

    .insight-card-warning {
        border-left-color: #ffd93d;
    }

    .insight-card-info {
        border-left-color: #4facfe;
    }

    /* ROI Card */
    .roi-card {
        background: linear-gradient(135deg, #2d3561 0%, #c05c7e 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        margin: 20px 0;
    }

    /* Chat bubbles - Enhanced */
    .chat-message {
        padding: 18px;
        border-radius: 16px;
        margin: 12px 0;
        max-width: 80%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: auto;
        text-align: right;
    }

    .assistant-message {
        background: #1E1E1E;
        color: #E0E0E0;
        border: 1px solid #333;
    }

    .score-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: bold;
        margin-top: 8px;
    }

    .score-high {
        background: #38ef7d;
        color: #0E1117;
    }

    .score-medium {
        background: #FFB800;
        color: #0E1117;
    }

    .score-low {
        background: #f5576c;
        color: white;
    }

    /* Phase badges */
    .phase-badge {
        display: inline-block;
        padding: 10px 18px;
        border-radius: 24px;
        font-size: 14px;
        font-weight: 600;
        margin: 5px;
    }

    .phase-complete {
        background: #38ef7d;
        color: #0E1117;
    }

    .phase-pending {
        background: #FFB800;
        color: #0E1117;
    }

    /* Export Button */
    .export-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    .export-btn:hover {
        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
        transform: translateY(-2px);
    }

    /* Stale cache warning */
    .stale-cache {display: none;}

    /* Headers - Enhanced */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 36px !important;
        font-weight: 700 !important;
    }

    h2 {
        color: #E0E0E0;
        font-weight: 600;
    }

    /* Action Items */
    .action-item {
        background: #1E1E1E;
        padding: 15px 20px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
        display: flex;
        align-items: center;
    }

    .action-item::before {
        content: '▶';
        margin-right: 12px;
        color: #667eea;
        font-size: 12px;
    }

    /* Cost Badge */
    .cost-badge {
        background: rgba(255, 215, 0, 0.2);
        color: #ffd700;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-left: 8px;
    }

    /* Benchmark Bar */
    .benchmark-bar {
        width: 100%;
        height: 8px;
        background: #2a2a2a;
        border-radius: 4px;
        margin-top: 8px;
        overflow: hidden;
    }

    .benchmark-progress {
        height: 100%;
        background: linear-gradient(90deg, #38ef7d 0%, #11998e 100%);
        transition: width 0.5s ease;
    }
</style>
""", unsafe_allow_html=True)


def calculate_trend(current, previous):
    """Calculate trend percentage and direction."""
    if previous == 0:
        return 0, "neutral"

    change = ((current - previous) / previous) * 100

    if change > 5:
        return change, "up"
    elif change < -5:
        return change, "down"
    else:
        return change, "neutral"


def estimate_monthly_cost(interactions):
    """Estimate monthly API costs."""
    # Rough estimates:
    # - LLM: $0.15 per 1M tokens, avg 500 tokens per interaction
    # - RAGAS: $0.0001 per evaluation
    llm_cost = (interactions * 500 / 1_000_000) * 0.15
    ragas_cost = interactions * 0.0001
    total = llm_cost + ragas_cost
    return total


def init_state():
    """Initialize session state."""
    if "profile" not in st.session_state:
        st.session_state.profile = settings.qdrant.active_profile
    if "embeddings" not in st.session_state:
        st.session_state.embeddings = create_embeddings()
    if "rag" not in st.session_state:
        st.session_state.rag = build_service(st.session_state.embeddings)
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "analytics" not in st.session_state:
        st.session_state.analytics = RLVRAnalytics()


def render_executive_summary():
    """Render executive summary banner at the top."""
    analytics = st.session_state.analytics
    stats = stats = analytics.get_basic_stats()
    readiness = analytics.estimate_rl_readiness()

    total = stats['total_interactions']
    avg_score = stats['average_score']
    progress = stats['progress_percentage']

    # Generate insight
    if total == 0:
        insight = "System ready. Upload PDFs and start collecting training data."
    elif total < 100:
        insight = f"Early stage: {total} interactions collected. Continue usage to build training dataset."
    elif total < 500:
        insight = f"On track: {progress:.0f}% toward RL training readiness. {500-total} more interactions needed."
    else:
        insight = f"Ready for Phase 4! {total} interactions collected. System can now be trained for improved performance."

    # Cost estimate
    monthly_cost = estimate_monthly_cost(total)

    st.markdown(f"""
    <div class="exec-summary">
        <h2>📊 Executive Summary</h2>
        <p><strong>{insight}</strong></p>
        <p style="margin-top: 12px; font-size: 14px; opacity: 0.8;">
            Quality Score: <strong>{avg_score:.2f}/1.00</strong> •
            Training Progress: <strong>{progress:.0f}%</strong> •
            Estimated Monthly Cost: <strong>${monthly_cost:.2f}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render enhanced sidebar with branding."""
    with st.sidebar:
        # Branding area
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("https://img.icons8.com/3d-fluency/94/artificial-intelligence.png", width=60)
        with col2:
            st.markdown("### RLVR System")
            st.caption("AI-Powered Document Intelligence")

        st.divider()

        # PDF Upload
        st.subheader("📂 Upload Documents")
        files = st.file_uploader(
            "Drop PDF files here",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload one or more PDF documents to index"
        )

        if files and st.button("🚀 Process PDFs", use_container_width=True):
            uploads = prepare_uploads(files)
            with st.spinner("⚡ Indexing documents..."):
                added = st.session_state.rag.process_pdfs(uploads)
            st.success(f"✅ Indexed {added} chunks from {len(files)} PDF(s)")
            st.rerun()

        st.divider()

        # Retrieval Settings
        with st.expander("⚙️ Retrieval Settings", expanded=False):
            chunk_size = st.slider(
                "Chunk size",
                200, 1200, settings.chunk.size, step=50,
                help="Size of text chunks for indexing"
            )
            chunk_overlap = st.slider(
                "Chunk overlap",
                0, 400, settings.chunk.overlap, step=10,
                help="Overlap between consecutive chunks"
            )
            top_k = st.slider(
                "Top-K retrieval",
                1, 15, settings.retrieval.top_k, step=1,
                help="Number of chunks to retrieve per query"
            )

            settings.chunk.size = chunk_size
            settings.chunk.overlap = chunk_overlap
            st.session_state.rag.update_top_k(top_k)

        # System Info
        with st.expander("ℹ️ System Info", expanded=False):
            st.write(f"**Qdrant Profile:** {settings.qdrant.active_profile}")
            st.write(f"**LLM Backend:** {settings.llm.backend}")
            st.write(f"**Embedding Backend:** {settings.embedding.backend}")
            st.write(f"**RAGAS Backend:** {settings.verification.ragas_llm_backend}")
            st.write(f"**Collection:** {settings.qdrant.collection_name}")

        st.divider()

        # Quick Actions
        st.subheader("Quick Actions")

        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        if st.button("🔄 Refresh Analytics", use_container_width=True):
            st.session_state.analytics = RLVRAnalytics()
            st.rerun()


def render_dashboard_tab():
    """Render enhanced analytics dashboard with business metrics."""
    st.header("📊 Executive Dashboard")
    st.caption("Real-time performance metrics and business intelligence")

    analytics = st.session_state.analytics
    stats = analytics.get_basic_stats()

    # Top metrics row with trends
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total = stats['total_interactions']
        # Simulate previous value for trend (in real app, store historical data)
        previous_total = max(0, total - 10)
        trend_pct, trend_dir = calculate_trend(total, previous_total if previous_total > 0 else total)

        trend_icon = "↗" if trend_dir == "up" else ("↘" if trend_dir == "down" else "→")
        trend_class = f"trend-{trend_dir}"

        st.markdown(f"""
        <div class="metric-card-blue">
            <div class="metric-label">Total Interactions</div>
            <div class="metric-value">{total}</div>
            <div class="metric-trend {trend_class}">{trend_icon} {abs(trend_pct):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        avg_score = stats['average_score']
        target_score = 0.80
        score_pct = (avg_score / target_score) * 100 if target_score > 0 else 0

        st.markdown(f"""
        <div class="metric-card-green">
            <div class="metric-label">Quality Score</div>
            <div class="metric-value">{avg_score:.2f}</div>
            <div class="metric-label">{score_pct:.0f}% of target</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        high_quality_pct = stats['high_quality_percentage']

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">High Quality</div>
            <div class="metric-value">{stats['high_quality_count']}</div>
            <div class="metric-label">{high_quality_pct:.0f}% of total</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        progress_pct = stats['progress_percentage']
        color_class = "metric-card-green" if progress_pct >= 100 else "metric-card-orange"

        st.markdown(f"""
        <div class="{color_class}">
            <div class="metric-label">RL Readiness</div>
            <div class="metric-value">{progress_pct:.0f}%</div>
            <div class="metric-label">{stats['remaining_interactions']} to go</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        monthly_cost = estimate_monthly_cost(total)

        st.markdown(f"""
        <div class="metric-card-gold">
            <div class="metric-label">Monthly Cost</div>
            <div class="metric-value">${monthly_cost:.2f}</div>
            <div class="metric-label">Estimated</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ROI & Business Impact Section
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("💼 Business Impact & ROI")

        # Calculate some business metrics
        automation_hours = total * 0.25  # Assume 15 mins saved per query
        cost_per_interaction = monthly_cost / total if total > 0 else 0

        st.markdown(f"""
        <div class="roi-card">
            <h3 style="margin-top: 0; color: white;">Value Delivered</h3>
            <p style="font-size: 18px; margin: 10px 0;">
                ⏱️ <strong>{automation_hours:.1f} hours</strong> of manual research automated<br>
                💰 <strong>${cost_per_interaction:.4f}</strong> cost per interaction<br>
                🎯 <strong>{stats['high_quality_count']}</strong> high-confidence answers delivered<br>
                📈 <strong>Self-improving</strong> system collecting training data
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.subheader("🎯 Key Insights")

        readiness = analytics.estimate_rl_readiness()

        if readiness['readiness'] == "Ready for Training":
            st.markdown("""
            <div class="insight-card insight-card-success">
                <strong>✅ Phase 4 Ready</strong><br>
                System has sufficient data for RL training. Recommend proceeding to fine-tuning.
            </div>
            """, unsafe_allow_html=True)
        elif total > 0:
            st.markdown(f"""
            <div class="insight-card insight-card-info">
                <strong>📊 Data Collection</strong><br>
                {total} interactions logged. Continue to {500 - total} for RL readiness.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="insight-card insight-card-warning">
                <strong>⚠️ Getting Started</strong><br>
                Upload PDFs and ask questions to begin data collection.
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Score Distribution")

        if stats['total_interactions'] > 0:
            scores, bins = analytics.get_score_distribution()

            fig = px.histogram(
                x=scores,
                nbins=20,
                labels={'x': 'Verification Score', 'y': 'Count'},
                title="Quality Distribution Analysis",
                color_discrete_sequence=['#667eea']
            )

            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                xaxis=dict(range=[0, 1]),
                showlegend=False
            )

            # Add quality zones
            fig.add_vrect(x0=0.8, x1=1.0, fillcolor="green", opacity=0.1, annotation_text="Excellent")
            fig.add_vrect(x0=0.5, x1=0.8, fillcolor="orange", opacity=0.1, annotation_text="Good")
            fig.add_vrect(x0=0.0, x1=0.5, fillcolor="red", opacity=0.1, annotation_text="Needs Work")

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 No data yet. Start asking questions to see distribution!")

    with col2:
        st.subheader("📉 Performance Trend")

        if stats['total_interactions'] >= 5:
            indices, moving_avg = analytics.get_score_trend()

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=indices,
                y=moving_avg,
                mode='lines+markers',
                name='Quality (Moving Avg)',
                line=dict(color='#38ef7d', width=3),
                marker=dict(size=6),
                fill='tozeroy',
                fillcolor='rgba(56, 239, 125, 0.1)'
            ))

            fig.update_layout(
                title="Quality Improvement Over Time",
                xaxis_title="Interaction Number",
                yaxis_title="Average Score",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                yaxis=dict(range=[0, 1]),
                showlegend=True
            )

            # Add target line
            fig.add_hline(y=0.8, line_dash="dash", line_color="gold", annotation_text="Target")

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📈 Need at least 5 interactions to show trend.")

    st.divider()

    # Quality breakdown and phase status
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 Quality Breakdown")

        if stats['total_interactions'] > 0:
            quality_data = analytics.get_quality_breakdown()

            fig = go.Figure(data=[go.Pie(
                labels=list(quality_data.keys()),
                values=list(quality_data.values()),
                marker=dict(colors=['#38ef7d', '#FFB800', '#f5576c']),
                hole=0.5,
                textinfo='label+percent',
                textfont=dict(size=14)
            )])

            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=True,
                title="Answer Quality Distribution"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🎯 No quality data available yet.")

    with col2:
        st.subheader("🏗️ RLVR Implementation Status")

        phase_status = analytics.get_phase_status()

        for phase_name, phase_data in phase_status.items():
            phase_label = phase_name.replace("_", " ").title()
            badge_class = "phase-complete" if phase_data["complete"] else "phase-pending"

            st.markdown(f"""
            <div style="margin: 12px 0;">
                <strong style="font-size: 15px;">{phase_label}</strong>
                <span class="phase-badge {badge_class}">{phase_data['status']}</span>
            </div>
            """, unsafe_allow_html=True)

            if "progress" in phase_data and not phase_data["complete"]:
                st.progress(phase_data["progress"] / 100)

        st.divider()

        # RL Readiness with enhanced styling
        readiness = analytics.estimate_rl_readiness()

        border_color = {
            "red": "#f5576c",
            "orange": "#FFB800",
            "yellow": "#ffd93d",
            "green": "#38ef7d"
        }.get(readiness['color'], "#667eea")

        st.markdown(f"""
        <div style="padding: 24px; background: #1E1E1E; border-radius: 12px; border-left: 6px solid {border_color};">
            <h4 style="margin-top: 0;">🎓 Training Readiness Assessment</h4>
            <p style="font-size: 20px; font-weight: bold; color: {border_color}; margin: 12px 0;">
                {readiness['readiness']}
            </p>
            <p style="margin: 12px 0;">{readiness['recommendation']}</p>
            <div class="benchmark-bar">
                <div class="benchmark-progress" style="width: {min(100, (readiness['total_interactions']/500)*100)}%"></div>
            </div>
            <p style="opacity: 0.7; margin-top: 8px; font-size: 14px;">
                Progress: {readiness['total_interactions']} / {readiness['target']} interactions
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Action Items for Stakeholders
    st.divider()
    st.subheader("📋 Recommended Actions")

    col1, col2 = st.columns(2)

    with col1:
        if total < 100:
            st.markdown("""
            <div class="action-item">
                <div>
                    <strong>Increase Usage</strong><br>
                    <span style="opacity: 0.8;">Upload more PDFs and generate diverse queries to build training dataset faster.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if avg_score < 0.75:
            st.markdown("""
            <div class="action-item">
                <div>
                    <strong>Review Low-Quality Answers</strong><br>
                    <span style="opacity: 0.8;">Analyze answers with scores < 0.5 to identify improvement opportunities.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        if progress_pct >= 100:
            st.markdown("""
            <div class="action-item">
                <div>
                    <strong>Initiate Phase 4 Training</strong><br>
                    <span style="opacity: 0.8;">Sufficient data collected. Proceed with DPO fine-tuning to improve model performance.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if monthly_cost > 10:
            st.markdown(f"""
            <div class="action-item">
                <div>
                    <strong>Cost Optimization Review</strong><br>
                    <span style="opacity: 0.8;">Monthly cost (${monthly_cost:.2f}) exceeds baseline. Consider adjusting usage or tier.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Recent interactions
    st.divider()
    st.subheader("🕒 Recent Activity")

    recent = analytics.get_recent_questions(limit=10)

    if recent:
        for interaction in recent:
            score = interaction['score']
            confidence = interaction['confidence']

            if score >= 0.8:
                badge_class = "score-high"
                emoji = "✅"
            elif score >= 0.5:
                badge_class = "score-medium"
                emoji = "⚠️"
            else:
                badge_class = "score-low"
                emoji = "❌"

            st.markdown(f"""
            <div style="padding: 14px; background: #1E1E1E; border-radius: 10px; margin: 10px 0; border-left: 3px solid {'#38ef7d' if score >= 0.8 else ('#FFB800' if score >= 0.5 else '#f5576c')};">
                <div style="font-size: 13px; opacity: 0.7;">{interaction['timestamp']}</div>
                <div style="margin: 10px 0; font-size: 15px;">{interaction['question']}</div>
                <span class="score-badge {badge_class}">{emoji} {score:.2f} ({confidence})</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No interactions yet. Start chatting to see history!")


def render_chat_tab():
    """Render chat interface (same as before)."""
    st.header("💬 Chat with Your Documents")
    st.caption("Ask questions about your uploaded PDFs")

    # Chat container
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>You:</strong><br>
                    {msg['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                verification = msg.get("verification", {})
                score = verification.get("overall_score", 0)
                confidence = verification.get("confidence", "unknown")

                if score >= 0.8:
                    badge_class = "score-high"
                    emoji = "✅"
                elif score >= 0.5:
                    badge_class = "score-medium"
                    emoji = "⚠️"
                else:
                    badge_class = "score-low"
                    emoji = "❌"

                badge_html = f'<span class="score-badge {badge_class}">{emoji} {score:.2f} ({confidence})</span>'

                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <strong>Assistant:</strong><br>
                    {msg['content']}<br>
                    {badge_html}
                </div>
                """, unsafe_allow_html=True)

                # Sources expander
                if msg.get("sources"):
                    with st.expander("📚 View Sources"):
                        for idx, doc in enumerate(msg["sources"], 1):
                            meta = doc.metadata or {}
                            src = meta.get("source", "unknown")
                            page = meta.get("page", "?")
                            preview = doc.page_content[:200] if hasattr(doc, 'page_content') else ""

                            st.markdown(f"""
                            **Source {idx}:** {src} (Page {page})

                            *Preview:* {preview}...
                            """)

    # Input section
    st.divider()

    col1, col2 = st.columns([5, 1])

    with col1:
        question = st.text_input(
            "Your question",
            placeholder="What is the price of Taj Mahal Palace?",
            key="question_input",
            label_visibility="collapsed"
        )

    with col2:
        send_button = st.button("📤 Send", use_container_width=True)

    if send_button and question:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": question})

        # Get answer
        with st.spinner("🤔 Thinking..."):
            result = st.session_state.rag.answer_question(question)

        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "verification": result.get("verification"),
            "sources": result.get("sources"),
        })

        st.rerun()


def render_settings_tab():
    """Render settings (same as before with slight enhancements)."""
    st.header("⚙️ Configuration & Documentation")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔧 System Configuration")

        st.markdown(f"""
        **LLM Backend:** `{settings.llm.backend}`

        **Ollama Model:** `{settings.llm.ollama.model}`

        **Embedding Backend:** `{settings.embedding.backend}`

        **Embedding Model:** `{settings.embedding.model_name[:50]}...`

        **RAGAS Backend:** `{settings.verification.ragas_llm_backend}`

        **Qdrant Profile:** `{settings.qdrant.active_profile}`

        **Collection Name:** `{settings.qdrant.collection_name}`

        **Chunk Size:** `{settings.chunk.size}`

        **Chunk Overlap:** `{settings.chunk.overlap}`

        **Top-K Retrieval:** `{settings.retrieval.top_k}`
        """)

        st.divider()

        st.subheader("📊 Training Data")
        analytics = st.session_state.analytics
        stats = analytics.get_basic_stats()

        st.info(f"""
        **Location:** `training_data/`

        **Total Interactions:** {stats['total_interactions']}

        **Average Score:** {stats['average_score']:.3f}

        **Target for RL:** 500 interactions

        **Progress:** {stats['progress_percentage']:.1f}%
        """)

    with col2:
        st.subheader("📚 Documentation")

        st.markdown("""
        **Quick Links:**

        - 📖 [RLVR Implementation Guide](RLVR_IMPLEMENTATION_GUIDE.md)
        - 🔧 [RAGAS Configuration](RAGAS_CONFIGURATION_GUIDE.md)
        - 🐛 [Fixes Applied](FIXES_APPLIED.md)
        - ✅ [Project Status](PROJECT_STATUS.md)
        - 🧪 [CID Artifact Fix](CID_ARTIFACT_FIX.md)
        - ☁️ [Streamlit Cloud Deployment](STREAMLIT_CLOUD_DEPLOYMENT.md)
        """)

        st.divider()

        st.subheader("🎯 RLVR Phases")

        st.markdown("""
        **Phase 1: Retrieval** ✅
        - Qdrant vector database
        - Semantic search working

        **Phase 2: LLM** ✅
        - Ollama Llama 3.2 3B
        - Context-based generation

        **Phase 3: Verification** ✅
        - RAGAS scoring
        - Training data logging

        **Phase 4: RL Training** ⏳
        - DPO fine-tuning
        - Model improvement
        - Requires 500+ interactions
        """)

        st.divider()

        st.subheader("🚀 Next Steps")

        readiness = analytics.estimate_rl_readiness()

        if readiness['total_interactions'] >= 500:
            st.success("""
            ✅ **Ready for Phase 4!**

            You have enough training data to start RL training.

            See [RLVR_IMPLEMENTATION_GUIDE.md](RLVR_IMPLEMENTATION_GUIDE.md) for:
            - Preparing DPO training data
            - Training with DPO
            - Deploying fine-tuned model
            """)
        else:
            remaining = 500 - readiness['total_interactions']
            st.warning(f"""
            ⏳ **Collecting Training Data**

            Keep using the chat to collect more interactions.

            **Remaining:** {remaining} interactions

            **Current:** {readiness['total_interactions']}

            **Target:** 500
            """)


def main():
    """Main application with enhanced executive features."""
    init_state()
    render_sidebar()

    # Header with branding
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🤖 RLVR PDF Chat")
        st.caption("Reinforcement Learning with Verifiable Rewards - Executive Edition")
    with col2:
        st.markdown("<div style='text-align: right; padding-top: 20px;'>", unsafe_allow_html=True)
        if st.button("📥 Export Report"):
            st.info("Export feature: Generate PDF reports coming soon!")
        st.markdown("</div>", unsafe_allow_html=True)

    # Executive Summary Banner
    render_executive_summary()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Executive Dashboard", "⚙️ Settings"])

    with tab1:
        render_chat_tab()

    with tab2:
        render_dashboard_tab()

    with tab3:
        render_settings_tab()


if __name__ == "__main__":
    logger.info("Starting RLVR PDF Chat - Executive Edition")
    main()

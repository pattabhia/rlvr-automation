"""
RLVR PDF Chat - Professional UI
Redesigned with analytics dashboard for CTO presentations
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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
    page_title="RLVR PDF Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS
st.markdown("""
<style>
    /* Main theme */
    .main {background-color: #0E1117;}

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .metric-card-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .metric-card-orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .metric-card-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .metric-value {
        font-size: 36px;
        font-weight: bold;
        margin: 10px 0;
    }

    .metric-label {
        font-size: 14px;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Chat bubbles */
    .chat-message {
        padding: 15px;
        border-radius: 15px;
        margin: 10px 0;
        max-width: 80%;
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
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
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
        padding: 8px 16px;
        border-radius: 20px;
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

    /* Stale cache warning */
    .stale-cache {display: none;}

    /* Headers */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
</style>
""", unsafe_allow_html=True)


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


def render_sidebar():
    """Render sidebar with controls."""
    with st.sidebar:
        st.image("https://img.icons8.com/3d-fluency/94/artificial-intelligence.png", width=80)
        st.title("RLVR Control Panel")

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
    """Render the analytics dashboard."""
    st.header("📊 RLVR Analytics Dashboard")
    st.caption("Real-time metrics and training progress visualization")

    analytics = st.session_state.analytics
    stats = analytics.get_basic_stats()

    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card-blue">
            <div class="metric-label">Total Interactions</div>
            <div class="metric-value">{stats['total_interactions']}</div>
            <div class="metric-label">Collected</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card-green">
            <div class="metric-label">Average Score</div>
            <div class="metric-value">{stats['average_score']:.2f}</div>
            <div class="metric-label">Quality</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">High Quality</div>
            <div class="metric-value">{stats['high_quality_count']}</div>
            <div class="metric-label">{stats['high_quality_percentage']:.0f}% of total</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        progress_pct = stats['progress_percentage']
        color_class = "metric-card-green" if progress_pct >= 100 else "metric-card-orange"
        st.markdown(f"""
        <div class="{color_class}">
            <div class="metric-label">Training Progress</div>
            <div class="metric-value">{progress_pct:.0f}%</div>
            <div class="metric-label">{stats['remaining_interactions']} to target</div>
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
                title="Distribution of Verification Scores",
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
            fig.add_vrect(x0=0.8, x1=1.0, fillcolor="green", opacity=0.1, annotation_text="High")
            fig.add_vrect(x0=0.5, x1=0.8, fillcolor="orange", opacity=0.1, annotation_text="Medium")
            fig.add_vrect(x0=0.0, x1=0.5, fillcolor="red", opacity=0.1, annotation_text="Low")

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 No data yet. Start asking questions to see score distribution!")

    with col2:
        st.subheader("📉 Score Trend")

        if stats['total_interactions'] >= 5:
            indices, moving_avg = analytics.get_score_trend()

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=indices,
                y=moving_avg,
                mode='lines+markers',
                name='Moving Average (10)',
                line=dict(color='#38ef7d', width=3),
                marker=dict(size=6)
            ))

            fig.update_layout(
                title="Score Trend Over Time (Moving Average)",
                xaxis_title="Interaction Number",
                yaxis_title="Average Score",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                yaxis=dict(range=[0, 1]),
                showlegend=True
            )

            # Add target line
            fig.add_hline(y=0.8, line_dash="dash", line_color="green", annotation_text="Target Quality")

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
                hole=0.4
            )])

            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🎯 No quality data available yet.")

    with col2:
        st.subheader("🏗️ RLVR Phase Status")

        phase_status = analytics.get_phase_status()

        for phase_name, phase_data in phase_status.items():
            phase_label = phase_name.replace("_", " ").title()
            badge_class = "phase-complete" if phase_data["complete"] else "phase-pending"

            st.markdown(f"""
            <div style="margin: 10px 0;">
                <strong>{phase_label}</strong>
                <span class="phase-badge {badge_class}">{phase_data['status']}</span>
            </div>
            """, unsafe_allow_html=True)

            if "progress" in phase_data and not phase_data["complete"]:
                st.progress(phase_data["progress"] / 100)

        st.divider()

        # RL Readiness
        readiness = analytics.estimate_rl_readiness()

        st.markdown(f"""
        <div style="padding: 20px; background: #1E1E1E; border-radius: 10px; border-left: 4px solid {readiness['color']};">
            <h4>🎓 RL Training Readiness</h4>
            <p style="font-size: 18px; font-weight: bold; color: {readiness['color']};">
                {readiness['readiness']}
            </p>
            <p>{readiness['recommendation']}</p>
            <p style="opacity: 0.7;">
                Progress: {readiness['total_interactions']} / {readiness['target']} interactions
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Recent interactions
    st.divider()
    st.subheader("🕒 Recent Interactions")

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
            <div style="padding: 12px; background: #1E1E1E; border-radius: 8px; margin: 8px 0;">
                <div style="font-size: 14px; opacity: 0.7;">{interaction['timestamp']}</div>
                <div style="margin: 8px 0;">{interaction['question']}</div>
                <span class="score-badge {badge_class}">{emoji} {score:.2f} ({confidence})</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No interactions yet. Start chatting to see history!")


def render_chat_tab():
    """Render the chat interface."""
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
    """Render settings and configuration."""
    st.header("⚙️ Settings & Configuration")

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
    """Main application."""
    init_state()
    render_sidebar()

    # Header
    st.title("🤖 RLVR PDF Chat")
    st.caption("Reinforcement Learning with Verifiable Rewards - Production Demo")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Analytics", "⚙️ Settings"])

    with tab1:
        render_chat_tab()

    with tab2:
        render_dashboard_tab()

    with tab3:
        render_settings_tab()


if __name__ == "__main__":
    logger.info("Starting RLVR PDF Chat with professional UI")
    main()

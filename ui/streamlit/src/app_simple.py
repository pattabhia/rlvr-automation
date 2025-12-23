"""
RLVR Automation Demo - Simple UI with Explainability
"""

import streamlit as st
from utils.api_client import get_api_client
import time
from datetime import datetime

# Page config
st.set_page_config(
    page_title="RLVR Automation Demo",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "api_client" not in st.session_state:
    st.session_state.api_client = get_api_client()
if "processing" not in st.session_state:
    st.session_state.processing = False

# Simple CSS
st.markdown("""
<style>
    .main {background: #f5f5f5;}
    .stTextInput > div > div > input {
        font-size: 16px;
        padding: 12px;
    }
    .user-msg {
        background: #dcf8c6;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
        text-align: right;
    }
    .bot-msg {
        background: white;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .metrics-box {
        background: #e3f2fd;
        padding: 16px;
        border-radius: 8px;
        margin-top: 12px;
        border-left: 4px solid #1976d2;
    }
    .metric-row {
        display: flex;
        gap: 24px;
        margin: 8px 0;
    }
    .metric {
        flex: 1;
    }
    .metric-label {
        font-size: 12px;
        color: #666;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #1976d2;
    }
    .event-id {
        font-size: 11px;
        color: #666;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🤖 RLVR PDF Chat")
st.markdown("Ask questions about your AWS documents")

# API Links
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("[📚 QA API](http://localhost:8000/docs)")
with col2:
    st.markdown("[🔍 Ground Truth API](http://localhost:8001/docs)")
with col3:
    st.markdown("[📊 Training Data API](http://localhost:8002/docs)")

st.markdown("---")

# Chat container
chat_container = st.container()

# Display chat history
with chat_container:
    for msg in st.session_state.chat_history:
        # User question
        st.markdown(f"""
        <div class="user-msg">
            <strong>You:</strong> {msg['question']}
            <div style="font-size: 11px; color: #666; margin-top: 4px;">{msg.get('timestamp', '')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Bot answer
        st.markdown(f"""
        <div class="bot-msg">
            <strong>🤖 AI Assistant:</strong><br/>
            {msg['answer']}
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics (if available)
        verification = msg.get('verification', {})
        if verification:
            faithfulness = verification.get('faithfulness_score', 0)
            relevancy = verification.get('relevancy_score', 0)
            overall = verification.get('overall_score', 0)
            event_id = msg.get('metadata', {}).get('event_id', 'N/A')
            
            st.markdown(f"""
            <div class="metrics-box">
                <div style="font-weight: 600; color: #1976d2; margin-bottom: 12px;">📊 Answer Quality Metrics</div>
                <div class="metric-row">
                    <div class="metric">
                        <div class="metric-label">Faithfulness</div>
                        <div class="metric-value">{faithfulness:.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Relevancy</div>
                        <div class="metric-value">{relevancy:.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Overall Score</div>
                        <div class="metric-value">{overall:.2f}</div>
                    </div>
                </div>
                <div class="event-id">Event ID: <code>{event_id}</code></div>
            </div>
            """, unsafe_allow_html=True)
        
        # Context sources (expandable)
        with st.expander(f"📚 View {len(msg.get('contexts', []))} Context Sources"):
            for i, ctx in enumerate(msg.get('contexts', []), 1):
                st.markdown(f"**Source {i}** (Score: {ctx.get('score', 0):.2f})")
                st.markdown(f"📄 {ctx.get('metadata', {}).get('source', 'Unknown')}")
                st.text(ctx.get('content', '')[:400] + "...")
                st.markdown("---")

# Input area
st.markdown("---")

# Question input
question = st.text_input(
    "Ask a question:",
    placeholder="e.g., What is AWS Lambda?",
    key="question_input"
)

if st.button("Send", disabled=not question):
    with st.spinner("🤔 Thinking... (Generating 3 candidate answers, this may take 60-90 seconds on CPU)"):
        try:
            # Call multi-candidate API (generates 3 candidates in background)
            result = st.session_state.api_client.ask_question_multi_candidate(
                question=question,
                publish_events=True  # Enable background RAGAS verification
            )

            # Get the best candidate (first one - they're not ranked yet)
            # In future, we could rank by initial heuristics, but for now just use first
            candidates = result.get('candidates', [])
            if not candidates:
                st.error("No candidates generated")
                st.stop()

            best_candidate = candidates[0]

            # Get event ID from best candidate
            event_id = best_candidate.get('metadata', {}).get('event_id')

            # Wait for verification (up to 10 seconds)
            verification_data = None
            if event_id:
                for attempt in range(10):
                    try:
                        entries = st.session_state.api_client.get_entries(limit=10)
                        for entry in entries:
                            if entry.get('metadata', {}).get('answer_event_id') == event_id:
                                verification_data = entry.get('verification')
                                break
                        if verification_data:
                            break
                        time.sleep(1)
                    except:
                        time.sleep(1)

            # Add to chat history (using best candidate)
            chat_item = {
                'question': question,
                'answer': best_candidate.get('answer', ''),
                'contexts': best_candidate.get('contexts', []),
                'metadata': best_candidate.get('metadata', {}),
                'timestamp': datetime.now().strftime("%H:%M"),
                'verification': verification_data,
                'num_candidates': result.get('num_candidates', 1),
                'events_published': result.get('events_published', 0)
            }

            st.session_state.chat_history.append(chat_item)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            time.sleep(2)
            st.rerun()



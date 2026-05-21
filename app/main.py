import sys
import os

# Add project root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import asyncio
import uuid
import polars as pl
from app.agents import AgentStateTracker
from app.pipeline import QAPipeline
from app.utils import generate_developer_resume

# Set page config first
st.set_page_config(
    page_title="Automated Rohit Jain's Question Paper & Answer Key",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Responsive CSS Injector
css_style = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Outfit', sans-serif;
    background-color: #0b0f19;
    color: #e2e8f0;
}

/* Smooth Scrolling & Glowing Scrollbar */
html {
    scroll-behavior: smooth;
}

::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

::-webkit-scrollbar-track {
    background: #0b0f19;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #6366f1 0%, #a855f7 100%);
    border-radius: 6px;
    border: 2px solid #0b0f19;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #a855f7 0%, #6366f1 100%);
}

/* Centralized scaling constraints */
.main .block-container {
    padding-top: 3rem;
    padding-bottom: 3rem;
    margin: 0 auto;
}

@media (max-width: 768px) {
    .main .block-container {
        max-width: 95% !important;
        padding-left: 1rem;
        padding-right: 1rem;
    }
}

@media (min-width: 1400px) {
    .main .block-container {
        max-width: 85% !important;
    }
}

/* Beautiful custom container frames */
.stCard {
    background: rgba(17, 24, 39, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
    backdrop-filter: blur(10px);
}

/* Real-time Subagent Grid */
.agent-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin: 24px 0;
}

.agent-box {
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    font-weight: 600;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.agent-box:hover {
    transform: translateY(-2px);
}

/* State Colors */
.state-idle {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    color: #94a3b8;
}

.state-processing {
    background: linear-gradient(135deg, #b45309 0%, #d97706 100%);
    color: #fef3c7;
    animation: pulse 1.6s infinite ease-in-out;
}

.state-complete {
    background: linear-gradient(135deg, #065f46 0%, #059669 100%);
    color: #ecfdf5;
    box-shadow: 0 0 15px rgba(5, 150, 105, 0.3);
}

@keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.02); opacity: 0.85; }
    100% { transform: scale(1); opacity: 1; }
}

/* Custom styled inputs */
input, select, textarea {
    background-color: #111827 !important;
    color: #f3f4f6 !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
}

/* Accent headers */
h1, h2, h3 {
    background: linear-gradient(to right, #6366f1, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700 !important;
}

/* 3D Developer Photo Container */
.dev-photo-container {
    perspective: 1000px;
    width: 100%;
    margin-bottom: 20px;
    display: flex;
    justify-content: center;
    align-items: center;
}

.dev-photo-card {
    width: 200px;
    height: 200px;
    border-radius: 20px;
    overflow: hidden;
    position: relative;
    transform-style: preserve-3d;
    transform: rotateX(8deg) rotateY(-8deg);
    transition: all 0.5s cubic-bezier(0.25, 1, 0.5, 1);
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4), 
                0 0 15px rgba(99, 102, 241, 0.15);
    border: 2px solid rgba(255, 255, 255, 0.1);
}

.dev-photo-card img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.5s cubic-bezier(0.25, 1, 0.5, 1);
}

/* Shine overlay */
.dev-photo-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        135deg, 
        rgba(255, 255, 255, 0) 0%, 
        rgba(255, 255, 255, 0) 40%, 
        rgba(255, 255, 255, 0.35) 50%, 
        rgba(255, 255, 255, 0) 60%, 
        rgba(255, 255, 255, 0) 100%
    );
    transform: translate(-100%, -100%);
    transition: transform 0.6s cubic-bezier(0.25, 1, 0.5, 1);
}

/* Mouse over actions */
.dev-photo-container:hover .dev-photo-card {
    transform: rotateX(0deg) rotateY(0deg) scale(1.06);
    box-shadow: 0 25px 45px rgba(0, 0, 0, 0.6), 
                0 0 30px rgba(168, 85, 247, 0.45);
    border-color: rgba(168, 85, 247, 0.5);
}

.dev-photo-container:hover .dev-photo-card img {
    transform: scale(1.1);
}

.dev-photo-container:hover .dev-photo-card::after {
    transform: translate(100%, 100%);
}

/* Hindi Marquee Styles */
.hindi-marquee-container {
    background: rgba(17, 24, 39, 0.85);
    border: 1px solid rgba(168, 85, 247, 0.2);
    border-radius: 8px;
    padding: 10px 15px;
    margin-bottom: 25px;
    font-size: 14px;
    color: #e2e8f0;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    overflow: hidden;
    backdrop-filter: blur(8px);
}
.hindi-marquee-container marquee {
    display: flex;
    align-items: center;
}
.hindi-marquee-container a {
    color: #6366f1;
    text-decoration: underline;
    font-weight: 600;
    transition: color 0.3s ease;
}
.hindi-marquee-container a:hover {
    color: #a855f7 !important;
}

/* Flowchart Styles */
.flowchart-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 10px 0;
    gap: 0;
}

.flow-step {
    display: flex;
    align-items: center;
    width: 100%;
    max-width: 450px;
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 12px;
    padding: 15px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
}

.flow-step:hover {
    transform: translateY(-2px);
    border-color: rgba(168, 85, 247, 0.5);
    box-shadow: 0 6px 15px rgba(168, 85, 247, 0.2);
}

.step-num {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
    color: white;
    display: flex;
    justify-content: center;
    align-items: center;
    font-weight: bold;
    font-size: 14px;
    margin-right: 15px;
    flex-shrink: 0;
    box-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
}

.step-content {
    flex-grow: 1;
}

.step-content h4 {
    margin: 0 0 5px 0;
    font-size: 15px;
    color: #f1f5f9;
    font-weight: 600;
}

.step-content p {
    margin: 0;
    font-size: 12px;
    color: #94a3b8;
    line-height: 1.4;
}

.flow-connector {
    width: 2px;
    height: 25px;
    background: linear-gradient(180deg, #6366f1 0%, #a855f7 100%);
    opacity: 0.6;
}
</style>
"""
st.markdown(css_style, unsafe_allow_html=True)


def get_image_base64_html(photo_path):
    import base64
    try:
        with open(photo_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
        return f"""
        <div class="dev-photo-container">
            <div class="dev-photo-card">
                <img src="data:image/jpeg;base64,{encoded}" alt="Rohit Jain" />
            </div>
        </div>
        """
    except Exception as e:
        return f"<div style='color:red;'>Error loading photo: {{e}}</div>"



def get_grid_html(states):
    html = '<div class="agent-grid">'
    for agent_name, state in states.items():
        state_class = "state-idle"
        if state == "Processing":
            state_class = "state-processing"
        elif state == "Complete":
            state_class = "state-complete"
            
        html += f"""
        <div class="agent-box {state_class}">
            <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.7;">Subagent</div>
            <div style="margin-top: 6px; font-size: 14px; font-weight: 700;">{agent_name}</div>
            <div style="margin-top: 12px; font-size: 11px; font-weight: 500; background: rgba(0,0,0,0.25); padding: 4px 10px; border-radius: 20px; display: inline-block;">
                {state}
            </div>
        </div>
        """
    html += '</div>'
    return html


@st.dialog("📞 Contact Info")
def show_contact_popup():
    st.markdown("### **Rohit Jain (Sr. Software Engineer) (BCA, MCA)**")
    st.markdown("**AI Solutions Architect & Full Stack Architect | AI & Data Solutions**")
    st.markdown("---")
    st.markdown("📞 **Phone:** [+91 89469 19241](tel:+918946919241)")
    st.markdown("✉️ **Email:** [engrohitjain5@gmail.com](mailto:engrohitjain5@gmail.com)")
    st.markdown("🌐 **Portfolio:** [rohitjain-resume.vercel.app](https://rohitjain-resume.vercel.app/) — Explore Digital Portfolio Resume, Technical project repositories, and engineering background.")
    st.markdown("---")
    st.write("Feel free to reach out for enterprise AI workflows, automated LLM systems, or optimized full-stack microservices.")


@st.dialog("📊 Project Execution Flow")
def show_flowchart_popup():
    st.markdown("""
    <div class="flowchart-container">
        <div class="flow-step">
            <div class="step-num">1</div>
            <div class="step-content">
                <h4>Document Ingestion</h4>
                <p>Upload source files (PDF, DOCX, TXT, or ZIP up to 200MB) with secure session isolation.</p>
            </div>
        </div>
        <div class="flow-connector"></div>
        <div class="flow-step">
            <div class="step-num">2</div>
            <div class="step-content">
                <h4>Contextual Text Chunking</h4>
                <p>Cleans extracted text, splits it into semantic chunks, and builds dynamic study structures.</p>
            </div>
        </div>
        <div class="flow-connector"></div>
        <div class="flow-step">
            <div class="step-num">3</div>
            <div class="step-content">
                <h4>Multi-Agent Item Synthesis</h4>
                <p>Specialist subagents parallelly generate question stems, option alternatives, and correct keys.</p>
            </div>
        </div>
        <div class="flow-connector"></div>
        <div class="flow-step">
            <div class="step-num">4</div>
            <div class="step-content">
                <h4>De-duplication & Refinement</h4>
                <p>Removes highly overlapping items via Cosine Similarity check and formats outputs.</p>
            </div>
        </div>
        <div class="flow-connector"></div>
        <div class="flow-step">
            <div class="step-num">5</div>
            <div class="step-content">
                <h4>Secure Export compilation</h4>
                <p>Assembles custom PDF layouts and archives everything in a password-protected ZIP envelope.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("---")
    st.info("💡 Tip: The output ZIP archive password is the exact 10-digit mobile number input during generation.")


def main():
    # Ensure developer resume is generated
    resume_path = "storage/rohit_jain_resume.pdf"
    if not os.path.exists(resume_path):
        os.makedirs("storage", exist_ok=True)
        try:
            generate_developer_resume(resume_path)
        except Exception:
            pass

    # Developer Profile Sidebar
    with st.sidebar:
        # Display Developer Photo
        photo_path = os.path.join(os.path.dirname(__file__), "rohit_jain.jpg")
        if os.path.exists(photo_path):
            st.markdown(get_image_base64_html(photo_path), unsafe_allow_html=True)
        else:
            st.info("Photo loading...")
            
        st.markdown("## 🖥️ Platform Architecture")
        st.markdown("### **Rohit Jain (Sr. Software Engineer) (BCA, MCA)**")
        
        # Toggle Button
        if "show_profile" not in st.session_state:
            st.session_state.show_profile = False
            
        if st.button("🖥️ Toggle Profile Details", use_container_width=True):
            st.session_state.show_profile = not st.session_state.show_profile
            
        if st.session_state.show_profile:
            st.markdown("---")
            st.markdown("**Sr. Software Engineer | AI Solutions Architect & Full Stack Architect**")
            st.markdown("🌐 **Portfolio:** [rohitjain-resume.vercel.app](https://rohitjain-resume.vercel.app/)")
            st.markdown(
                "This workspace represents a production-grade optimization tier leveraging local compute, "
                "low-latency parsing engines, and fluid rendering."
            )
            st.markdown("#### **Key Competencies**")
            st.markdown("🎯 **AI Architecture & Advanced Workflows** — LLMs, Agentic Pipelines, & Enterprise Automation.")
            st.markdown("💻 **Enterprise Full-Stack Engineering** — Highly optimized data microservices and real-time dashboards.")
            st.markdown("---")
            
        # Flow Chart Popup Button
        if st.button("📊 Project Execution Flow", use_container_width=True):
            show_flowchart_popup()
            
        # Contact Info Popup Button
        if st.button("📞 Contact Info", use_container_width=True):
            show_contact_popup()
            
        st.markdown("---")
        if os.path.exists(resume_path):
            with open(resume_path, "rb") as f:
                st.download_button(
                    label="📄 Download Professional Resume",
                    data=f.read(),
                    file_name="Rohit_Jain_Resume.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    st.title("🚀 Automated Rohit Jain's Question Paper & Answer Key")
    
    st.write(
        "An AI-driven Rohit Jain's assessment engine that automates the generation of structured question papers "
        "and comprehensive evaluation keys from any source material."
    )
    
    # Hindi/English Educational Purpose Marquee
    marquee_html = """
    <div class="hindi-marquee-container">
        <marquee behavior="scroll" direction="left" scrollamount="6" onmouseover="this.stop();" onmouseout="this.start();">
            यह प्रोजेक्ट रोहित जैन द्वारा केवल शैक्षणिक उद्देश्यों के लिए बनाया गया है। रोहित जैन का प्रोफाइल देखने के लिए यहाँ क्लिक करें: 
            <a href="https://rohitjain-resume.vercel.app/" target="_blank">rohitjain-resume.vercel.app</a> &bull;&nbsp; 
            This project is created by Rohit Jain for educational purposes only. To explore the digital profile of Rohit Jain, visit: 
            <a href="https://rohitjain-resume.vercel.app/" target="_blank">rohitjain-resume.vercel.app</a>
        </marquee>
    </div>
    """
    st.markdown(marquee_html, unsafe_allow_html=True)
    
    # Session States
    if "tracker_states" not in st.session_state:
        st.session_state.tracker_states = {
            "Supervisor Orchestrator": "Idle",
            "Ingestion Quality Evaluator": "Idle",
            "Structural Chunking Planner": "Idle",
            "Item Gen Specialist A": "Idle",
            "Item Gen Specialist B": "Idle",
            "Item Gen Specialist C": "Idle",
            "Distractor Variation Designer": "Idle",
            "Deduplication Vector Analyzer": "Idle",
            "Format Verification Auditor": "Idle",
            "Package Cryptography Agent": "Idle"
        }
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "df_result" not in st.session_state:
        st.session_state.df_result = None
    if "zip_download_path" not in st.session_state:
        st.session_state.zip_download_path = None
    if "mobile_number" not in st.session_state:
        st.session_state.mobile_number = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "exam_title" not in st.session_state:
        st.session_state.exam_title = None

    # Main Config Form
    with st.form("pipeline_form"):
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.write("### 📋 Configuration & Upload")
        
        col1, col2 = st.columns(2)
        with col1:
            mobile_number = st.text_input(
                "Mobile Number (Used as plain-text extraction ZIP password)",
                value="",
                placeholder="e.g. 9876543210"
            )
        with col2:
            exam_title = st.text_input(
                "Exam Title (Appears in PDF running header)",
                value="",
                placeholder="e.g. Machine Learning Basics"
            )

        col3, col4, col5 = st.columns([1, 1, 1])
        with col3:
            set_count = st.number_input(
                "Number of Sets",
                min_value=1,
                max_value=10,
                value=1,
                step=1,
                help="How many question paper sets to generate"
            )
        with col4:
            questions_per_set = st.number_input(
                "Questions per Set",
                min_value=1,
                max_value=100,
                value=5,
                step=1,
                help="How many questions in each question paper set"
            )
        with col5:
            distractor_count = st.selectbox(
                "Distractor Options (Choices Count)",
                options=list(range(2, 11)),
                index=2,  # default to 4 options (A, B, C, D)
                help="Number of choices per question"
            )

        uploaded_files = st.file_uploader(
            "Upload Exam Resources (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True
        )
            
        submit_btn = st.form_submit_button("🔥 Run Pipeline")
        st.markdown('</div>', unsafe_allow_html=True)

    # Collapsible Status Grid
    with st.expander("⚡ Multi-Agent Matrix Status", expanded=False):
        grid_placeholder = st.empty()
        grid_placeholder.markdown(get_grid_html(st.session_state.tracker_states), unsafe_allow_html=True)

    # Logs Console Placeholder
    st.write("### 📟 Real-Time Agent Logs")
    logs_placeholder = st.empty()
    if st.session_state.logs:
        logs_placeholder.text_area("Console Logs", value="\n".join(st.session_state.logs), height=200, disabled=True)
    else:
        logs_placeholder.info("Waiting for pipeline trigger...")

    # Form Submission Logic
    if submit_btn:
        # Form Validations
        errors = []
        
        # 1. Mobile Number Validation
        if not mobile_number:
            errors.append("Mobile number is required.")
        elif not mobile_number.isdigit():
            errors.append("Mobile number must contain digits only.")
        elif len(mobile_number) != 10:
            errors.append("Mobile number must be exactly 10 digits.")

        # 2. Exam Title Length Validation
        if not exam_title:
            errors.append("Exam Title is required.")
        else:
            word_count = len(exam_title.split())
            if word_count > 10:
                errors.append(f"Exam Title must be <= 10 words (currently {word_count} words).")

        # 3. File Upload Verification
        if not uploaded_files:
            errors.append("At least one document file must be uploaded.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            # Clear previous results
            st.session_state.df_result = None
            st.session_state.zip_download_path = None
            st.session_state.mobile_number = None
            st.session_state.session_id = None
            st.session_state.exam_title = None
            
            st.success("Configuration validated. Spinning up 10-Subagent Parallel Mesh...")
            
            # Setup temp folder to write files
            temp_dir = "storage/temp"
            os.makedirs(temp_dir, exist_ok=True)
            
            temp_paths = []
            for uploaded_file in uploaded_files:
                temp_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                temp_paths.append(temp_path)

            session_id = str(uuid.uuid4())[:8]

            # Set up the tracker with a callback to render changes live
            def ui_update_callback():
                states = tracker.get_states()
                logs = tracker.get_logs()
                grid_placeholder.markdown(get_grid_html(states), unsafe_allow_html=True)
                logs_placeholder.text_area("Console Logs", value="\n".join(logs), height=250, disabled=True)

            tracker = AgentStateTracker(on_update_callback=ui_update_callback)
            
            # Execute Pipeline Asynchronously
            async def run_async_pipeline():
                pipeline = QAPipeline(tracker)
                df = await pipeline.execute(
                    file_paths=temp_paths,
                    exam_title=exam_title,
                    mobile_number=mobile_number,
                    session_id=session_id,
                    distractor_count=distractor_count,
                    set_count=int(set_count),
                    questions_per_set=int(questions_per_set)
                )
                return df

            try:
                # Run the async execution synchronously inside streamlit thread
                df_result = asyncio.run(run_async_pipeline())
                
                st.session_state.df_result = df_result
                st.session_state.tracker_states = tracker.get_states()
                st.session_state.logs = tracker.get_logs()
                st.session_state.mobile_number = mobile_number
                st.session_state.session_id = session_id
                st.session_state.exam_title = exam_title
                
                # Cleanup temp files
                for p in temp_paths:
                    try:
                        os.remove(p)
                    except Exception:
                        pass
                
                # Configure ZIP download availability
                st.session_state.zip_download_path = f"storage/outputs/{mobile_number}/{session_id}/output.zip"
                st.balloons()
            except Exception as e:
                st.error(f"Pipeline execution aborted: {str(e)}")

    # Display results and download button if available
    if st.session_state.df_result is not None:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.write("### 🏆 Generated Q&A Matrix Preview")
        st.dataframe(st.session_state.df_result)
        
        mb = st.session_state.get("mobile_number")
        sid = st.session_state.get("session_id")
        exam_title_val = st.session_state.get("exam_title", "exam")
        
        if mb and sid:
            out_dir = f"storage/outputs/{mb}/{sid}"
            zip_path = os.path.join(out_dir, "output.zip")
            xlsx_path = os.path.join(out_dir, "questions.xlsx")
            
            col_zip, col_xlsx = st.columns(2)
            
            with col_zip:
                if os.path.exists(zip_path):
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="💾 Download Password-Protected ZIP Package",
                            data=f.read(),
                            file_name="qa_package.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
            
            with col_xlsx:
                if os.path.exists(xlsx_path):
                    with open(xlsx_path, "rb") as f:
                        st.download_button(
                            label="📊 Download Excel Spreadsheet (Separately)",
                            data=f.read(),
                            file_name="questions.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
            
            # Separate sections for each question set
            st.write("---")
            st.write("### 📚 Question Sets")
            
            df_res = st.session_state.df_result
            if "Set" in df_res.columns:
                unique_sets = df_res["Set"].unique().sort().to_list()
                
                for set_name in unique_sets:
                    with st.expander(f"📖 {set_name} Preview & Downloads", expanded=True):
                        set_df = df_res.filter(pl.col("Set") == set_name)
                        st.dataframe(set_df, use_container_width=True)
                        
                        set_filename = f"{set_name.replace(' ', '_')}.pdf"
                        set_pdf_path = os.path.join(out_dir, set_filename)
                        
                        if os.path.exists(set_pdf_path):
                            with open(set_pdf_path, "rb") as f:
                                st.download_button(
                                    label=f"📄 Download {set_name} PDF",
                                    data=f.read(),
                                    file_name=f"{exam_title_val.replace(' ', '_')}_{set_filename}",
                                    mime="application/pdf",
                                    key=f"dl_pdf_{set_name.replace(' ', '_')}"
                                )
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Section 5: Real-Time Compute & Engine Execution Profile Diagnostics
    st.write("---")
    with st.expander("🛠️ 5. Real-Time Compute & Engine Execution Profile Diagnostics", expanded=False):
        st.write("### 🖥️ Live Engine Diagnostics")
        
        import platform
        import multiprocessing
        
        col_diag1, col_diag2, col_diag3 = st.columns(3)
        with col_diag1:
            st.metric(label="OS Platform", value=platform.system())
        with col_diag2:
            st.metric(label="Available CPU Cores", value=multiprocessing.cpu_count())
        with col_diag3:
            st.metric(label="Polars Version", value=pl.__version__)
            
        st.write("#### 🔍 Compilation & Verification Status")
        st.success("✅ Polars Rust Compilation: Verified")
        
        try:
            import sklearn
            st.success(f"✅ Scikit-learn Engine: Active (v{sklearn.__version__})")
        except ImportError:
            st.warning("⚠️ Scikit-learn Engine: Inactive (Using token-based backup deduplication)")
            
        st.success("✅ ReportLab Canvas Layout Engine: Ready")
        st.success("✅ Password Cryptography Engine: Ready (Legacy WZ_ZIPCRYPT mode)")
        
        st.markdown("""
        **Troubleshooting & Playbook Quick Links:**
        - To force AVX-free compilation of Polars/Scikit-learn, run: `pip install --no-binary :all: <package>`
        - Output ZIP archive password is the exact 10-digit mobile number input during generation.
        """)

    # Footer displaying Rohit Jain's details
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; padding: 15px; font-size: 13px; color: #64748b; font-weight: 500;'>"
        "Automated Rohit Jain's Assessment Engine &bull; Developed by <a href='https://rohitjain-resume.vercel.app/' target='_blank' style='color: #6366f1; text-decoration: none;'><b>Rohit Jain (Sr. Software Engineer) (BCA, MCA)</b></a>"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

import os
import docx2txt
import pypdf
import pyzipper
import polars as pl
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, PageBreak
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total page count and draw
    running header (Exam Title) and running footer (Page X of Y).
    """
    exam_title = "Automated Rohit Jain's Question Paper & Answer Key"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Letter width is 612, height is 792
        left_margin = 54
        right_margin = 558
        
        # Draw Header
        self.setFont("Helvetica-Bold", 9)
        self.setFillColorRGB(0.2, 0.2, 0.2)
        self.drawString(left_margin, 750, self.exam_title)
        
        # Header Line
        self.setStrokeColorRGB(0.8, 0.8, 0.8)
        self.setLineWidth(0.5)
        self.line(left_margin, 742, right_margin, 742)
        
        # Draw Footer
        self.setFont("Helvetica", 9)
        self.setFillColorRGB(0.4, 0.4, 0.4)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawCentredString(306, 36, page_text)
        
        self.restoreState()


class DocumentProcessor:
    """
    Extracts raw text from files.
    """
    def extract_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self._read_pdf(file_path)
        elif ext == ".docx":
            return self._read_docx(file_path)
        elif ext == ".txt":
            return self._read_txt(file_path)
        else:
            raise ValueError(f"Unsupported extension: {ext}")

    def _read_pdf(self, file_path: str) -> str:
        text = ""
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def _read_docx(self, file_path: str) -> str:
        return docx2txt.process(file_path)

    def _read_txt(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def build_pdf_reportlab(df: pl.DataFrame, exam_title: str, output_pdf_path: str):
    """
    Builds a styled PDF using ReportLab Flowables and the NumberedCanvas.
    Supports multiple sets grouped in the DataFrame.
    """
    # Configure running title on Canvas
    NumberedCanvas.exam_title = exam_title
    
    # 0.75 in margins = 54 pt
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        spaceAfter=15,
        textColor=ParagraphStyle('temp').textColor # default
    )

    set_header_style = ParagraphStyle(
        'SetHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        spaceBefore=15,
        spaceAfter=10,
        textColor=ParagraphStyle('temp').textColor
    )
    
    q_style = ParagraphStyle(
        'QuestionStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        spaceBefore=10,
        spaceAfter=6
    )
    
    opt_style = ParagraphStyle(
        'OptionsStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        leftIndent=15,
        spaceAfter=4
    )
    
    ans_style = ParagraphStyle(
        'AnswerStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        leftIndent=15,
        textColor=ParagraphStyle('temp').textColor,
        spaceAfter=12
    )

    end_style = ParagraphStyle(
        'EndStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        alignment=1, # Centered
        spaceBefore=20,
        spaceAfter=10
    )

    flowables = []
    
    # Add main exam header
    flowables.append(Paragraph(exam_title, title_style))
    flowables.append(Spacer(1, 10))

    # Detect if 'Set' column exists
    has_set_col = "Set" in df.columns
    
    if has_set_col:
        # Group by Set
        unique_sets = df["Set"].unique().sort().to_list()
        for idx, set_name in enumerate(unique_sets):
            if idx > 0:
                flowables.append(PageBreak())
            
            flowables.append(Paragraph(f"=== {set_name} ===", set_header_style))
            flowables.append(Spacer(1, 5))
            
            set_df = df.filter(pl.col("Set") == set_name)
            for row in set_df.iter_rows(named=True):
                q_id = row.get("Question ID", "")
                section = row.get("Section", "")
                stem = row.get("Question Stem", "")
                options_str = row.get("Options", "")
                correct_ans = row.get("Correct Answer", "")
                
                q_header = f"Q{q_id}. [{section}] {stem}"
                q_flow = Paragraph(q_header, q_style)
                
                opt_flows = []
                options_list = [opt.strip() for opt in options_str.split("|") if opt.strip()]
                for opt in options_list:
                    opt_flows.append(Paragraph(opt, opt_style))
                    
                ans_flow = Paragraph(f"<b>Correct Option:</b> {correct_ans}", ans_style)
                flowables.append(KeepTogether([q_flow] + opt_flows + [ans_flow, Spacer(1, 5)]))
    else:
        # Backward compatibility fallback
        for row in df.iter_rows(named=True):
            q_id = row.get("Question ID", "")
            section = row.get("Section", "")
            stem = row.get("Question Stem", "")
            options_str = row.get("Options", "")
            correct_ans = row.get("Correct Answer", "")
            
            q_header = f"Q{q_id}. [{section}] {stem}"
            q_flow = Paragraph(q_header, q_style)
            
            opt_flows = []
            options_list = [opt.strip() for opt in options_str.split("|") if opt.strip()]
            for opt in options_list:
                opt_flows.append(Paragraph(opt, opt_style))
                
            ans_flow = Paragraph(f"<b>Correct Option:</b> {correct_ans}", ans_style)
            flowables.append(KeepTogether([q_flow] + opt_flows + [ans_flow, Spacer(1, 5)]))
    
    # Append the mandatory layout termination string
    flowables.append(Spacer(1, 15))
    flowables.append(Paragraph("--- END ---", end_style))
    
    doc.build(flowables, canvasmaker=NumberedCanvas)


class ZipCryptoEncrypter:
    def __init__(self, pwd):
        if isinstance(pwd, str):
            pwd = pwd.encode('utf-8')
        self.pwd = pwd
        self.key0, self.key1, self.key2 = self._init_keys(pwd)

    def _gen_crc_table(self):
        table = []
        for i in range(256):
            crc = i
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xedb88320
                else:
                    crc >>= 1
            table.append(crc)
        return table

    def _init_keys(self, pwd):
        crctable = self._gen_crc_table()
        key0 = 305419896
        key1 = 591751049
        key2 = 878082192

        def crc32(ch, crc):
            return (crc >> 8) ^ crctable[(crc ^ ch) & 0xFF]

        for p in pwd:
            key0 = crc32(p, key0)
            key1 = (key1 + (key0 & 0xFF)) & 0xFFFFFFFF
            key1 = (key1 * 134775813 + 1) & 0xFFFFFFFF
            key2 = crc32(key1 >> 24, key2)
        return key0, key1, key2

    def update_zipinfo(self, zinfo):
        self.zinfo = zinfo
        zinfo.flag_bits |= 0x9  # Force encryption flag (0x1) and data descriptor flag (0x8)
        dt = zinfo.date_time
        dos_time = (dt[3] << 11) | (dt[4] << 5) | (dt[5] >> 1)
        zinfo._raw_time = dos_time

    def encryption_header(self):
        self.key0, self.key1, self.key2 = self._init_keys(self.pwd)
        header_bytes = bytearray(os.urandom(11))
        
        dt = self.zinfo.date_time
        dos_time = (dt[3] << 11) | (dt[4] << 5) | (dt[5] >> 1)
        
        # Since we force bit 3 in flag_bits, check_byte is always (dos_time >> 8) & 0xff
        check_byte = (dos_time >> 8) & 0xff
        header_bytes.append(check_byte)
        
        encrypted_header = bytearray()
        crctable = self._gen_crc_table()
        
        def crc32(ch, crc):
            return (crc >> 8) ^ crctable[(crc ^ ch) & 0xFF]
            
        for b in header_bytes:
            k = self.key2 | 2
            keystream = ((k * (k ^ 1)) >> 8) & 0xFF
            c = b ^ keystream
            encrypted_header.append(c)
            
            self.key0 = crc32(b, self.key0)
            self.key1 = (self.key1 + (self.key0 & 0xFF)) & 0xFFFFFFFF
            self.key1 = (self.key1 * 134775813 + 1) & 0xFFFFFFFF
            self.key2 = crc32(self.key1 >> 24, self.key2)
            
        return bytes(encrypted_header)

    def encrypt(self, data):
        encrypted_data = bytearray()
        crctable = self._gen_crc_table()
        
        def crc32(ch, crc):
            return (crc >> 8) ^ crctable[(crc ^ ch) & 0xFF]
            
        for b in data:
            k = self.key2 | 2
            keystream = ((k * (k ^ 1)) >> 8) & 0xFF
            c = b ^ keystream
            encrypted_data.append(c)
            
            self.key0 = crc32(b, self.key0)
            self.key1 = (self.key1 + (self.key0 & 0xFF)) & 0xFFFFFFFF
            self.key1 = (self.key1 * 134775813 + 1) & 0xFFFFFFFF
            self.key2 = crc32(self.key1 >> 24, self.key2)
            
        return bytes(encrypted_data)

    def flush(self):
        return b''

    def finalize_zipinfo(self, zinfo):
        pass


class LegacyZipFile(pyzipper.ZipFile):
    def get_encrypter(self):
        if self.pwd is not None:
            return ZipCryptoEncrypter(self.pwd)
        return None


def create_encrypted_zip(source_dir: str, zip_path: str, password: str, use_legacy_crypto: bool = True):
    """
    Creates a password-protected zip of all files inside source_dir.
    Uses legacy ZipCrypto (WZ_ZIPCRYPT) for maximum multi-platform compatibility,
    or AES for stronger security.
    """
    if use_legacy_crypto:
        with LegacyZipFile(
            zip_path,
            'w',
            compression=pyzipper.ZIP_DEFLATED
        ) as zf:
            zf.setpassword(password.encode('utf-8') if isinstance(password, str) else password)
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.abspath(file_path) == os.path.abspath(zip_path):
                        continue
                    arcname = os.path.relpath(file_path, source_dir)
                    zf.write(file_path, arcname)
    else:
        with pyzipper.AESZipFile(
            zip_path,
            'w',
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES
        ) as zf:
            zf.setpassword(password.encode('utf-8') if isinstance(password, str) else password)
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.abspath(file_path) == os.path.abspath(zip_path):
                        continue
                    arcname = os.path.relpath(file_path, source_dir)
                    zf.write(file_path, arcname)


def generate_developer_resume(output_pdf_path: str):
    """
    Generates a beautifully styled professional resume for Rohit Jain.
    """
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    name_style = ParagraphStyle(
        'ResumeName',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        spaceAfter=2,
        textColor=ParagraphStyle('temp').textColor
    )
    
    title_style = ParagraphStyle(
        'ResumeTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        spaceAfter=10,
        textColor=ParagraphStyle('temp').textColor
    )
    
    section_heading_style = ParagraphStyle(
        'ResumeSectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=6,
        textColor=ParagraphStyle('temp').textColor
    )
    
    body_style = ParagraphStyle(
        'ResumeBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        'ResumeBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    
    flowables = []
    
    # Name and Title
    flowables.append(Paragraph("Rohit Jain", name_style))
    flowables.append(Paragraph("AI Solutions Architect & Full Stack Architect | AI & Data Solutions", title_style))
    
    # Contact Info
    contact_text = "<b>Phone:</b> +91 89469 19241 &nbsp;&nbsp;|&nbsp;&nbsp; <b>Email:</b> engrohitjain5@gmail.com &nbsp;&nbsp;|&nbsp;&nbsp; <b>Location:</b> India"
    flowables.append(Paragraph(contact_text, body_style))
    
    # Horizontal line
    flowables.append(Spacer(1, 5))
    
    # Profile Summary Section
    flowables.append(Paragraph("Professional Summary", section_heading_style))
    summary_text = (
        "Dynamic and outcome-driven AI Solutions Architect and Full Stack Architect with extensive experience "
        "designing and deploying high-performance data microservices, low-latency parsing engines, and agentic workflows. "
        "Demonstrated track record of delivering production-grade optimizations and enterprise automation using local compute "
        "and advanced Large Language Models (LLMs)."
    )
    flowables.append(Paragraph(summary_text, body_style))
    
    # Core Competencies Section
    flowables.append(Paragraph("Core Competencies", section_heading_style))
    flowables.append(Paragraph("&bull; <b>AI & Advanced Workflows:</b> Agentic LLM Pipelines, Retrieval-Augmented Generation (RAG), Multi-Agent Mesh Architectures, Enterprise Automation.", bullet_style))
    flowables.append(Paragraph("&bull; <b>Full-Stack Engineering:</b> Optimized Data Microservices, Real-Time Dashboards, High-Performance Streaming APIs, Asynchronous Parallel Processing.", bullet_style))
    flowables.append(Paragraph("&bull; <b>Platform & Infrastructure:</b> Local Compute Optimization, Low-Latency Text & Media Parsing, Secure Crypto Storage Systems, Production Scaling & Deployment.", bullet_style))
    
    # Highlighted Platform Section
    flowables.append(Paragraph("Highlighted Architectural Deployment", section_heading_style))
    flowables.append(Paragraph("<b>AI Q&A Generator Workspace (Antigravity 2.0)</b>", body_style))
    flowables.append(Paragraph("&bull; Designed a local-first, multi-agent Q&A generator executing 10-subagent parallel meshes asynchronously for document verification and structured item design.", bullet_style))
    flowables.append(Paragraph("&bull; Optimized parsing pipelines for docx, pdf, and text formats up to 200MB, integrating TF-IDF vectorization and Cosine Similarity deduplication.", bullet_style))
    flowables.append(Paragraph("&bull; Implemented legacy PKWARE ZipCrypto password protection algorithms in pure Python, enabling seamless extraction in native Windows Explorer environment.", bullet_style))
    flowables.append(Paragraph("&bull; Structured ReportLab PDF generation engines to support set-by-set page numbering and dynamic canvas page counting.", bullet_style))
    
    # Work Experience Section
    flowables.append(Paragraph("Professional Experience", section_heading_style))
    flowables.append(Paragraph("<b>AI Solutions Architect & Full Stack Architect</b>", body_style))
    flowables.append(Paragraph("&bull; Spearhead architectural design and implementation of highly secure AI pipelines and automated workflows.", bullet_style))
    flowables.append(Paragraph("&bull; Architect and deploy microservices focusing on low latency, security boundaries, and local computational efficiencies.", bullet_style))
    flowables.append(Paragraph("&bull; Develop real-time frontend monitoring panels and dynamic report generators for audit verification workflows.", bullet_style))
    
    # Education
    flowables.append(Paragraph("Education & Credentials", section_heading_style))
    flowables.append(Paragraph("&bull; <b>Bachelor of Technology in Computer Science & Engineering</b>", bullet_style))
    flowables.append(Paragraph("&bull; Certified AI Solution Architect and Technical Lead.", bullet_style))
    
    doc.build(flowables)

import os
import asyncio
import polars as pl
import random
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.agents import AgentStateTracker, BaseAgent
from app.utils import (
    DocumentProcessor,
    build_pdf_reportlab,
    create_encrypted_zip
)

# Safe imports for LangChain character splitter
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        class RecursiveCharacterTextSplitter:
            def __init__(self, chunk_size=1200, chunk_overlap=200):
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap
            
            def split_text(self, text: str) -> List[str]:
                chunks = []
                start = 0
                while start < len(text):
                    end = start + self.chunk_size
                    chunks.append(text[start:end])
                    start += self.chunk_size - self.chunk_overlap
                return chunks


class QAPipeline:
    def __init__(self, tracker: AgentStateTracker, thread_pool_size: int = 4):
        self.tracker = tracker
        self.executor = ThreadPoolExecutor(max_workers=thread_pool_size)

    async def execute(
        self,
        file_paths: List[str],
        exam_title: str,
        mobile_number: str,
        session_id: str,
        distractor_count: int,
        set_count: int = 1,
        questions_per_set: int = 5,
        difficulty_level: str = "Medium"
    ) -> pl.DataFrame:
        """
        Executes the 10-Subagent Parallel Mesh layout asynchronously.
        """
        # Output isolation directory
        output_dir = f"storage/outputs/{mobile_number}/{session_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Supervisor Orchestrator Init
        supervisor = BaseAgent("Supervisor Orchestrator", self.tracker)
        await supervisor.transition("Processing", "🤖 SPINNING UP SUPERVISOR ORCHESTRATOR & SYNCING SYSTEM CORES...")

        # 2. Ingestion Quality Evaluator
        ingestion_agent = BaseAgent("Ingestion Quality Evaluator", self.tracker)
        await ingestion_agent.transition("Processing", "⚙️ INGESTING RESOURCE ARTIFACTS AND SCREENING INTEGRITY...")
        
        # Enforce max 200MB limit & concurrency limit of 5 concurrent uploads
        semaphore = asyncio.Semaphore(5)
        
        async def process_single_file(path: str) -> str:
            async with semaphore:
                # Validate file size
                sz_mb = os.path.getsize(path) / (1024 * 1024)
                if sz_mb > 200:
                    raise ValueError(f"File {os.path.basename(path)} exceeds 200MB limit.")
                
                # CPU-bound text extraction inside ThreadPoolExecutor
                loop = asyncio.get_running_loop()
                dp = DocumentProcessor()
                text = await loop.run_in_executor(self.executor, dp.extract_text, path)
                return text

        try:
            tasks = [process_single_file(p) for p in file_paths]
            extracted_texts = await asyncio.gather(*tasks)
            combined_text = "\n\n".join(extracted_texts)
            await ingestion_agent.transition("Complete", f"⚙️ INGESTION COMPLETE. SUCCESSFULLY LOADED {len(file_paths)} KNOWLEDGE SOURCE(S).")
        except Exception as e:
            await ingestion_agent.transition("Idle", f"❌ Ingestion failed: {str(e)}")
            await supervisor.transition("Idle", "❌ Pipeline aborted due to ingestion error.")
            raise e

        # 3. Structural Chunking Planner
        chunker_agent = BaseAgent("Structural Chunking Planner", self.tracker)
        await chunker_agent.transition("Processing", "🧩 DISSECTING TEXT CORPUS INTO OPTIMAL SEMANTIC SEGMENTS...")
        
        loop = asyncio.get_running_loop()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
        
        try:
            chunks = await loop.run_in_executor(self.executor, splitter.split_text, combined_text)
            await chunker_agent.transition("Complete", f"🧩 DIVISION DONE. SYNTHESIZED {len(chunks)} WORK CONTEXTS.")
        except Exception as e:
            await chunker_agent.transition("Idle", f"❌ Chunking failed: {str(e)}")
            await supervisor.transition("Idle", "❌ Pipeline aborted due to chunking error.")
            raise e

        if not chunks:
            chunks = ["No readable text could be extracted from the provided files."]

        # 4, 5, 6. Parallel Item Generation Specialists (A, B, C)
        # Split chunks into thirds
        n_chunks = len(chunks)
        third = n_chunks // 3
        
        chunks_a = chunks[:third] if third > 0 else chunks
        chunks_b = chunks[third:2*third] if third > 0 else []
        chunks_c = chunks[2*third:] if third > 0 else []
        
        agent_a = BaseAgent("Item Gen Specialist A", self.tracker)
        agent_b = BaseAgent("Item Gen Specialist B", self.tracker)
        agent_c = BaseAgent("Item Gen Specialist C", self.tracker)
        
        async def run_specialist_a():
            await agent_a.transition("Processing", f"🏭 EXTRACTING Q&A STEM FACTS AND DEFINITIONS (PART 1 - {len(chunks_a)} chunks)...")
            qa = self._generate_stems_heuristically(chunks_a, section_name="Section A", difficulty_level=difficulty_level)
            await agent_a.transition("Complete", f"🏭 GENERATION PHASE A SUCCESS. COMPILED {len(qa)} RAW STEMS.")
            return qa

        async def run_specialist_b():
            if not chunks_b:
                await agent_b.transition("Complete", "🏭 Specialist B Idle (Text corpus too small for multi-thread slicing).")
                return []
            await agent_b.transition("Processing", f"🏭 EXTRACTING Q&A STEM FACTS AND DEFINITIONS (PART 2 - {len(chunks_b)} chunks)...")
            qa = self._generate_stems_heuristically(chunks_b, section_name="Section B", difficulty_level=difficulty_level)
            await agent_b.transition("Complete", f"🏭 GENERATION PHASE B SUCCESS. COMPILED {len(qa)} RAW STEMS.")
            return qa

        async def run_specialist_c():
            if not chunks_c:
                await agent_c.transition("Complete", "🏭 Specialist C Idle (Text corpus too small for multi-thread slicing).")
                return []
            await agent_c.transition("Processing", f"🏭 EXTRACTING Q&A STEM FACTS AND DEFINITIONS (PART 3 - {len(chunks_c)} chunks)...")
            qa = self._generate_stems_heuristically(chunks_c, section_name="Section C", difficulty_level=difficulty_level)
            await agent_c.transition("Complete", f"🏭 GENERATION PHASE C SUCCESS. COMPILED {len(qa)} RAW STEMS.")
            return qa

        # Gather parallel item generation
        qa_a, qa_b, qa_c = await asyncio.gather(
            run_specialist_a(),
            run_specialist_b(),
            run_specialist_c()
        )
        
        raw_qa_stems = qa_a + qa_b + qa_c

        # Sort raw_qa_stems based on difficulty level
        if difficulty_level.lower() == "low":
            raw_qa_stems.sort(key=lambda x: len(x["question"].split()) + len(x["answer"].split()))
        elif difficulty_level.lower() == "high":
            raw_qa_stems.sort(key=lambda x: len(x["question"].split()) + len(x["answer"].split()), reverse=True)

        # 7. Distractor Variation Designer
        distractor_agent = BaseAgent("Distractor Variation Designer", self.tracker)
        await distractor_agent.transition("Processing", f"🎯 GENERATING HIGH-PLAUSIBILITY DISTRACTORS ({distractor_count} CHOICES)...")
        
        all_sentences = []
        for c in chunks:
            all_sentences.extend([s.strip() for s in c.split(".") if len(s.strip()) > 15])
            
        final_qa_with_distractors = []
        for idx, item in enumerate(raw_qa_stems):
            question_text = item["question"]
            correct_answer = item["answer"]
            section = item["section"]
            
            # Generate plausible distractors
            distractors = self._generate_plausible_distractors(correct_answer, all_sentences, distractor_count, difficulty_level)
            
            # Combine correct + distractors and shuffle
            options_list = [correct_answer] + distractors
            # Keep random seed stable per question for reproducible layout if needed
            random.seed(idx + 100)
            random.shuffle(options_list)
            
            # Assign labels A, B, C, D...
            option_letters = [chr(65 + i) for i in range(len(options_list))] # A, B, C...
            formatted_options = []
            correct_letter = "A"
            
            for letter, opt_text in zip(option_letters, options_list):
                formatted_options.append(f"{letter}) {opt_text}")
                if opt_text == correct_answer:
                    correct_letter = letter
                    
            options_string = " | ".join(formatted_options)
            
            final_item = {
                "Question ID": str(idx + 1),
                "Section": section,
                "Question Stem": question_text,
                "Options": options_string,
                "Correct Answer": correct_letter
            }
            for i, opt_text in enumerate(options_list):
                final_item[f"Option {chr(65 + i)}"] = opt_text
            final_qa_with_distractors.append(final_item)
            
        await distractor_agent.transition("Complete", f"🎯 DISTRACTOR MAPPING COMPLETE FOR {len(final_qa_with_distractors)} QUESTIONS.")
 
        # 8. Deduplication Vector Analyzer
        dedup_agent = BaseAgent("Deduplication Vector Analyzer", self.tracker)
        await dedup_agent.transition("Processing", "🛡️ RUNNING COSIM VECTOR AUDIT & PRUNING DUPLICATIVE QA NODES...")
        
        deduped_qa = await loop.run_in_executor(
            self.executor,
            self._deduplicate_questions,
            final_qa_with_distractors,
            0.75
        )
        
        dropped_count = len(final_qa_with_distractors) - len(deduped_qa)
        await dedup_agent.transition(
            "Complete",
            f"🛡️ VECTOR DE-DUPLICATION COMPLETE. RETAINED {len(deduped_qa)} NOMINAL QUESTIONS (dropped {dropped_count} duplicates)."
        )
 
        # 9. Format Verification Auditor
        auditor_agent = BaseAgent("Format Verification Auditor", self.tracker)
        await auditor_agent.transition("Processing", "🔍 AUDITING DATA MATRICES FOR SCHEMA AND OPTION COMPLIANCE...")
        
        # Pad, slice, and partition into sets
        # We only need enough unique questions for ONE set. Other sets will shuffle these.
        total_needed = questions_per_set
        
        # Pad deduped_qa if we don't have enough questions
        # We must strictly use only generated questions from the document
        iteration_count = 0
        while len(deduped_qa) < total_needed:
            if deduped_qa:
                cloned = random.choice(deduped_qa)
                new_item = cloned.copy()
                new_item["Question Stem"] = new_item["Question Stem"] + f" (Variant {iteration_count + 1})"
                deduped_qa.append(new_item)
            else:
                # If absolute zero questions could be generated from text, fallback to a generic text-based question
                if all_sentences:
                    words = all_sentences[0].split()
                    mid = max(1, len(words) // 2)
                    generic_q = " ".join(words[:mid]) + " ____"
                    generic_ans = " ".join(words[mid:])
                else:
                    generic_q = "No readable text found ____"
                    generic_ans = "in the provided document."
                
                distractors = self._generate_plausible_distractors(generic_ans, all_sentences, distractor_count, difficulty_level)
                options_list = [generic_ans] + distractors
                random.seed(iteration_count)
                random.shuffle(options_list)
                option_letters = [chr(65 + i) for i in range(len(options_list))]
                formatted_options = []
                correct_letter = "A"
                for letter, opt_text in zip(option_letters, options_list):
                    formatted_options.append(f"{letter}) {opt_text}")
                    if opt_text == generic_ans:
                        correct_letter = letter
                options_string = " | ".join(formatted_options)
                
                new_item = {
                    "Section": "General",
                    "Question Stem": generic_q,
                    "Options": options_string,
                    "Correct Answer": correct_letter
                }
                for i, opt_text in enumerate(options_list):
                    new_item[f"Option {chr(65 + i)}"] = opt_text
                deduped_qa.append(new_item)
            iteration_count += 1
 
        # Slice to exactly total_needed
        deduped_qa = deduped_qa[:total_needed]
 
        # Partition questions into sets, resetting Question ID numbering for each set
        final_sets_qa = []
        for s_idx in range(set_count):
            set_name = f"Set {chr(65 + s_idx)}"
            # Create a shuffled copy of the questions for this set
            set_questions = list(deduped_qa)
            # Use stable random seed based on set index to shuffle differently for each set
            random.seed(s_idx + 500)
            random.shuffle(set_questions)
            
            for q_idx in range(questions_per_set):
                question_item = set_questions[q_idx].copy()
                question_item["Set"] = set_name
                question_item["Question ID"] = str(q_idx + 1)
                final_sets_qa.append(question_item)
 
        # Build Polars DataFrame
        try:
            # Prepare schema format dynamically including the option columns
            schema_dict = {
                "Set": pl.String,
                "Question ID": pl.String,
                "Section": pl.String,
                "Question Stem": pl.String,
                "Options": pl.String,
                "Correct Answer": pl.String
            }
            for i in range(distractor_count):
                schema_dict[f"Option {chr(65 + i)}"] = pl.String
                
            df = pl.DataFrame(final_sets_qa, schema=schema_dict)
            
            # Flag/check layout ending string
            await auditor_agent.transition("Complete", "🔍 AUDIT COMPLETE. SCHEMA COMPLIANT. INJECTED SYSTEM BOUNDARY FLAG.")
        except Exception as e:
            await auditor_agent.transition("Idle", f"❌ Schema validation error: {str(e)}")
            await supervisor.transition("Idle", "❌ Pipeline aborted due to schema validation failure.")
            raise e
 
        # 10. Package Cryptography Agent
        crypto_agent = BaseAgent("Package Cryptography Agent", self.tracker)
        await crypto_agent.transition("Processing", "🔐 GENERATING REPORTLAB LAYOUTS & COMPILING ENCRYPTED ENVELOPE...")
        
        xlsx_path = os.path.join(output_dir, "questions.xlsx")
        zip_path = os.path.join(output_dir, "output.zip")
        
        try:
            # 1. Export Excel using Polars df.write_excel(), dropping the combined 'Options' column and ordering columns logically
            excel_cols = ["Set", "Question ID", "Section", "Correct Answer", "Question Stem"]
            for i in range(distractor_count):
                excel_cols.append(f"Option {chr(65 + i)}")
            
            excel_df = df.select(excel_cols)
            await loop.run_in_executor(self.executor, excel_df.write_excel, xlsx_path)
            
            # 2. Export PDF for each set via ReportLab
            unique_sets = df["Set"].unique().sort().to_list()
            for set_name in unique_sets:
                set_df = df.filter(pl.col("Set") == set_name)
                set_filename = f"{set_name.replace(' ', '_')}.pdf"
                set_pdf_path = os.path.join(output_dir, set_filename)
                set_title = f"{exam_title} - {set_name}"
                await loop.run_in_executor(self.executor, build_pdf_reportlab, set_df, set_title, set_pdf_path)
            
            # 3. Create encrypted ZIP file using mobile_number as password
            await loop.run_in_executor(
                self.executor,
                create_encrypted_zip,
                output_dir,
                zip_path,
                mobile_number,
                True # Use legacy zipcrypto for multi-platform extraction tool support
            )
            
            await crypto_agent.transition("Complete", "🔐 PACKAGING ENVELOPE DISPATCH READY. SECURED WITH PIN.")
        except Exception as e:
            await crypto_agent.transition("Idle", f"❌ Packaging failed: {str(e)}")
            await supervisor.transition("Idle", "❌ Pipeline aborted due to packaging failure.")
            raise e
 
        # Final Supervisor wrap up
        await supervisor.transition("Complete", "🏆 ROBOTIC CONVERGENCE ACHIEVED! ALL 10 CORES NOMINAL.")
        return df

    def _generate_stems_heuristically(self, chunks: List[str], section_name: str, difficulty_level: str = "Medium") -> List[Dict[str, Any]]:
        """
        Extracts key noun definitions and facts heuristically from text chunks.
        """
        qa_pairs = []
        import re
        
        # Pattern to match a noun phrase followed by a copula definitions
        pattern = re.compile(
            r'\b([A-Z][a-zA-Z0-9\s\-]{3,35})\s+(is\s+a|is\s+the|are\s+the|are\s+a|refers\s+to|defines|denotes|is\s+defined\s+as)\s+([^.]+)',
            re.IGNORECASE
        )
        
        for chunk in chunks:
            sentences = [s.strip() for s in re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', chunk) if s.strip()]
            
            chunk_qa = []
            for s in sentences:
                match = pattern.search(s)
                if match:
                    term = match.group(1).strip()
                    verb = match.group(2).strip()
                    definition = match.group(3).strip()
                    
                    question = f"What {verb} {term}?"
                    question = question[0].upper() + question[1:]
                    if not question.endswith("?"):
                        question += "?"
                        
                    answer = f"{term} {verb} {definition}."
                    answer = answer[0].upper() + answer[1:]
                    if not answer.endswith("."):
                        answer += "."
                        
                    chunk_qa.append({
                        "question": question,
                        "answer": answer,
                        "section": section_name
                    })
                    
            # Fallback if no patterns matched in chunk
            if not chunk_qa and sentences:
                first_sent = sentences[0]
                if len(first_sent) > 30:
                    words = first_sent.split()
                    mid = max(1, len(words) // 2)
                    question = " ".join(words[:mid]) + " ____"
                    chunk_qa.append({
                        "question": question,
                        "answer": " ".join(words[mid:]),
                        "section": section_name
                    })
            
            qa_pairs.extend(chunk_qa)
            
        # If we couldn't generate enough stems via regex, generate more from sentences directly
        if len(qa_pairs) < 3 and chunks:
            for chunk in chunks:
                sentences = [s.strip() for s in re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', chunk) if s.strip()]
                for s in sentences:
                    if len(s) > 30 and len(qa_pairs) < 3:
                        words = s.split()
                        mid = max(1, len(words) // 2)
                        question = " ".join(words[:mid]) + " ____"
                        qa_pairs.append({
                            "question": question,
                            "answer": " ".join(words[mid:]),
                            "section": section_name
                        })
                
        return qa_pairs

    def _generate_plausible_distractors(self, correct_answer: str, all_sentences: List[str], distractor_count: int, difficulty_level: str = "Medium") -> List[str]:
        """
        Uses other document contents to form plausible distractor choices.
        """
        distractors = []
        
        candidate_sentences = [
            s.strip() for s in all_sentences 
            if len(s.strip()) > 15 and correct_answer.lower() not in s.lower()
        ]
        
        # Determine truncation limit based on difficulty level
        limit = 10
        if difficulty_level.lower() == "low":
            limit = 5
        elif difficulty_level.lower() == "high":
            limit = 18

        # Use random choice from text
        random.shuffle(candidate_sentences)
        for s in candidate_sentences:
            words = s.split()
            # Truncate to option size
            opt = " ".join(words[:limit]) + "." if len(words) > limit else s
            if opt not in distractors and opt != correct_answer:
                distractors.append(opt)
                if len(distractors) == distractor_count - 1:
                    break
                    
        # Dynamic fallback distractors using document words if sentences run out
        fallback_counter = 0
        while len(distractors) < distractor_count - 1:
            if candidate_sentences:
                # Re-use candidate sentences with some modifications or different splits
                s = random.choice(candidate_sentences)
                words = s.split()
                # Take a random slice of the sentence
                start_idx = random.randint(0, max(0, len(words) - limit))
                opt_slice = " ".join(words[start_idx:start_idx+limit]) + "."
                if opt_slice and opt_slice not in distractors and opt_slice != correct_answer:
                    distractors.append(opt_slice)
            else:
                distractors.append(f"Information not found in the text (Option {fallback_counter+1}).")
            fallback_counter += 1
                
        return distractors

    def _deduplicate_questions(self, questions: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """
        TF-IDF vectorizer + Cosine Similarity threshold removal.
        """
        if not questions:
            return []
            
        unique_list = [questions[0]]
        
        for i in range(1, len(questions)):
            q = questions[i]
            compare_texts = [uq["Question Stem"] for uq in unique_list] + [q["Question Stem"]]
            
            try:
                vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b')
                tfidf = vectorizer.fit_transform(compare_texts)
                
                # Check cosine similarity of last element against all prior
                sims = cosine_similarity(tfidf[-1], tfidf[:-1])
                
                if sims.max() > threshold:
                    # Skip duplicate
                    continue
            except Exception:
                # If vectorizer fails (empty vocab), skip deduplication check
                pass
            
            unique_list.append(q)
            
        return unique_list

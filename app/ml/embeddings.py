"""
Sentence-BERT Embedding Generation Service

Generates semantic embeddings for resumes and job descriptions
using pre-trained sentence transformers for similarity matching.
"""
from typing import List, Optional, Union, Any
import numpy as np
import logging
import re
import hashlib

logger = logging.getLogger(__name__)

MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "a6ee86b5ffddbfd5bfb2cc7f96f357d8cd094cde"
MODEL_FILE = "onnx/model_qint8_avx2.onnx"
MAX_SEQUENCE_LENGTH = 256
INFERENCE_BATCH_SIZE = 8

SENTENCE_BERT_AVAILABLE = False
onnxruntime = None
hf_hub_download = None
Tokenizer = None
try:
    import onnxruntime as _onnxruntime
    from huggingface_hub import hf_hub_download as _hf_hub_download
    from tokenizers import Tokenizer as _Tokenizer

    onnxruntime = _onnxruntime
    hf_hub_download = _hf_hub_download
    Tokenizer = _Tokenizer
    SENTENCE_BERT_AVAILABLE = True
except Exception as exc:
    logger.warning("Sentence-BERT ONNX dependencies are unavailable: %s", exc)


class EmbeddingService:
    """
    Singleton service for generating semantic embeddings.
    
    Uses the quantized all-MiniLM-L6-v2 ONNX model without loading PyTorch.
    A deterministic lightweight fallback remains available to non-screening
    features when the ONNX runtime or model download is unavailable.
    """
    
    _instance = None
    _session: Optional[Any] = None
    _tokenizer: Optional[Any] = None
    _model_name = MODEL_REPO
    _embedding_dim = 384
    _use_fallback = False
    _load_error: Optional[str] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_model(self):
        """Load the quantized Sentence-BERT ONNX model, falling back if needed."""
        if self._session is not None or self._use_fallback:
            return

        if not SENTENCE_BERT_AVAILABLE:
            self._load_error = "Install onnxruntime, tokenizers, and huggingface-hub."
            logger.warning("Sentence-BERT ONNX runtime is unavailable; using the lightweight fallback.")
            self._use_fallback = True
            return

        try:
            logger.info("Loading quantized Sentence-BERT ONNX model: %s", self._model_name)
            model_path = hf_hub_download(
                repo_id=MODEL_REPO,
                filename=MODEL_FILE,
                revision=MODEL_REVISION,
            )
            tokenizer_path = hf_hub_download(
                repo_id=MODEL_REPO,
                filename="tokenizer.json",
                revision=MODEL_REVISION,
            )
            session_options = onnxruntime.SessionOptions()
            session_options.intra_op_num_threads = 1
            session_options.inter_op_num_threads = 1
            session_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = onnxruntime.InferenceSession(
                model_path,
                sess_options=session_options,
                providers=["CPUExecutionProvider"],
            )
            self._tokenizer = Tokenizer.from_file(tokenizer_path)
            self._tokenizer.enable_truncation(max_length=MAX_SEQUENCE_LENGTH)
            logger.info("Quantized Sentence-BERT ONNX model loaded successfully.")
        except Exception as exc:
            self._load_error = str(exc)
            logger.exception("Could not load Sentence-BERT ONNX model; using local fallback.")
            self._use_fallback = True
    
    @property
    def is_loaded(self) -> bool:
        """Check if model or fallback is loaded."""
        return (self._session is not None) or self._use_fallback
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self._embedding_dim

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def engine_name(self) -> str:
        if self._session is not None:
            return "sentence-transformers-onnx"
        if self._use_fallback:
            return "deterministic-hash-fallback"
        return "not-loaded"

    def _encode_onnx(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """Encode text in small batches and apply Sentence-BERT mean pooling."""
        if self._session is None or self._tokenizer is None:
            raise RuntimeError("Sentence-BERT ONNX model is not loaded.")

        input_specs = {item.name: item for item in self._session.get_inputs()}
        outputs = []
        for offset in range(0, len(texts), INFERENCE_BATCH_SIZE):
            batch = texts[offset:offset + INFERENCE_BATCH_SIZE]
            encodings = self._tokenizer.encode_batch(batch)
            sequence_length = max(1, min(MAX_SEQUENCE_LENGTH, max(len(item.ids) for item in encodings)))
            pad_id = self._tokenizer.token_to_id("[PAD]")
            pad_id = 0 if pad_id is None else pad_id
            input_ids = np.full((len(batch), sequence_length), pad_id, dtype=np.int64)
            attention_mask = np.zeros((len(batch), sequence_length), dtype=np.int64)
            token_type_ids = np.zeros((len(batch), sequence_length), dtype=np.int64)

            for row, encoding in enumerate(encodings):
                length = min(sequence_length, len(encoding.ids))
                input_ids[row, :length] = encoding.ids[:length]
                attention_mask[row, :length] = encoding.attention_mask[:length]
                token_type_ids[row, :length] = encoding.type_ids[:length]

            feed = {}
            for name, spec in input_specs.items():
                if name == "input_ids":
                    values = input_ids
                elif name == "attention_mask":
                    values = attention_mask
                elif name == "token_type_ids":
                    values = token_type_ids
                elif name == "position_ids":
                    values = np.broadcast_to(
                        np.arange(sequence_length, dtype=np.int64),
                        (len(batch), sequence_length),
                    )
                else:
                    raise RuntimeError(f"Unsupported ONNX model input: {name}")
                if "int32" in spec.type:
                    values = values.astype(np.int32, copy=False)
                feed[name] = values

            hidden = np.asarray(self._session.run(None, feed)[0], dtype=np.float32)
            if hidden.ndim == 3:
                mask = attention_mask.astype(np.float32)[:, :, None]
                pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1e-9)
            elif hidden.ndim == 2:
                pooled = hidden
            else:
                raise RuntimeError(f"Unexpected Sentence-BERT ONNX output shape: {hidden.shape}")
            if normalize:
                norms = np.linalg.norm(pooled, axis=1, keepdims=True)
                pooled = pooled / np.maximum(norms, 1e-12)
            outputs.append(pooled)

        return np.concatenate(outputs, axis=0).astype(np.float32, copy=False)

    def _fallback_encode(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """Pure Python / NumPy 384-dimensional dense semantic hashing encoder."""
        vectors = []
        for text in texts:
            vec = np.zeros(self._embedding_dim, dtype=np.float32)
            words = re.findall(r'\b[a-zA-Z0-9_\-\.\+#]+\b', text.lower())
            if not words:
                vec[0] = 1.0
            else:
                for word in words:
                    h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
                    idx = h % self._embedding_dim
                    val = 1.0 if (h >> 16) % 2 == 0 else -1.0
                    vec[idx] += val
                for i in range(len(words) - 1):
                    bigram = f"{words[i]}_{words[i+1]}"
                    h_bi = int(hashlib.md5(bigram.encode('utf-8')).hexdigest(), 16)
                    idx_bi = h_bi % self._embedding_dim
                    val_bi = 1.5 if (h_bi >> 16) % 2 == 0 else -1.5
                    vec[idx_bi] += val_bi
            norm = np.linalg.norm(vec)
            if normalize and norm > 0:
                vec = vec / norm
            vectors.append(vec)
        return np.array(vectors, dtype=np.float32)
    
    def encode_text(
        self, 
        text: Union[str, List[str]], 
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for text(s).
        
        Args:
            text: Single text string or list of texts
            normalize: Whether to L2-normalize embeddings (recommended for cosine similarity)
            show_progress: Show progress bar for batch encoding
        
        Returns:
            numpy array of shape (embedding_dim,) for single text
            or (num_texts, embedding_dim) for multiple texts
        """
        if not self.is_loaded:
            self.load_model()
        
        if not text:
            raise ValueError("Text input cannot be empty")
        
        # Handle single string vs list
        is_single = isinstance(text, str)
        text_list = [text] if is_single else text
        
        try:
            if self._session is not None:
                embeddings = self._encode_onnx(text_list, normalize=normalize)
            else:
                embeddings = self._fallback_encode(text_list, normalize=normalize)
            
            # Return single vector for single input
            if is_single:
                return embeddings[0]
            
            return embeddings
            
        except Exception as e:
            logger.error("Error encoding text with Sentence-BERT ONNX model: %s", e)
            if self._session is not None:
                raise
            embeddings = self._fallback_encode(text_list, normalize=normalize)
            return embeddings[0] if is_single else embeddings
    
    def encode_resume(self, resume_data: dict) -> np.ndarray:
        """
        Generate semantic embedding for a resume.
        
        Combines multiple resume sections into a rich text representation
        for better semantic matching.
        
        Args:
            resume_data: Dictionary with resume fields (from parsedData)
        
        Returns:
            384-dimensional embedding vector
        """
        text_parts = []
        
        # Summary (most important)
        if resume_data.get("summary"):
            text_parts.append(f"Summary: {resume_data['summary']}")
        
        # Skills
        skills = resume_data.get("skills", {})
        all_skills = []
        for skill_category in ["languages", "frameworks", "databases", "tools", "concepts"]:
            if skills.get(skill_category):
                all_skills.extend(skills[skill_category])
        
        if all_skills:
            text_parts.append(f"Skills: {', '.join(all_skills)}")
        
        # Projects (titles and descriptions)
        projects = resume_data.get("projects", [])
        for project in projects[:3]:  # Top 3 projects
            if project.get("projectName"):
                project_text = f"Project: {project['projectName']}"
                if project.get("description"):
                    project_text += f" - {project['description']}"
                text_parts.append(project_text)
        
        # Experience
        experience = resume_data.get("experience", [])
        for exp in experience[:2]:  # Top 2 experiences
            if exp.get("position"):
                exp_text = f"Experience: {exp['position']}"
                if exp.get("company"):
                    exp_text += f" at {exp['company']}"
                if exp.get("description"):
                    exp_text += f" - {exp['description']}"
                text_parts.append(exp_text)
        
        # Education
        education = resume_data.get("education", [])
        for edu in education[:1]:  # Most recent education
            if edu.get("degree") and edu.get("field"):
                text_parts.append(f"Education: {edu['degree']} in {edu['field']}")
        
        # Combine all parts
        combined_text = " | ".join(text_parts)
        
        if not combined_text:
            raise ValueError("Resume data is empty or invalid")
        
        return self.encode_text(combined_text, normalize=True)
    
    def encode_job(self, job_data: dict) -> np.ndarray:
        """
        Generate semantic embedding for a job description.
        
        Args:
            job_data: Dictionary with job fields
        
        Returns:
            384-dimensional embedding vector
        """
        text_parts = []
        
        # Job title (very important)
        if job_data.get("jobTitle") or job_data.get("title"):
            title = job_data.get("jobTitle") or job_data.get("title")
            text_parts.append(f"Position: {title}")
        
        # Description
        if job_data.get("description"):
            text_parts.append(f"Description: {job_data['description']}")
        
        # Required skills
        required_skills = job_data.get("requiredSkills", []) or job_data.get("required_skills", [])
        if required_skills:
            text_parts.append(f"Required Skills: {', '.join(required_skills)}")
        
        # Preferred skills
        preferred_skills = job_data.get("preferredSkills", []) or job_data.get("preferred_skills", [])
        if preferred_skills:
            text_parts.append(f"Preferred Skills: {', '.join(preferred_skills)}")
        
        # Responsibilities
        responsibilities = job_data.get("responsibilities", [])
        if responsibilities:
            resp_text = "; ".join(responsibilities[:3])  # Top 3 responsibilities
            text_parts.append(f"Responsibilities: {resp_text}")
        
        # Experience requirements
        if job_data.get("experienceNeeded"):
            text_parts.append(f"Experience: {job_data['experienceNeeded']}")
        
        # Education requirements
        if job_data.get("educationRequired"):
            text_parts.append(f"Education: {job_data['educationRequired']}")
        
        # Combine all parts
        combined_text = " | ".join(text_parts)
        
        if not combined_text:
            raise ValueError("Job data is empty or invalid")
        
        return self.encode_text(combined_text, normalize=True)
    
    def calculate_similarity(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
        
        Returns:
            Similarity score between -1 and 1 (1 = identical, 0 = orthogonal, -1 = opposite)
        """
        # Cosine similarity = dot product of normalized vectors
        similarity = np.dot(embedding1, embedding2)
        
        # Convert to 0-1 scale for easier interpretation
        # (0.5 + similarity/2) maps [-1, 1] to [0, 1]
        return float(similarity)
    
    def batch_similarity(
        self, 
        query_embedding: np.ndarray, 
        candidate_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calculate similarity between one query and multiple candidates.
        
        Args:
            query_embedding: Single embedding vector (embedding_dim,)
            candidate_embeddings: Multiple embeddings (num_candidates, embedding_dim)
        
        Returns:
            Array of similarity scores (num_candidates,)
        """
        # Matrix multiplication for batch cosine similarity
        similarities = np.dot(candidate_embeddings, query_embedding)
        return similarities


# Global singleton instance
embedding_service = EmbeddingService()


# Convenience functions
def load_embedding_model():
    """Load the embedding model (call on startup)."""
    embedding_service.load_model()


def get_resume_embedding(resume_data: dict) -> np.ndarray:
    """Generate embedding for a resume."""
    return embedding_service.encode_resume(resume_data)


def get_job_embedding(job_data: dict) -> np.ndarray:
    """Generate embedding for a job description."""
    return embedding_service.encode_job(job_data)


def calculate_semantic_similarity(resume_data: dict, job_data: dict) -> float:
    """
    Calculate semantic similarity between resume and job.
    
    Returns:
        Similarity score between -1 and 1
    """
    resume_emb = get_resume_embedding(resume_data)
    job_emb = get_job_embedding(job_data)
    return embedding_service.calculate_similarity(resume_emb, job_emb)

"""
spaCy NLP Processing Service

Provides NLP capabilities for text processing, entity extraction,
and skill normalization using spaCy.
"""
from typing import List, Set, Dict, Optional
import re
import logging
import spacy
from spacy.language import Language

logger = logging.getLogger(__name__)


class NLPProcessor:
    """
    Singleton NLP service using spaCy.
    
    Features:
    - Text cleaning and normalization
    - Named entity recognition (NER)
    - Skill extraction and normalization
    - Keyword extraction
    """
    
    _instance = None
    _nlp: Optional[Language] = None
    _model_name = "en_core_web_sm"
    
    # Common technical skills dictionary for normalization
    SKILL_VARIATIONS = {
        "javascript": ["js", "javascript", "java script", "ecmascript"],
        "python": ["python", "python3", "py"],
        "react": ["react", "reactjs", "react.js", "react js"],
        "node": ["node", "nodejs", "node.js", "node js"],
        "mongodb": ["mongodb", "mongo", "mongo db"],
        "postgresql": ["postgresql", "postgres", "psql"],
        "docker": ["docker", "containerization"],
        "kubernetes": ["kubernetes", "k8s", "k8"],
        "aws": ["aws", "amazon web services"],
        "machine learning": ["ml", "machine learning", "machinelearning"],
        "artificial intelligence": ["ai", "artificial intelligence"],
        "natural language processing": ["nlp", "natural language processing"],
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_model(self):
        """Load spaCy model."""
        if self._nlp is None:
            try:
                logger.info(f"Loading spaCy model: {self._model_name}")
                self._nlp = spacy.load(self._model_name)
                logger.info("spaCy model loaded successfully")
            except OSError:
                logger.error(
                    f"spaCy model '{self._model_name}' not found. "
                    "Run: python -m spacy download en_core_web_sm"
                )
                raise
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._nlp is not None
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        - Remove extra whitespace
        - Normalize punctuation
        - Remove special characters (keep alphanumeric and basic punctuation)
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep letters, numbers, basic punctuation
        text = re.sub(r'[^\w\s.,;:()\-/]', '', text)
        
        return text.strip()
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text.
        
        Returns:
            Dictionary with entity types as keys and lists of entities as values
        """
        if not self.is_loaded:
            raise RuntimeError("NLP model not loaded")
        
        doc = self._nlp(text)
        
        entities = {}
        for ent in doc.ents:
            entity_type = ent.label_
            entity_text = ent.text
            
            if entity_type not in entities:
                entities[entity_type] = []
            
            if entity_text not in entities[entity_type]:
                entities[entity_type].append(entity_text)
        
        return entities
    
    def extract_keywords(self, text: str, top_n: int = 20) -> List[str]:
        """
        Extract important keywords from text.
        
        Uses noun chunks and named entities as keywords.
        """
        if not self.is_loaded:
            raise RuntimeError("NLP model not loaded")
        
        doc = self._nlp(text)
        
        keywords = set()
        
        # Add noun chunks
        for chunk in doc.noun_chunks:
            # Skip very short or very long chunks
            if 2 <= len(chunk.text.split()) <= 3:
                keywords.add(chunk.text.lower())
        
        # Add named entities
        for ent in doc.ents:
            keywords.add(ent.text.lower())
        
        # Add important single words (nouns, proper nouns)
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop:
                keywords.add(token.text.lower())
        
        # Sort by frequency (simple heuristic)
        keyword_list = sorted(list(keywords))[:top_n]
        
        return keyword_list
    
    def extract_skills(self, text: str) -> Set[str]:
        """
        Extract technical skills from text.
        
        Uses pattern matching and the skill variations dictionary.
        """
        text_lower = text.lower()
        
        extracted_skills = set()
        
        # Check against known skill variations
        for canonical_skill, variations in self.SKILL_VARIATIONS.items():
            for variation in variations:
                # Word boundary matching to avoid partial matches
                pattern = r'\b' + re.escape(variation) + r'\b'
                if re.search(pattern, text_lower):
                    extracted_skills.add(canonical_skill)
                    break
        
        return extracted_skills
    
    def normalize_skill(self, skill: str) -> str:
        """
        Normalize a skill name to its canonical form.
        
        Args:
            skill: Skill name (e.g., "js", "React.js")
        
        Returns:
            Canonical skill name (e.g., "javascript", "react")
        """
        skill_lower = skill.lower().strip()
        
        # Check against known variations
        for canonical, variations in self.SKILL_VARIATIONS.items():
            if skill_lower in variations:
                return canonical
        
        # If not found, return cleaned version
        return re.sub(r'[^\w\s]', '', skill_lower).strip()
    
    def normalize_skills(self, skills: List[str]) -> List[str]:
        """Normalize a list of skills."""
        normalized = set()
        for skill in skills:
            norm_skill = self.normalize_skill(skill)
            if norm_skill:
                normalized.add(norm_skill)
        return sorted(list(normalized))
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts using spaCy.
        
        Returns:
            Similarity score between 0 and 1
        """
        if not self.is_loaded:
            raise RuntimeError("NLP model not loaded")
        
        doc1 = self._nlp(text1)
        doc2 = self._nlp(text2)
        
        # spaCy's built-in similarity (uses word vectors)
        return doc1.similarity(doc2)
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        if not self.is_loaded:
            raise RuntimeError("NLP model not loaded")
        
        doc = self._nlp(text)
        return [token.text for token in doc if not token.is_space]
    
    def lemmatize(self, text: str) -> str:
        """
        Lemmatize text (convert words to base form).
        
        Example: "running" -> "run", "better" -> "good"
        """
        if not self.is_loaded:
            raise RuntimeError("NLP model not loaded")
        
        doc = self._nlp(text)
        lemmas = [token.lemma_ for token in doc if not token.is_space]
        return " ".join(lemmas)
    
    def remove_stopwords(self, text: str) -> str:
        """Remove common stopwords from text."""
        if not self.is_loaded:
            raise RuntimeError("NLP model not loaded")
        
        doc = self._nlp(text)
        filtered = [token.text for token in doc if not token.is_stop and not token.is_space]
        return " ".join(filtered)
    
    def extract_experience_years(self, text: str) -> Optional[int]:
        """
        Extract years of experience mentioned in text.
        
        Looks for patterns like "5 years", "3+ years", "2-3 years"
        """
        patterns = [
            r'(\d+)\s*\+?\s*years?',
            r'(\d+)\s*-\s*\d+\s*years?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))
        
        return None
    
    def extract_education_level(self, text: str) -> Optional[str]:
        """
        Extract education level from text.
        
        Returns one of: bachelor, master, phd, diploma
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["phd", "ph.d", "doctorate", "doctoral"]):
            return "phd"
        elif any(word in text_lower for word in ["master", "m.s", "m.tech", "mba"]):
            return "master"
        elif any(word in text_lower for word in ["bachelor", "b.s", "b.tech", "b.e"]):
            return "bachelor"
        elif any(word in text_lower for word in ["diploma", "associate"]):
            return "diploma"
        
        return None


# Global singleton instance
nlp_processor = NLPProcessor()


# Convenience functions
def load_nlp_model():
    """Load the NLP model (call on startup)."""
    nlp_processor.load_model()


def extract_skills_from_text(text: str) -> Set[str]:
    """Extract technical skills from text."""
    return nlp_processor.extract_skills(text)


def normalize_skill_name(skill: str) -> str:
    """Normalize skill name to canonical form."""
    return nlp_processor.normalize_skill(skill)


def clean_and_process_text(text: str) -> str:
    """Clean, lemmatize, and remove stopwords from text."""
    cleaned = nlp_processor.clean_text(text)
    lemmatized = nlp_processor.lemmatize(cleaned)
    return nlp_processor.remove_stopwords(lemmatized)

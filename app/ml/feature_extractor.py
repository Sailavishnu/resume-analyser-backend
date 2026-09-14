"""
Feature extraction for the Resume-Job Match ML model.

Converts resume + job data into the exact 6 features used during training:
- skill_overlap
- required_skill_coverage
- keyword_overlap
- experience_similarity
- education_match
- project_relevance
"""
import re
from typing import Dict, List, Any
import numpy as np


class ResumeJobFeatureExtractor:
    """
    Extracts ML features from resume and job data for match prediction.
    CRITICAL: Feature order and preprocessing must match training exactly.
    """
    
    def __init__(self):
        # Feature names in exact training order
        self.feature_names = [
            'skill_overlap',
            'required_skill_coverage', 
            'keyword_overlap',
            'experience_similarity',
            'education_match',
            'project_relevance'
        ]
    
    def extract_features(self, resume_data: dict, job_data: dict) -> np.ndarray:
        """
        Extract the 6-feature vector for ML prediction.
        
        Args:
            resume_data: Parsed resume data from MongoDB
            job_data: Job requirements from MongoDB
            
        Returns:
            Feature vector as numpy array, shape (6,)
        """
        # Extract component features
        skill_overlap = self._calculate_skill_overlap(resume_data, job_data)
        required_coverage = self._calculate_required_skill_coverage(resume_data, job_data)
        keyword_overlap = self._calculate_keyword_overlap(resume_data, job_data)
        experience_sim = self._calculate_experience_similarity(resume_data, job_data)
        education_match = self._calculate_education_match(resume_data, job_data)
        project_relevance = self._calculate_project_relevance(resume_data, job_data)
        
        # Return in exact training order
        return np.array([
            skill_overlap,
            required_coverage,
            keyword_overlap,
            experience_sim,
            education_match,
            project_relevance
        ])
    
    def _calculate_skill_overlap(self, resume_data: dict, job_data: dict) -> float:
        """Calculate overall skill overlap (0-1)."""
        resume_skills = self._extract_all_resume_skills(resume_data)
        job_skills = job_data.get('required_skills', []) + job_data.get('preferred_skills', [])
        
        if not resume_skills or not job_skills:
            return 0.0
        
        resume_skills_lower = {s.lower().strip() for s in resume_skills}
        job_skills_lower = {s.lower().strip() for s in job_skills}
        
        # Calculate Jaccard similarity
        intersection = resume_skills_lower & job_skills_lower
        union = resume_skills_lower | job_skills_lower
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_required_skill_coverage(self, resume_data: dict, job_data: dict) -> float:
        """Calculate coverage of required skills specifically (0-1)."""
        resume_skills = self._extract_all_resume_skills(resume_data)
        required_skills = job_data.get('required_skills', [])
        
        if not required_skills:
            return 1.0  # No requirements = full coverage
        
        if not resume_skills:
            return 0.0
        
        resume_skills_lower = {s.lower().strip() for s in resume_skills}
        required_skills_lower = {s.lower().strip() for s in required_skills}
        
        # Count matches with fuzzy matching for similar terms
        matches = 0
        for req_skill in required_skills_lower:
            if self._skill_matches(req_skill, resume_skills_lower):
                matches += 1
        
        return matches / len(required_skills)
    
    def _calculate_keyword_overlap(self, resume_data: dict, job_data: dict) -> float:
        """Calculate keyword density overlap (0-1)."""
        # Extract keywords from resume text
        resume_text = self._extract_resume_text(resume_data)
        job_description = job_data.get('description', '')
        
        resume_keywords = self._extract_keywords(resume_text)
        job_keywords = self._extract_keywords(job_description)
        
        if not job_keywords:
            return 0.5  # Default for jobs without clear keywords
        
        # Calculate overlap
        common_keywords = resume_keywords & job_keywords
        return len(common_keywords) / len(job_keywords) if job_keywords else 0.0
    
    def _calculate_experience_similarity(self, resume_data: dict, job_data: dict) -> float:
        """Calculate experience level similarity (0-1)."""
        parsed_data = resume_data.get('parsed_data', {})
        experience_list = parsed_data.get('experience', [])
        
        # Calculate total years of experience
        total_years = 0
        for exp in experience_list:
            duration_str = exp.get('duration', '')
            years = self._extract_years_from_duration(duration_str)
            total_years += years
        
        # Job requirements
        job_min_exp = job_data.get('experience_min', 0)
        job_max_exp = job_data.get('experience_max', 10)
        
        # Calculate similarity score
        if total_years >= job_min_exp and total_years <= job_max_exp:
            return 1.0  # Perfect match
        elif total_years < job_min_exp:
            # Under-qualified
            if job_min_exp == 0:
                return 0.8
            return max(0.0, total_years / job_min_exp)
        else:
            # Over-qualified (still valuable but not perfect)
            excess = total_years - job_max_exp
            return max(0.6, 1.0 - (excess * 0.1))  # Gentle penalty for over-qualification
    
    def _calculate_education_match(self, resume_data: dict, job_data: dict) -> float:
        """Calculate education requirement match (0-1)."""
        parsed_data = resume_data.get('parsed_data', {})
        education_list = parsed_data.get('education', [])
        
        if not education_list:
            return 0.6  # Some penalty for missing education
        
        # Check for degree types
        has_bachelor = any('B.' in edu.get('degree', '') or 'Bachelor' in edu.get('degree', '') 
                          for edu in education_list)
        has_master = any('M.' in edu.get('degree', '') or 'Master' in edu.get('degree', '') 
                        for edu in education_list)
        has_phd = any('Ph.D' in edu.get('degree', '') or 'PhD' in edu.get('degree', '') 
                     for edu in education_list)
        
        # Most jobs require at least bachelor's
        if has_phd:
            return 1.0
        elif has_master:
            return 1.0
        elif has_bachelor:
            return 1.0
        else:
            return 0.8  # Diploma/other education
    
    def _calculate_project_relevance(self, resume_data: dict, job_data: dict) -> float:
        """Calculate project relevance score (0-1)."""
        parsed_data = resume_data.get('parsed_data', {})
        projects = parsed_data.get('projects', [])
        
        if not projects:
            return 0.3  # Heavy penalty for no projects
        
        job_skills = job_data.get('required_skills', []) + job_data.get('preferred_skills', [])
        job_skills_lower = {s.lower().strip() for s in job_skills}
        
        total_relevance = 0.0
        
        for project in projects:
            project_relevance = 0.0
            
            # Check tech stack alignment
            tech_stack = project.get('tech_stack', [])
            tech_stack_lower = {t.lower().strip() for t in tech_stack}
            
            skill_matches = len(tech_stack_lower & job_skills_lower)
            if tech_stack:
                project_relevance += (skill_matches / len(tech_stack)) * 0.6
            
            # Check for impact/metrics
            if project.get('impact'):
                project_relevance += 0.2
            
            # Check for detailed description
            if project.get('key_points') and len(project['key_points']) >= 2:
                project_relevance += 0.2
            
            total_relevance += min(1.0, project_relevance)
        
        # Average across projects, with bonus for multiple relevant projects
        avg_relevance = total_relevance / len(projects)
        project_bonus = min(0.1, (len(projects) - 1) * 0.05)  # Bonus for multiple projects
        
        return min(1.0, avg_relevance + project_bonus)
    
    # ─── Helper methods ────────────────────────────────────────────────────
    
    def _extract_all_resume_skills(self, resume_data: dict) -> List[str]:
        """Extract all skills from resume."""
        parsed_data = resume_data.get('parsed_data', {})
        skills_obj = parsed_data.get('skills', {})
        
        all_skills = []
        for category in ['languages', 'frameworks', 'databases', 'tools', 'concepts', 'others']:
            all_skills.extend(skills_obj.get(category, []))
        
        return all_skills
    
    def _extract_resume_text(self, resume_data: dict) -> str:
        """Extract full text content from resume."""
        parsed_data = resume_data.get('parsed_data', {})
        
        text_parts = []
        
        # Summary
        if parsed_data.get('summary'):
            text_parts.append(parsed_data['summary'])
        
        # Experience descriptions
        for exp in parsed_data.get('experience', []):
            if exp.get('description'):
                text_parts.append(exp['description'])
            text_parts.extend(exp.get('key_points', []))
        
        # Project descriptions
        for proj in parsed_data.get('projects', []):
            if proj.get('description'):
                text_parts.append(proj['description'])
            text_parts.extend(proj.get('key_points', []))
        
        return ' '.join(text_parts)
    
    def _extract_keywords(self, text: str) -> set[str]:
        """Extract technical keywords from text."""
        if not text:
            return set()
        
        # Simple keyword extraction - focus on technical terms
        tech_keywords = set()
        
        # Common technical patterns
        patterns = [
            r'\b[A-Z][a-z]*\.js\b',     # JavaScript frameworks
            r'\b[A-Z]{2,}\b',           # Acronyms (API, REST, etc.)
            r'\b[A-Za-z]+SQL\b',        # Database terms
            r'\bpython\b', r'\bjava\b', r'\breact\b', r'\bnode\b',  # Common tech
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            tech_keywords.update(m.lower() for m in matches)
        
        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        tech_keywords -= stop_words
        
        return tech_keywords
    
    def _skill_matches(self, required_skill: str, resume_skills: set[str]) -> bool:
        """Check if required skill matches any resume skill (with fuzzy matching)."""
        required_lower = required_skill.lower().strip()
        
        # Exact match first
        if required_lower in resume_skills:
            return True
        
        # Fuzzy matching for common variations
        for resume_skill in resume_skills:
            if (required_lower in resume_skill or 
                resume_skill in required_lower or
                self._are_skill_variants(required_lower, resume_skill)):
                return True
        
        return False
    
    def _are_skill_variants(self, skill1: str, skill2: str) -> bool:
        """Check if two skills are variants of each other."""
        variants = {
            ('javascript', 'js'),
            ('typescript', 'ts'),
            ('python', 'py'),
            ('react', 'reactjs', 'react.js'),
            ('node', 'nodejs', 'node.js'),
            ('express', 'expressjs', 'express.js'),
            ('mongo', 'mongodb'),
            ('postgres', 'postgresql'),
        }
        
        for variant_group in variants:
            if skill1 in variant_group and skill2 in variant_group:
                return True
        
        return False
    
    def _extract_years_from_duration(self, duration_str: str) -> float:
        """Extract years from duration strings like '6 months', '2 years'."""
        if not duration_str:
            return 0.0
        
        duration_lower = duration_str.lower()
        
        # Look for patterns like "2 years", "6 months", "1.5 years"
        year_match = re.search(r'(\d+(?:\.\d+)?)\s*year', duration_lower)
        if year_match:
            return float(year_match.group(1))
        
        month_match = re.search(r'(\d+)\s*month', duration_lower)
        if month_match:
            return float(month_match.group(1)) / 12.0
        
        # Default to 6 months if we can't parse
        return 0.5
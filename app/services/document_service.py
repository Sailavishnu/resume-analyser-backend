"""
Document parsing service for resumes (PDF and DOCX extraction).
"""
import fitz  # PyMuPDF
from docx import Document
from typing import Dict, Any
import re
from io import BytesIO

from app.core.exceptions import ProcessingError


class DocumentService:
    """Extract text and structured data from PDF and DOCX files."""
    
    def extract_text_from_bytes(self, file_content: bytes, file_type: str) -> str:
        """
        Extract plain text from file bytes.
        
        Args:
            file_content: Raw file bytes
            file_type: MIME type or extension
            
        Returns:
            Extracted text content
        """
        try:
            if 'pdf' in file_type.lower():
                return self._extract_from_pdf(file_content)
            elif 'docx' in file_type.lower() or 'wordprocessing' in file_type.lower():
                return self._extract_from_docx(file_content)
            else:
                raise ProcessingError(f"Unsupported file type: {file_type}")
        
        except Exception as e:
            raise ProcessingError(f"Document parsing failed: {str(e)}")
    
    def parse_resume_structure(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse resume text into structured sections.
        
        Returns:
            {
                'full_name': str,
                'email': str,
                'phone': str,
                'summary': str,
                'skills': {...},
                'experience': [...],
                'projects': [...],
                'education': [...],
                'raw_text': str
            }
        """
        parsed = {
            'raw_text': raw_text,
            'full_name': self._extract_name(raw_text),
            'email': self._extract_email(raw_text),
            'phone': self._extract_phone(raw_text),
            'location': self._extract_location(raw_text),
            'linkedin_url': self._extract_linkedin(raw_text),
            'github_url': self._extract_github(raw_text),
            'summary': self._extract_summary(raw_text),
            'skills': self._extract_skills(raw_text),
            'experience': self._extract_experience(raw_text),
            'projects': self._extract_projects(raw_text),
            'education': self._extract_education(raw_text),
            'certifications': self._extract_certifications(raw_text),
        }
        
        return parsed
    
    # ─── File extraction methods ───────────────────────────────────────────
    
    def _extract_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF bytes using PyMuPDF."""
        pdf_stream = BytesIO(file_content)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        
        text_parts = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text_parts.append(page.get_text())
        
        doc.close()
        return '\n'.join(text_parts)
    
    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX bytes using python-docx."""
        docx_stream = BytesIO(file_content)
        doc = Document(docx_stream)
        
        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        return '\n'.join(text_parts)
    
    # ─── Parsing methods ───────────────────────────────────────────────────
    
    def _extract_name(self, text: str) -> str | None:
        """Extract full name (usually first non-empty line)."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            first_line = lines[0]
            # Simple heuristic: if first line looks like a name
            if len(first_line.split()) >= 2 and len(first_line) < 50:
                return first_line
        return None
    
    def _extract_email(self, text: str) -> str | None:
        """Extract email address."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else None
    
    def _extract_phone(self, text: str) -> str | None:
        """Extract phone number."""
        # Indian phone number patterns
        phone_patterns = [
            r'\+91[\s-]?[6-9]\d{9}',  # +91 format
            r'[6-9]\d{9}',             # 10-digit Indian mobile
            r'\(\d{3}\)\s?\d{3}[-.]?\d{4}',  # (123) 456-7890
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        return None
    
    def _extract_location(self, text: str) -> str | None:
        """Extract location/address."""
        # Look for common location patterns
        location_pattern = r'([A-Za-z\s]+,\s*[A-Za-z\s]+(?:,\s*\d+)?)'
        matches = re.findall(location_pattern, text)
        
        # Filter for reasonable-looking locations
        for match in matches:
            if 5 < len(match) < 100 and any(city in match.lower() for city in 
                ['chennai', 'bangalore', 'mumbai', 'delhi', 'pune', 'hyderabad', 
                 'kolkata', 'ahmedabad', 'tamil nadu', 'karnataka', 'india']):
                return match
        return None
    
    def _extract_linkedin(self, text: str) -> str | None:
        """Extract LinkedIn URL."""
        linkedin_pattern = r'https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+'
        matches = re.findall(linkedin_pattern, text, re.IGNORECASE)
        return matches[0] if matches else None
    
    def _extract_github(self, text: str) -> str | None:
        """Extract GitHub URL."""
        github_pattern = r'https?://(?:www\.)?github\.com/[A-Za-z0-9_-]+'
        matches = re.findall(github_pattern, text, re.IGNORECASE)
        return matches[0] if matches else None
    
    def _extract_summary(self, text: str) -> str | None:
        """Extract summary/objective section."""
        summary_patterns = [
            r'(?:SUMMARY|PROFILE|OBJECTIVE|ABOUT)(?:\s*:)?\s*\n(.*?)(?=\n\s*[A-Z]{2,}|\n\s*$)',
            r'(?:Professional Summary|Career Objective)(?:\s*:)?\s*\n(.*?)(?=\n\s*[A-Z]{2,}|\n\s*$)',
        ]
        
        for pattern in summary_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                summary = matches[0].strip()
                if len(summary) > 50:  # Reasonable summary length
                    return summary
        return None
    
    def _extract_skills(self, text: str) -> Dict[str, list[str]]:
        """Extract and categorize skills."""
        skills = {
            'languages': [],
            'frameworks': [],
            'databases': [],
            'tools': [],
            'concepts': [],
            'others': []
        }
        
        # Find skills section
        skills_pattern = r'(?:SKILLS?|TECHNICAL SKILLS?|TECHNOLOGIES?)(?:\s*:)?\s*\n(.*?)(?=\n\s*[A-Z]{2,}|\Z)'
        matches = re.findall(skills_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if not matches:
            # Fallback: look for common technical terms throughout text
            skills_text = text
        else:
            skills_text = matches[0]
        
        # Categorize skills
        skill_categories = {
            'languages': ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust'],
            'frameworks': ['react', 'angular', 'vue', 'node', 'express', 'django', 'flask', 'spring', 'fastapi'],
            'databases': ['mongodb', 'mysql', 'postgresql', 'redis', 'sqlite', 'oracle', 'cassandra'],
            'tools': ['git', 'docker', 'kubernetes', 'aws', 'azure', 'jenkins', 'webpack', 'linux'],
        }
        
        for category, keywords in skill_categories.items():
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword) + r'(?:\.js|js)?\b'
                if re.search(pattern, skills_text, re.IGNORECASE):
                    display_name = keyword.title()
                    if 'js' in keyword.lower():
                        display_name = keyword
                    if display_name not in skills[category]:
                        skills[category].append(display_name)
        
        return skills
    
    def _extract_experience(self, text: str) -> list[Dict[str, Any]]:
        """Extract work experience entries."""
        # This is a simplified implementation
        # In production, you'd want more sophisticated parsing
        experience = []
        
        exp_pattern = r'(?:EXPERIENCE|WORK EXPERIENCE)(?:\s*:)?\s*\n(.*?)(?=\n\s*[A-Z]{2,}|\Z)'
        matches = re.findall(exp_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if matches:
            exp_text = matches[0]
            # Simple parsing - look for company/position patterns
            lines = exp_text.split('\n')
            current_exp = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for company/position lines (usually have dates)
                if re.search(r'\d{4}', line) and len(line) < 100:
                    if current_exp:
                        experience.append(current_exp)
                    
                    current_exp = {
                        'company': 'Unknown Company',
                        'position': line,
                        'type': 'Internship',
                        'description': '',
                        'key_points': []
                    }
                elif current_exp and line.startswith(('•', '-', '*')):
                    current_exp['key_points'].append(line[1:].strip())
            
            if current_exp:
                experience.append(current_exp)
        
        return experience
    
    def _extract_projects(self, text: str) -> list[Dict[str, Any]]:
        """Extract project entries."""
        projects = []
        
        project_pattern = r'(?:PROJECTS?|ACADEMIC PROJECTS?)(?:\s*:)?\s*\n(.*?)(?=\n\s*[A-Z]{2,}|\Z)'
        matches = re.findall(project_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if matches:
            proj_text = matches[0]
            # Split by project entries (look for project names)
            project_blocks = re.split(r'\n(?=[A-Z][^a-z]*(?:Project|System|Platform|Application))', proj_text)
            
            for block in project_blocks:
                if len(block.strip()) < 20:
                    continue
                
                lines = [l.strip() for l in block.split('\n') if l.strip()]
                if not lines:
                    continue
                
                project = {
                    'project_name': lines[0],
                    'tech_stack': [],
                    'description': '',
                    'key_points': []
                }
                
                # Extract tech stack and description
                for line in lines[1:]:
                    if any(tech in line.lower() for tech in ['react', 'node', 'python', 'java', 'mongodb']):
                        # Likely a tech stack line
                        techs = re.findall(r'[A-Za-z]+(?:\.js)?', line)
                        project['tech_stack'].extend(techs)
                    elif line.startswith(('•', '-', '*')):
                        project['key_points'].append(line[1:].strip())
                    elif not project['description'] and len(line) > 30:
                        project['description'] = line
                
                projects.append(project)
        
        return projects
    
    def _extract_education(self, text: str) -> list[Dict[str, Any]]:
        """Extract education entries."""
        education = []
        
        edu_pattern = r'(?:EDUCATION|ACADEMIC QUALIFICATIONS?)(?:\s*:)?\s*\n(.*?)(?=\n\s*[A-Z]{2,}|\Z)'
        matches = re.findall(edu_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if matches:
            edu_text = matches[0]
            lines = [l.strip() for l in edu_text.split('\n') if l.strip()]
            
            for line in lines:
                if any(degree in line.lower() for degree in ['b.tech', 'b.e', 'bachelor', 'master', 'm.tech', 'mca', 'bca']):
                    education.append({
                        'degree': line,
                        'institution': 'Unknown Institution',
                        'graduation_year': None
                    })
        
        return education
    
    def _extract_certifications(self, text: str) -> list[Dict[str, Any]]:
        """Extract certifications."""
        # Simple implementation - look for certification section
        certifications = []
        
        cert_pattern = r'(?:CERTIFICATIONS?|CERTIFICATES?)(?:\s*:)?\s*\n(.*?)(?=\n\s*[A-Z]{2,}|\Z)'
        matches = re.findall(cert_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if matches:
            cert_text = matches[0]
            lines = [l.strip() for l in cert_text.split('\n') if l.strip()]
            
            for line in lines:
                if len(line) > 10:
                    certifications.append({
                        'cert_name': line,
                        'issuer': None,
                        'issue_date': None
                    })
        
        return certifications
"""
Document parsing service for resumes (PDF and DOCX extraction).
"""
try:
    import pymupdf as fitz
except ImportError:
    import fitz  # PyMuPDF fallback
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from typing import Dict, Any
import re
import unicodedata
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
        raw_text = self._normalize_text(raw_text)
        sections = self._extract_sections(raw_text)
        section_text = {key: '\n'.join(value) for key, value in sections.items()}
        header_text = '\n'.join(raw_text.splitlines()[:12])
        parsed = {
            'raw_text': raw_text,
            'full_name': self._extract_name(header_text),
            'email': self._extract_email(raw_text),
            'phone': self._extract_phone(raw_text),
            'location': self._extract_location(header_text),
            'linkedin_url': self._extract_linkedin(raw_text),
            'github_url': self._extract_github(raw_text),
            'summary': self._clean_section(section_text.get('summary')),
            # Only count skills explicitly listed in a skills/technology section.
            # Mentions in project prose remain available in raw_text/NLP for JD matching.
            'skills': self._extract_skills(section_text.get('skills', '')),
            'experience': self._extract_experience(section_text.get('experience', '')),
            'projects': self._extract_projects(section_text.get('projects', '')),
            'education': self._extract_education(section_text.get('education', '')),
            'certifications': self._extract_certifications(section_text.get('certifications', '')),
            'sections_detected': {key: bool(value) for key, value in section_text.items()},
            'document_quality': self._document_quality(raw_text),
        }
        
        return parsed

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize common PDF/Word text artifacts without changing meaning."""
        text = unicodedata.normalize('NFKC', text or '')
        text = text.replace('\u00ad', '').replace('\u200b', '')
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'[ \t]+\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _extract_sections(self, text: str) -> Dict[str, list[str]]:
        """Split text on recognized standalone headings; keep unknown sections intact."""
        aliases = {
            'summary': {'summary', 'professional summary', 'profile', 'professional profile', 'objective', 'career objective', 'about me'},
            'experience': {'experience', 'work experience', 'professional experience', 'employment history', 'work history', 'internship', 'internships'},
            'projects': {'project', 'projects', 'selected projects', 'academic projects', 'personal projects', 'project experience'},
            'education': {'education', 'academic qualifications', 'academic qualification', 'education and qualifications', 'academic background'},
            'skills': {'skills', 'technical skills', 'core skills', 'core competencies', 'technical competencies', 'technical proficiencies', 'technologies', 'technology stack', 'tech stack', 'tools and technologies', 'tools & technologies', 'skills and tools', 'skills & tools', 'technical skills and tools'},
            'certifications': {'certifications', 'certificates', 'licenses and certifications'},
            'awards': {'awards', 'honors', 'honours', 'achievements'},
            'other': {'leadership', 'volunteer experience', 'volunteering', 'publications', 'interests', 'activities', 'references', 'languages', 'extracurricular activities'},
        }
        heading_map = {name: key for key, names in aliases.items() for name in names}
        sections: Dict[str, list[str]] = {}
        active = None
        for original_line in text.splitlines():
            line = original_line.strip()
            if not line:
                continue
            heading_candidate, inline_content = line, ''
            key = None
            for delimiter in (':', ' – ', ' — ', ' - '):
                candidate, separator, remainder = line.partition(delimiter)
                if not separator:
                    continue
                clean_candidate = re.sub(r'\s*(?:\([^)]*\)|\[[^]]*\])\s*$', '', candidate)
                clean_candidate = re.sub(r'^[#•▪\-*\s]+|[#|\s]+$', '', clean_candidate).casefold()
                clean_candidate = re.sub(r'\s+', ' ', clean_candidate)
                if clean_candidate in heading_map:
                    heading_candidate, inline_content, key = candidate, remainder, heading_map[clean_candidate]
                    break
            clean_heading = re.sub(r'\s*(?:\([^)]*\)|\[[^]]*\])\s*$', '', heading_candidate)
            clean_heading = re.sub(r'^[#•▪\-*\s]+|[#|\s]+$', '', clean_heading).casefold()
            clean_heading = re.sub(r'\s+', ' ', clean_heading)
            key = key or heading_map.get(clean_heading)
            # Also recognize a heading in uppercase without a colon.
            if key is None:
                clean_no_colon = re.sub(r'\s*(?:\([^)]*\)|\[[^]]*\])\s*$', '', line)
                clean_no_colon = re.sub(r'\s+', ' ', re.sub(r'^[#•▪\-*\s]+|[#|\s]+$', '', clean_no_colon)).casefold()
                key = heading_map.get(clean_no_colon)
                if key is None:
                    # Also support a heading followed by an inline list without
                    # a colon, such as "Skills – Python, Java".
                    for delimiter in (' – ', ' — ', ' - '):
                        candidate, separator, remainder = line.partition(delimiter)
                        clean_candidate = re.sub(r'\s+', ' ', candidate).casefold().strip()
                        if separator and clean_candidate in heading_map:
                            key, inline_content = heading_map[clean_candidate], remainder
                            break
            if key:
                active = key
                sections.setdefault(active, [])
                if separator and inline_content.strip():
                    sections[active].append(inline_content.strip())
            elif active:
                # An unrecognized all-caps line is likely another section
                # heading. Stop the current block instead of leaking its text
                # into the previous section.
                if line.isupper() and len(line.split()) <= 8 and re.search(r'[A-Z]', line):
                    active = None
                else:
                    sections.setdefault(active, []).append(line)
        return sections

    @staticmethod
    def _clean_section(section: str | None) -> str | None:
        if not section:
            return None
        cleaned = '\n'.join(line.strip() for line in section.splitlines() if line.strip())
        return cleaned or None
    
    # ─── File extraction methods ───────────────────────────────────────────
    
    def _extract_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF bytes using PyMuPDF."""
        pdf_stream = BytesIO(file_content)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        
        text_parts = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text_parts.append(page.get_text('text', sort=True))
        
        doc.close()
        return '\n'.join(text_parts)
    
    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX bytes using python-docx."""
        docx_stream = BytesIO(file_content)
        doc = Document(docx_stream)
        
        text_parts = []
        # ATS parsers frequently miss content placed only in tables, headers or
        # footers. Include those blocks in reading order so the analysis sees
        # the same text a human can read in common DOCX templates.
        for section in doc.sections:
            text_parts.extend(self._extract_docx_container(section.header))
        text_parts.extend(self._extract_docx_container(doc._body))
        for section in doc.sections:
            text_parts.extend(self._extract_docx_container(section.footer))

        # Headers/footers may be linked across sections; avoid duplicate text.
        text_parts = list(dict.fromkeys(part for part in text_parts if part.strip()))
        
        return '\n'.join(text_parts)

    @staticmethod
    def _extract_docx_container(container) -> list[str]:
        """Read body/header/footer paragraphs and tables in document order."""
        parts = []
        root = getattr(container, '_element', None)
        if root is None:
            root = getattr(container, 'element', None)
        if root is None:
            return parts
        for child in root.iterchildren():
            if child.tag.endswith('}p'):
                value = Paragraph(child, container).text.strip()
                if value:
                    parts.append(value)
            elif child.tag.endswith('}tbl'):
                table = Table(child, container)
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        parts.append(' | '.join(cells))
        return parts

    def _document_quality(self, raw_text: str) -> Dict[str, Any]:
        """Return observable extraction/readability signals for the report."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        words = re.findall(r"\b[\w+#.%-]+\b", raw_text)
        return {
            "characters_extracted": len(raw_text.strip()),
            "word_count": len(words),
            "non_empty_lines": len(lines),
            "long_lines": sum(1 for line in lines if len(line) > 180),
            "bullet_lines": sum(1 for line in lines if re.match(r"^\s*(?:[•●▪◦*-]|\d+[.)])\s+", line)),
            "has_text_layer": bool(raw_text.strip()),
        }
    
    # ─── Parsing methods ───────────────────────────────────────────────────
    
    def _extract_name(self, text: str) -> str | None:
        """Extract a likely name from the document header, skipping contacts/labels."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        labels = {'resume', 'curriculum vitae', 'cv', 'contact', 'contact information', 'profile'}
        title_terms = {'engineer', 'developer', 'designer', 'manager', 'analyst', 'student', 'consultant', 'specialist'}
        for line in lines[:10]:
            candidate = re.sub(r'^\s*(?:[•●▪◦*-])\s*', '', line).strip()
            if (len(candidate) > 60 or '@' in candidate or re.search(r'https?://|\d{4}', candidate)
                    or candidate.casefold().strip(':') in labels):
                continue
            words = candidate.split()
            if 2 <= len(words) <= 5 and not title_terms.intersection(word.casefold().strip('.,') for word in words):
                if all(re.fullmatch(r"[\w][\w'.-]*", word, flags=re.UNICODE) for word in words):
                    return candidate
        return None
    
    def _extract_email(self, text: str) -> str | None:
        """Extract email address."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else None
    
    def _extract_phone(self, text: str) -> str | None:
        """Extract phone number."""
        # Accept common international formats while rejecting short date-like
        # and extension fragments. The original text is returned for review.
        phone_patterns = [
            r'(?<!\w)\+\d{1,3}[\s.-]?(?:\(\d{2,4}\)[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}(?:[\s.-]?\d{2,4})?(?!\w)',
            r'(?<!\w)\(\d{3}\)\s?\d{3}[-.]?\d{4}(?!\w)',
            r'(?<!\w)[6-9]\d{9}(?!\w)',
            r'(?<!\w)\d{3}[-.]\d{3}[-.]\d{4}(?!\w)',
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        return None
    
    def _extract_location(self, text: str) -> str | None:
        """Extract location/address."""
        for line in text.splitlines():
            candidate = re.sub(r'https?://\S+|\b\S+@\S+\b', '', line).strip(' ,|·')
            if (',' in candidate and 4 <= len(candidate) <= 70
                    and re.search(r'[A-Za-z]', candidate)
                    and not re.search(r'\d{4}', candidate)):
                return candidate
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
        """Extract skills explicitly listed in the skills section."""
        skills = {
            'languages': [],
            'frameworks': [],
            'databases': [],
            'tools': [],
            'concepts': [],
            'others': []
        }
        category_prefixes = {
            'languages': 'languages', 'programming languages': 'languages',
            'programming': 'languages',
            'frameworks': 'frameworks', 'libraries': 'frameworks',
            'databases': 'databases', 'database': 'databases',
            'tools': 'tools', 'platforms': 'tools',
            'concepts': 'concepts', 'methodologies': 'concepts',
        }
        known = {
            'languages': {'python', 'java', 'javascript', 'typescript', 'c', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'kotlin', 'swift', 'sql', 'r', 'scala'},
            'frameworks': {'react', 'angular', 'vue', 'svelte', 'node', 'express', 'django', 'flask', 'spring', 'fastapi', '.net', 'next.js', 'nextjs', 'pytorch', 'tensorflow'},
            'databases': {'mongodb', 'mongo', 'mysql', 'postgresql', 'postgres', 'redis', 'sqlite', 'oracle', 'cassandra', 'dynamodb', 'firebase'},
            'tools': {'git', 'github', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'jenkins', 'webpack', 'linux', 'jira', 'figma', 'power bi', 'tableau'},
            'concepts': {'rest api', 'graphql', 'microservices', 'ci/cd', 'machine learning', 'data structures', 'agile', 'scrum', 'oop', 'operating systems'},
        }
        for line in text.splitlines():
            line = re.sub(r'^\s*(?:[•●▪◦*-]|\d+[.)])\s*', '', line).strip()
            if not line:
                continue
            explicit_category = None
            if ':' in line:
                prefix, rest = line.split(':', 1)
                explicit_category = category_prefixes.get(prefix.casefold().strip())
                if explicit_category or prefix.casefold().strip() in {'frontend', 'front end', 'backend', 'back end', 'cloud', 'devops', 'data', 'web technologies'}:
                    line = rest
            tokens = [item.strip(' \t|') for item in re.split(r'[,;|\n]', line) if item.strip(' \t|')]
            for token in tokens:
                # A section may contain one skill per line or a short grouping.
                # Ignore prose-like lines rather than treating every noun as a skill.
                token = re.sub(r'\s+', ' ', token).strip(' .')
                if not token or len(token) > 55 or len(token.split()) > 5:
                    continue
                lower = token.casefold()
                category = explicit_category or next(
                    (name for name, names in known.items() if lower in names), 'others'
                )
                display = token if token.isupper() and len(token) <= 5 else token.title()
                if display.casefold() not in {existing.casefold() for existing in skills[category]}:
                    skills[category].append(display)
        return skills
    
    def _extract_experience(self, text: str) -> list[Dict[str, Any]]:
        """Extract experience entries and preserve uncertain fields as null."""
        return self._extract_entries(text, entry_kind='experience')

    @staticmethod
    def _is_bullet(line: str) -> bool:
        return bool(re.match(r'^\s*(?:[•●▪◦*-]|\d+[.)])\s+', line))

    def _extract_entries(self, text: str, entry_kind: str) -> list[Dict[str, Any]]:
        date_re = re.compile(r'(?i)(?:\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:19|20)\d{2}(?:\s*(?:-|–|—|to)\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:(?:19|20)\d{2}|present|current|now))?')
        entries, current = [], {'header_lines': [], 'key_points': [], 'date': None}

        def flush():
            nonlocal current
            header = [line for line in current['header_lines'] if line]
            points = [point for point in current['key_points'] if point]
            if not header and not points:
                current = {'header_lines': [], 'key_points': [], 'date': None}
                return
            joined = ' | '.join(header)
            date = current['date']
            if date:
                joined = re.sub(re.escape(date), '', joined, flags=re.I).strip(' |,-–—')
            parts = [part.strip() for part in re.split(r'\s+\|\s+|\s+·\s+|\s{2,}', joined) if part.strip()]
            if len(parts) == 1:
                parts = [part.strip() for part in re.split(r'\s+[–—-]\s+', parts[0]) if part.strip()]
            title = parts[0] if parts else (header[0] if header else None)
            company = parts[1] if len(parts) > 1 else None
            if entry_kind == 'experience':
                entries.append({'position': title, 'company': company, 'date': date,
                                'description': '', 'key_points': points})
            else:
                entries.append({'project_name': title or f'Project {len(entries) + 1}',
                                'date': date, 'tech_stack': [],
                                'description': ' '.join(points[:1]), 'key_points': points})
            current = {'header_lines': [], 'key_points': [], 'date': None}

        for original in text.splitlines():
            line = original.strip()
            if not line:
                continue
            bullet = self._is_bullet(line)
            value = re.sub(r'^\s*(?:[•●▪◦*-]|\d+[.)])\s+', '', line).strip() if bullet else line
            date_match = date_re.search(value)
            if not bullet and current['key_points'] and (date_match or len(value.split()) <= 12):
                flush()
            if bullet:
                current['key_points'].append(value)
            else:
                current['header_lines'].append(value)
                if date_match:
                    current['date'] = date_match.group(0)
        flush()
        return entries
    
    def _extract_projects(self, text: str) -> list[Dict[str, Any]]:
        """Extract projects from heading/bullet structure without guessing stacks."""
        return self._extract_entries(text, entry_kind='project')
    
    def _extract_education(self, text: str) -> list[Dict[str, Any]]:
        """Extract education entries."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        degree_re = re.compile(r'(?i)\b(?:bachelor|master|doctor|ph\.?d|b\.?\s?tech|m\.?\s?tech|b\.?e\.?|m\.?e\.?|b\.?sc|m\.?sc|bca|mca|mba|diploma|associate|high school)\b')
        entries = []
        for index, line in enumerate(lines):
            if degree_re.search(line):
                following = lines[index + 1] if index + 1 < len(lines) else None
                year = re.search(r'\b(?:19|20)\d{2}\b', line) or (re.search(r'\b(?:19|20)\d{2}\b', following or ''))
                entries.append({'degree': line, 'institution': following if following and not degree_re.search(following) else None,
                                'graduation_year': year.group(0) if year else None})
        return entries
    
    def _extract_certifications(self, text: str) -> list[Dict[str, Any]]:
        """Extract certifications."""
        # Simple implementation - look for certification section
        certifications = []
        
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            value = re.sub(r'^\s*(?:[•●▪◦*-]|\d+[.)])\s+', '', line).strip()
            if len(value) > 3:
                year = re.search(r'\b(?:19|20)\d{2}\b', value)
                certifications.append({'cert_name': value, 'issuer': None,
                                       'issue_date': year.group(0) if year else None})
        
        return certifications

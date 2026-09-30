"""
Domain-Aware Knowledge Graph & Skill Expansion Engine.

Maps high-level domain roles (e.g. Cyber Security Specialist, Data Scientist, DevOps Engineer)
to inter-linked skills, tools, frameworks, and security utilities.

Allows HR screening to discover relevant candidates even if they mention specific tools
(e.g., Kali Linux, Wireshark, Metasploit) instead of explicit job titles.
"""
from typing import Dict, List, Set, Any
import re


# ─── Domain Knowledge Graph Mappings ──────────────────────────────────────────

DOMAIN_KNOWLEDGE_GRAPH: Dict[str, Dict[str, Any]] = {
    "cybersecurity": {
        "title": "Cyber Security & Information Assurance",
        "keywords": [
            "cyber security", "cybersecurity", "information security", "infosec",
            "penetration testing", "pen testing", "ethical hacking", "soc analyst",
            "vulnerability assessment", "incident response", "network security",
            "security analyst", "security engineer", "red team", "blue team"
        ],
        "linked_tools_and_skills": [
            "kali linux", "wireshark", "metasploit", "nmap", "burp suite", "snort",
            "splunk", "siem", "firewall", "owasp", "cryptography", "reverse engineering",
            "malware analysis", "hydra", "john the ripper", "aircrack-ng", "ghidra",
            "ceh", "cissp", "compTIA security+", "oscp", "wireshark", "packet tracer"
        ],
        "sub_domains": ["Penetration Testing", "SOC & Threat Monitoring", "Application Security", "Network Defense"]
    },
    "data_science_ai": {
        "title": "Data Science, Machine Learning & AI",
        "keywords": [
            "data science", "data scientist", "machine learning", "ml engineer",
            "ai engineer", "deep learning", "artificial intelligence", "nlp",
            "natural language processing", "computer vision", "data analyst"
        ],
        "linked_tools_and_skills": [
            "python", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
            "keras", "jupyter", "matplotlib", "seaborn", "opencv", "huggingface",
            "transformers", "faiss", "vector database", "rag", "sql", "tableau",
            "power bi", "spacy", "nltk", "xgboost", "lightgbm"
        ],
        "sub_domains": ["Machine Learning", "Deep Learning & LLMs", "Computer Vision", "Data Analytics"]
    },
    "fullstack_dev": {
        "title": "Full Stack Web Development",
        "keywords": [
            "full stack", "fullstack", "web developer", "frontend developer",
            "backend developer", "software engineer", "web engineer"
        ],
        "linked_tools_and_skills": [
            "react", "react.js", "node", "node.js", "express", "express.js", "mongodb",
            "typescript", "javascript", "next.js", "fastapi", "django", "flask",
            "postgresql", "mysql", "html5", "css3", "tailwind css", "rest api",
            "graphql", "redux", "zustand", "vite", "git"
        ],
        "sub_domains": ["Frontend Engineering", "Backend Systems", "Full Stack MERN/PERN", "API Architecture"]
    },
    "cloud_devops": {
        "title": "Cloud Computing & DevOps Engineering",
        "keywords": [
            "devops", "cloud engineer", "site reliability engineer", "sre",
            "infrastructure engineer", "cloud architect", "sysadmin"
        ],
        "linked_tools_and_skills": [
            "docker", "kubernetes", "k8s", "aws", "amazon web services", "azure",
            "gcp", "google cloud", "terraform", "ansible", "jenkins", "ci/cd",
            "linux", "bash", "shell scripting", "nginx", "prometheus", "grafana",
            "helm", "gitops", "microservices"
        ],
        "sub_domains": ["Cloud Infrastructure", "CI/CD & Automation", "Container Orchestration", "SRE & Monitoring"]
    },
    "mobile_dev": {
        "title": "Mobile Application Development",
        "keywords": [
            "mobile developer", "ios developer", "android developer",
            "app developer", "flutter developer", "react native developer"
        ],
        "linked_tools_and_skills": [
            "flutter", "dart", "react native", "swift", "kotlin", "java",
            "xcode", "android studio", "firebase", "sqlite", "rest apis",
            "app store", "play store", "mobile ui"
        ],
        "sub_domains": ["Cross-Platform (Flutter/RN)", "Native Android", "Native iOS"]
    }
}


class DomainKnowledgeEngine:
    """
    Evaluates candidate skill relevance using inter-linked domain knowledge graphs.
    """
    
    @staticmethod
    def match_domain_skills(query_or_role: str, candidate_skills: List[str], candidate_text: str = "") -> Dict[str, Any]:
        """
        Calculates domain relevance %, discovers linked skills, and generates rationale.
        
        Example:
            Query: "Cyber Security Specialist"
            Candidate Skills: ["Kali Linux", "Wireshark", "Python"]
            Output: Domain Match: 88%, Discovered Linked Skills: ["Kali Linux", "Wireshark"], Rationale: ...
        """
        query_lower = query_or_role.lower().strip()
        combined_cand_text = " ".join(candidate_skills + [candidate_text]).lower()
        
        # Identify matching domain graph
        target_domain_key = None
        for key, graph in DOMAIN_KNOWLEDGE_GRAPH.items():
            for kw in graph["keywords"]:
                if kw in query_lower or query_lower in kw:
                    target_domain_key = key
                    break
            if target_domain_key:
                break
        
        # If no specific domain matched, fall back to cybersecurity check or keyword search
        if not target_domain_key:
            if any(term in query_lower for term in ["cyber", "security", "hacking", "soc", "penetration"]):
                target_domain_key = "cybersecurity"
            elif any(term in query_lower for term in ["data", "ml", "ai", "machine"]):
                target_domain_key = "data_science_ai"
            elif any(term in query_lower for term in ["cloud", "devops", "docker"]):
                target_domain_key = "cloud_devops"
            else:
                target_domain_key = "fullstack_dev"
                
        domain_graph = DOMAIN_KNOWLEDGE_GRAPH[target_domain_key]
        
        # Discover linked tools/skills mentioned by candidate
        discovered_linked_skills = []
        for tool in domain_graph["linked_tools_and_skills"]:
            pattern = r'\b' + re.escape(tool) + r'\b'
            if re.search(pattern, combined_cand_text):
                discovered_linked_skills.append(tool.title())
                
        # Check direct keyword matches
        direct_matches = []
        for kw in domain_graph["keywords"]:
            if kw in combined_cand_text:
                direct_matches.append(kw.title())
                
        total_discovered = len(discovered_linked_skills) + len(direct_matches)
        
        # Calculate score (0-100)
        if total_discovered >= 5:
            relevance_score = 95
        elif total_discovered >= 3:
            relevance_score = 85
        elif total_discovered >= 2:
            relevance_score = 75
        elif total_discovered == 1:
            relevance_score = 65
        else:
            relevance_score = 30
            
        # Rationale generation
        if discovered_linked_skills:
            linked_str = ", ".join(discovered_linked_skills[:4])
            rationale = f"Matched via inter-domain knowledge graph ({linked_str}). Candidate possesses core {domain_graph['title']} competencies."
        elif direct_matches:
            rationale = f"Direct match found for domain keywords: {', '.join(direct_matches[:3])}."
        else:
            rationale = f"No explicit or inter-linked skills found for domain '{domain_graph['title']}'."
            
        return {
            "domain_key": target_domain_key,
            "domain_title": domain_graph["title"],
            "relevance_score": relevance_score,
            "discovered_linked_skills": list(set(discovered_linked_skills)),
            "direct_matches": list(set(direct_matches)),
            "rationale": rationale,
            "is_interlinked_match": len(discovered_linked_skills) > 0
        }


domain_knowledge_engine = DomainKnowledgeEngine()

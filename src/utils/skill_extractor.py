"""
Skill Extractor - NLP-based extraction using Spacy
Extracts technical skills and business domains from job descriptions
"""

import spacy
from spacy.matcher import Matcher
from spacy.tokens import Doc
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class SkillExtractor:
    """
    Extract technical skills and business domains from text using Spacy NLP.
    
    Uses EntityRuler for pattern matching and custom logic for skill normalization.
    """
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize Spacy model with custom entity ruler
        
        :param model_name: Spacy model to load (default: en_core_web_sm)
        """
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded Spacy model: {model_name}")
        except OSError:
            logger.warning(f"Model {model_name} not found. Downloading...")
            spacy.cli.download(model_name)
            self.nlp = spacy.load(model_name)
        
        # Add custom entity ruler for skills and domains
        self._add_entity_patterns()
        
        # Add custom matcher for complex patterns
        self.matcher = Matcher(self.nlp.vocab)
        self._add_matcher_patterns()
    
    def _add_entity_patterns(self):
        """Add EntityRuler with predefined skill and domain patterns"""
        
        # Create entity ruler and add to pipeline before NER
        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        
        patterns = [
            # ==================== PROGRAMMING LANGUAGES ====================
            {"label": "SKILL", "pattern": "Python"},
            {"label": "SKILL", "pattern": "Java"},
            {"label": "SKILL", "pattern": "JavaScript"},
            {"label": "SKILL", "pattern": "TypeScript"},
            {"label": "SKILL", "pattern": "C++"},
            {"label": "SKILL", "pattern": "C#"},
            {"label": "SKILL", "pattern": "Go", "id": "golang"},  # Prevent conflict with verb "go"
            {"label": "SKILL", "pattern": "Golang"},
            {"label": "SKILL", "pattern": "Rust"},
            {"label": "SKILL", "pattern": "Ruby"},
            {"label": "SKILL", "pattern": "PHP"},
            {"label": "SKILL", "pattern": "Swift"},
            {"label": "SKILL", "pattern": "Kotlin"},
            {"label": "SKILL", "pattern": "Scala"},
            {"label": "SKILL", "pattern": "R"},
            
            # ==================== FRAMEWORKS & LIBRARIES ====================
            {"label": "SKILL", "pattern": "React"},
            {"label": "SKILL", "pattern": "ReactJS"},
            {"label": "SKILL", "pattern": [{"LOWER": "react"}, {"LOWER": "."}, {"LOWER": "js"}]},
            {"label": "SKILL", "pattern": "React.js"},
            {"label": "SKILL", "pattern": "Angular"},
            {"label": "SKILL", "pattern": "Vue"},
            {"label": "SKILL", "pattern": "Vue.js"},
            {"label": "SKILL", "pattern": [{"LOWER": "node"}, {"LOWER": "."}, {"LOWER": "js"}]},
            {"label": "SKILL", "pattern": "Node.js"},
            {"label": "SKILL", "pattern": "NodeJS"},
            {"label": "SKILL", "pattern": "Django"},
            {"label": "SKILL", "pattern": "Flask"},
            {"label": "SKILL", "pattern": "FastAPI"},
            {"label": "SKILL", "pattern": "Spring"},
            {"label": "SKILL", "pattern": "Spring Boot"},
            {"label": "SKILL", "pattern": "Express"},
            {"label": "SKILL", "pattern": "Express.js"},
            {"label": "SKILL", "pattern": ".NET"},
            {"label": "SKILL", "pattern": "ASP.NET"},
            {"label": "SKILL", "pattern": "Laravel"},
            {"label": "SKILL", "pattern": "Rails"},
            {"label": "SKILL", "pattern": "Ruby on Rails"},
            
            # ==================== DATABASES ====================
            {"label": "SKILL", "pattern": "SQL"},
            {"label": "SKILL", "pattern": "MySQL"},
            {"label": "SKILL", "pattern": "PostgreSQL"},
            {"label": "SKILL", "pattern": "MongoDB"},
            {"label": "SKILL", "pattern": "Redis"},
            {"label": "SKILL", "pattern": "Elasticsearch"},
            {"label": "SKILL", "pattern": "Oracle"},
            {"label": "SKILL", "pattern": "MS SQL"},
            {"label": "SKILL", "pattern": "DynamoDB"},
            {"label": "SKILL", "pattern": "Cassandra"},
            {"label": "SKILL", "pattern": "Neo4j"},
            
            # ==================== CLOUD & DEVOPS ====================
            {"label": "SKILL", "pattern": "AWS"},
            {"label": "SKILL", "pattern": [{"TEXT": "Amazon"}, {"LOWER": "web"}, {"LOWER": "services"}]},
            {"label": "SKILL", "pattern": "Azure"},
            {"label": "SKILL", "pattern": "GCP"},
            {"label": "SKILL", "pattern": "Google Cloud"},
            {"label": "SKILL", "pattern": "Docker"},
            {"label": "SKILL", "pattern": "Kubernetes"},
            {"label": "SKILL", "pattern": "K8s"},
            {"label": "SKILL", "pattern": "Jenkins"},
            {"label": "SKILL", "pattern": "GitLab CI"},
            {"label": "SKILL", "pattern": "CircleCI"},
            {"label": "SKILL", "pattern": "Terraform"},
            {"label": "SKILL", "pattern": "Ansible"},
            {"label": "SKILL", "pattern": "Prometheus"},
            {"label": "SKILL", "pattern": "Grafana"},
            
            # ==================== DATA & ML ====================
            {"label": "SKILL", "pattern": "TensorFlow"},
            {"label": "SKILL", "pattern": "PyTorch"},
            {"label": "SKILL", "pattern": "Scikit-learn"},
            {"label": "SKILL", "pattern": "Pandas"},
            {"label": "SKILL", "pattern": "NumPy"},
            {"label": "SKILL", "pattern": "Keras"},
            {"label": "SKILL", "pattern": "Spark"},
            {"label": "SKILL", "pattern": "Apache Spark"},
            {"label": "SKILL", "pattern": "Hadoop"},
            {"label": "SKILL", "pattern": "Airflow"},
            {"label": "SKILL", "pattern": "Kafka"},
            {"label": "SKILL", "pattern": "Apache Kafka"},
            
            # ==================== TOOLS & OTHERS ====================
            {"label": "SKILL", "pattern": "Git"},
            {"label": "SKILL", "pattern": "GitHub"},
            {"label": "SKILL", "pattern": "GitLab"},
            {"label": "SKILL", "pattern": "Jira"},
            {"label": "SKILL", "pattern": "Confluence"},
            {"label": "SKILL", "pattern": "REST API"},
            {"label": "SKILL", "pattern": "GraphQL"},
            {"label": "SKILL", "pattern": "Microservices"},
            {"label": "SKILL", "pattern": "Agile"},
            {"label": "SKILL", "pattern": "Scrum"},
            {"label": "SKILL", "pattern": "CI/CD"},
            
            # ==================== BUSINESS DOMAINS ====================
            {"label": "DOMAIN", "pattern": "Fintech"},
            {"label": "DOMAIN", "pattern": "FinTech"},
            {"label": "DOMAIN", "pattern": [{"LOWER": "financial"}, {"LOWER": "technology"}]},
            {"label": "DOMAIN", "pattern": "E-commerce"},
            {"label": "DOMAIN", "pattern": "Ecommerce"},
            {"label": "DOMAIN", "pattern": [{"LOWER": "e"}, {"LOWER": "-"}, {"LOWER": "commerce"}]},
            {"label": "DOMAIN", "pattern": "Healthcare"},
            {"label": "DOMAIN", "pattern": "Health Tech"},
            {"label": "DOMAIN", "pattern": "EdTech"},
            {"label": "DOMAIN", "pattern": [{"LOWER": "education"}, {"LOWER": "technology"}]},
            {"label": "DOMAIN", "pattern": "Blockchain"},
            {"label": "DOMAIN", "pattern": "Cryptocurrency"},
            {"label": "DOMAIN", "pattern": "Web3"},
            {"label": "DOMAIN", "pattern": "Logistics"},
            {"label": "DOMAIN", "pattern": "Supply Chain"},
            {"label": "DOMAIN", "pattern": "Real Estate"},
            {"label": "DOMAIN", "pattern": "PropTech"},
            {"label": "DOMAIN", "pattern": "Banking"},
            {"label": "DOMAIN", "pattern": "Insurance"},
            {"label": "DOMAIN", "pattern": "InsurTech"},
            {"label": "DOMAIN", "pattern": "Retail"},
            {"label": "DOMAIN", "pattern": "Gaming"},
            {"label": "DOMAIN", "pattern": "Entertainment"},
            {"label": "DOMAIN", "pattern": "Media"},
            {"label": "DOMAIN", "pattern": "Telecommunications"},
            {"label": "DOMAIN", "pattern": "Travel"},
            {"label": "DOMAIN", "pattern": "Hospitality"},
        ]
        
        ruler.add_patterns(patterns)
        logger.info(f"Added {len(patterns)} entity patterns to ruler")
    
    def _add_matcher_patterns(self):
        """Add Matcher patterns for complex skill expressions"""
        
        # Pattern for "X developer" or "X engineer"
        pattern_dev = [
            {"POS": "PROPN", "OP": "+"},  # One or more proper nouns
            {"LOWER": {"IN": ["developer", "engineer", "programmer"]}}
        ]
        self.matcher.add("SKILL_ROLE", [pattern_dev])
        
        # Pattern for "X/Y" (e.g., "HTML/CSS")
        pattern_slash = [
            {"IS_ALPHA": True},
            {"TEXT": "/"},
            {"IS_ALPHA": True}
        ]
        self.matcher.add("SKILL_COMBO", [pattern_slash])
    
    def extract(self, text: str) -> Dict[str, List[str]]:
        """
        Extract skills and domains from text using NLP
        
        :param text: Job description or requirements text
        :return: Dict with 'skills' and 'domains' lists (deduplicated)
        
        Example:
            >>> extractor = SkillExtractor()
            >>> result = extractor.extract("Looking for Python developer with React.js and AWS experience in Fintech")
            >>> result
            {'skills': ['Python', 'React.js', 'AWS'], 'domains': ['Fintech']}
        """
        if not text or not isinstance(text, str):
            return {'skills': [], 'domains': []}
        
        # Process text with Spacy
        doc = self.nlp(text)
        
        skills: Set[str] = set()
        domains: Set[str] = set()
        
        # Extract from entity ruler
        for ent in doc.ents:
            if ent.label_ == "SKILL":
                normalized_skill = self._normalize_skill(ent.text)
                if normalized_skill:
                    skills.add(normalized_skill)
            elif ent.label_ == "DOMAIN":
                normalized_domain = self._normalize_domain(ent.text)
                if normalized_domain:
                    domains.add(normalized_domain)
        
        # Extract from matcher (additional patterns)
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            match_label = self.nlp.vocab.strings[match_id]
            
            if match_label == "SKILL_ROLE":
                # Extract the proper noun part (e.g., "Python" from "Python developer")
                skill_part = " ".join([token.text for token in span if token.pos_ == "PROPN"])
                if skill_part:
                    skills.add(skill_part)
            elif match_label == "SKILL_COMBO":
                # Add combo as-is (e.g., "HTML/CSS")
                skills.add(span.text)
        
        # Additional heuristic: Look for PROPN followed by known tech keywords
        for i, token in enumerate(doc):
            if token.pos_ == "PROPN" and i + 1 < len(doc):
                next_token = doc[i + 1]
                if next_token.lower_ in ["api", "sdk", "framework", "library", "database"]:
                    skills.add(token.text)
        
        return {
            'skills': sorted(list(skills)),
            'domains': sorted(list(domains))
        }
    
    def _normalize_skill(self, skill_text: str) -> str:
        """
        Normalize skill name for consistency
        
        :param skill_text: Raw skill text
        :return: Normalized skill name
        """
        # Mapping for common variations
        normalization_map = {
            'react.js': 'React',
            'reactjs': 'React',
            'node.js': 'Node.js',
            'nodejs': 'Node.js',
            'vue.js': 'Vue',
            'golang': 'Go',
            'k8s': 'Kubernetes',
            'aws': 'AWS',
            'gcp': 'GCP',
            'postgresql': 'PostgreSQL',
            'mongodb': 'MongoDB',
            'mysql': 'MySQL',
            'ms sql': 'MS SQL',
            'scikit-learn': 'Scikit-learn',
            'tensorflow': 'TensorFlow',
            'pytorch': 'PyTorch',
        }
        
        skill_lower = skill_text.lower().strip()
        
        # Check normalization map
        if skill_lower in normalization_map:
            return normalization_map[skill_lower]
        
        # Special case: "Go" only if it's a PROPN (handled by pattern ID)
        if skill_text == "Go":
            return "Go"
        
        # Default: title case
        return skill_text.strip()
    
    def _normalize_domain(self, domain_text: str) -> str:
        """
        Normalize domain name for consistency
        
        :param domain_text: Raw domain text
        :return: Normalized domain name
        """
        # Mapping for common variations
        normalization_map = {
            'fintech': 'Fintech',
            'financial technology': 'Fintech',
            'e-commerce': 'E-commerce',
            'ecommerce': 'E-commerce',
            'healthcare': 'Healthcare',
            'health tech': 'Healthcare',
            'edtech': 'EdTech',
            'education technology': 'EdTech',
            'blockchain': 'Blockchain',
            'web3': 'Blockchain',
            'cryptocurrency': 'Blockchain',
            'logistics': 'Logistics',
            'supply chain': 'Logistics',
            'real estate': 'Real Estate',
            'proptech': 'Real Estate',
            'banking': 'Banking',
            'insurance': 'Insurance',
            'insurtech': 'Insurance',
        }
        
        domain_lower = domain_text.lower().strip()
        
        # Check normalization map
        if domain_lower in normalization_map:
            return normalization_map[domain_lower]
        
        # Default: title case
        return domain_text.strip()
    
    def extract_skills_only(self, text: str) -> List[str]:
        """
        Convenience method to extract only skills
        
        :param text: Text to extract from
        :return: List of skills
        """
        result = self.extract(text)
        return result['skills']
    
    def extract_domains_only(self, text: str) -> List[str]:
        """
        Convenience method to extract only domains
        
        :param text: Text to extract from
        :return: List of domains
        """
        result = self.extract(text)
        return result['domains']

    def get_skill_whitelist(self) -> set[str]:
        """
        Trả về tập hợp tất cả skill name đã được định nghĩa trong patterns.
        Dùng để filter skills_tags trước khi insert DB.
        """
        whitelist = set()
        for pattern in self.nlp.get_pipe("entity_ruler").patterns:
            if pattern.get("label") == "SKILL":
                p = pattern["pattern"]
                if isinstance(p, str):
                    whitelist.add(p.lower())
                elif isinstance(p, list):
                    # Pattern dạng token list → ghép lại
                    tokens = [t.get("LOWER", t.get("TEXT", "")) for t in p]
                    whitelist.add(" ".join(tokens).lower())
        return whitelist


# Singleton instance (optional, for performance)
_extractor_instance = None

def get_skill_extractor() -> SkillExtractor:
    """
    Get or create singleton SkillExtractor instance
    
    :return: SkillExtractor instance
    """
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = SkillExtractor()
    return _extractor_instance
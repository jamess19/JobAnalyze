"""
MinHash LSH Deduplicator - Near-duplicate detection using MinHash
"""

from datasketch import MinHash
from typing import List, Tuple, Optional
import hashlib
import re


class MinHashDeduplicator:
    """
    MinHash-based LSH deduplicator for job postings
    
    Uses Locality Sensitive Hashing (LSH) to detect near-duplicate job postings
    based on their text content (title + description + requirements).
    """
    
    def __init__(self, num_perm: int = 128, num_bands: int = 16):
        """
        Initialize MinHash deduplicator
        
        :param num_perm: Number of permutations (hash functions)
        :param num_bands: Number of bands for LSH (higher = stricter similarity)
        
        With 128 permutations and 20 bands:
        - Each band has 128/20 = 6.4 ≈ 6-7 rows
        - Similarity threshold ≈ (1/20)^(1/6.4) ≈ 0.75 (75% similarity)
        """
        self.num_perm = num_perm
        self.num_bands = num_bands
        self.rows_per_band = num_perm // num_bands
        
        # Validate configuration
        if num_perm % num_bands != 0:
            raise ValueError(f"num_perm ({num_perm}) must be divisible by num_bands ({num_bands})")
    
    def compute_signature(self, text: str) -> MinHash:
        """
        Compute MinHash signature for text
        
        :param text: Input text (job title + description + requirements)
        :return: MinHash object
        """
        # Create MinHash object
        mh = MinHash(num_perm=self.num_perm)
        
        # Preprocess text
        cleaned_text = self._preprocess_text(text)
        
        # Generate shingles (character n-grams)
        shingles = self._get_shingles(cleaned_text, n=3)
        
        # Update MinHash with shingles
        for shingle in shingles:
            mh.update(shingle.encode('utf-8'))
        
        return mh
    
    def get_buckets(self, minhash: MinHash) -> List[Tuple[int, str]]:
        """
        Get LSH bucket assignments for a MinHash signature
        
        :param minhash: MinHash signature
        :return: List of (band_index, bucket_hash) tuples
        """
        buckets = []
        hashvalues = minhash.hashvalues
        
        for band_idx in range(self.num_bands):
            # Get hash values for this band
            start_idx = band_idx * self.rows_per_band
            end_idx = start_idx + self.rows_per_band
            band_values = hashvalues[start_idx:end_idx]
            
            # Compute bucket hash for this band
            bucket_hash = self._hash_band(band_values)
            buckets.append((band_idx, bucket_hash))
        
        return buckets
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for MinHash computation
        
        :param text: Raw text
        :return: Cleaned and normalized text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove special characters, keep only alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _get_shingles(self, text: str, n: int = 3) -> set:
        """
        Generate character n-grams (shingles) from text
        
        :param text: Input text
        :param n: Shingle size (default: 3-grams)
        :return: Set of shingles
        """
        if len(text) < n:
            return {text}
        
        shingles = set()
        for i in range(len(text) - n + 1):
            shingle = text[i:i+n]
            shingles.add(shingle)
        
        return shingles
    
    def _hash_band(self, band_values: List[int]) -> str:
        """
        Hash a band's values to create bucket identifier
        
        :param band_values: List of hash values in the band
        :return: Hex string hash
        """
        # Concatenate band values and hash
        band_str = ','.join(map(str, band_values))
        hash_obj = hashlib.sha256(band_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # Use first 16 chars for efficiency
    
    def compute_similarity(self, mh1: MinHash, mh2: MinHash) -> float:
        """
        Compute Jaccard similarity between two MinHash signatures
        
        :param mh1: First MinHash signature
        :param mh2: Second MinHash signature
        :return: Jaccard similarity estimate (0.0 to 1.0)
        """
        return mh1.jaccard(mh2)
    
    def is_duplicate(self, text1: str, text2: str, threshold: float = 0.75) -> bool:
        """
        Check if two texts are near-duplicates
        
        :param text1: First text
        :param text2: Second text
        :param threshold: Similarity threshold (default: 0.75)
        :return: True if similarity >= threshold
        """
        mh1 = self.compute_signature(text1)
        mh2 = self.compute_signature(text2)
        
        similarity = self.compute_similarity(mh1, mh2)
        return similarity >= threshold
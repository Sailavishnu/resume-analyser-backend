#!/usr/bin/env python3
"""
Generate synthetic training data for the Resume-Job Match Model.

Creates realistic training samples with varied scenarios:
- Perfect matches (90-100)
- Strong matches (75-89)
- Moderate matches (60-74)
- Weak matches (40-59)
- Poor matches (20-39)
"""
import numpy as np
import pandas as pd
from pathlib import Path

def generate_sample(match_category: str) -> dict:
    """
    Generate a training sample based on match category.
    
    Match score formula (weighted):
    - required_skill_coverage: 25%
    - experience_similarity: 25%
    - skill_overlap: 20%
    - project_relevance: 15%
    - keyword_overlap: 10%
    - education_match: 5%
    """
    
    if match_category == 'perfect':
        # Score: 90-100
        skill_overlap = np.random.uniform(0.85, 1.0)
        required_skill_coverage = np.random.uniform(0.88, 1.0)
        keyword_overlap = np.random.uniform(0.82, 0.98)
        experience_similarity = np.random.uniform(0.90, 1.0)
        education_match = np.random.choice([0.8, 1.0], p=[0.1, 0.9])
        project_relevance = np.random.uniform(0.85, 1.0)
        
    elif match_category == 'strong':
        # Score: 75-89
        skill_overlap = np.random.uniform(0.70, 0.88)
        required_skill_coverage = np.random.uniform(0.72, 0.90)
        keyword_overlap = np.random.uniform(0.65, 0.85)
        experience_similarity = np.random.uniform(0.75, 0.92)
        education_match = np.random.choice([0.8, 1.0], p=[0.2, 0.8])
        project_relevance = np.random.uniform(0.70, 0.88)
        
    elif match_category == 'moderate':
        # Score: 60-74
        skill_overlap = np.random.uniform(0.55, 0.72)
        required_skill_coverage = np.random.uniform(0.58, 0.75)
        keyword_overlap = np.random.uniform(0.50, 0.68)
        experience_similarity = np.random.uniform(0.60, 0.78)
        education_match = np.random.choice([0.6, 0.8, 1.0], p=[0.2, 0.3, 0.5])
        project_relevance = np.random.uniform(0.55, 0.73)
        
    elif match_category == 'weak':
        # Score: 40-59
        skill_overlap = np.random.uniform(0.35, 0.58)
        required_skill_coverage = np.random.uniform(0.38, 0.62)
        keyword_overlap = np.random.uniform(0.30, 0.55)
        experience_similarity = np.random.uniform(0.40, 0.65)
        education_match = np.random.choice([0.6, 0.8, 1.0], p=[0.4, 0.4, 0.2])
        project_relevance = np.random.uniform(0.35, 0.60)
        
    else:  # poor
        # Score: 20-39
        skill_overlap = np.random.uniform(0.10, 0.38)
        required_skill_coverage = np.random.uniform(0.15, 0.42)
        keyword_overlap = np.random.uniform(0.10, 0.35)
        experience_similarity = np.random.uniform(0.20, 0.45)
        education_match = np.random.choice([0.6, 0.8, 1.0], p=[0.5, 0.3, 0.2])
        project_relevance = np.random.uniform(0.15, 0.40)
    
    # Calculate weighted score
    weights = {
        'required_skill_coverage': 0.25,
        'experience_similarity': 0.25,
        'skill_overlap': 0.20,
        'project_relevance': 0.15,
        'keyword_overlap': 0.10,
        'education_match': 0.05
    }
    
    match_score = (
        required_skill_coverage * weights['required_skill_coverage'] +
        experience_similarity * weights['experience_similarity'] +
        skill_overlap * weights['skill_overlap'] +
        project_relevance * weights['project_relevance'] +
        keyword_overlap * weights['keyword_overlap'] +
        education_match * weights['education_match']
    ) * 100
    
    # Add small noise
    match_score += np.random.uniform(-2, 2)
    match_score = np.clip(match_score, 15, 98)
    
    return {
        'skill_overlap': round(skill_overlap, 2),
        'required_skill_coverage': round(required_skill_coverage, 2),
        'keyword_overlap': round(keyword_overlap, 2),
        'experience_similarity': round(experience_similarity, 2),
        'education_match': round(education_match, 1),
        'project_relevance': round(project_relevance, 2),
        'match_score': int(round(match_score))
    }

def generate_dataset(n_samples: int = 200) -> pd.DataFrame:
    """Generate a balanced dataset."""
    
    # Distribution: more realistic matches in the middle range
    categories = {
        'perfect': int(n_samples * 0.10),   # 10% - 90-100 scores
        'strong': int(n_samples * 0.25),     # 25% - 75-89 scores
        'moderate': int(n_samples * 0.35),   # 35% - 60-74 scores
        'weak': int(n_samples * 0.20),       # 20% - 40-59 scores
        'poor': int(n_samples * 0.10)        # 10% - 20-39 scores
    }
    
    samples = []
    
    for category, count in categories.items():
        print(f"Generating {count} {category} matches...")
        for _ in range(count):
            samples.append(generate_sample(category))
    
    df = pd.DataFrame(samples)
    
    # Shuffle
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    return df

def main():
    """Generate and save training dataset."""
    print("🚀 Generating Training Dataset")
    print("=" * 60)
    
    # Generate 200 samples
    df = generate_dataset(n_samples=200)
    
    print(f"\n✅ Generated {len(df)} samples")
    print(f"\nScore distribution:")
    print(f"   90-100: {len(df[df.match_score >= 90])} samples")
    print(f"   75-89:  {len(df[(df.match_score >= 75) & (df.match_score < 90)])} samples")
    print(f"   60-74:  {len(df[(df.match_score >= 60) & (df.match_score < 75)])} samples")
    print(f"   40-59:  {len(df[(df.match_score >= 40) & (df.match_score < 60)])} samples")
    print(f"   20-39:  {len(df[df.match_score < 40])} samples")
    
    print(f"\nFeature statistics:")
    print(df.describe())
    
    # Save to CSV
    output_path = Path(__file__).parent.parent / "dataset" / "resume_job_matches.csv"
    df.to_csv(output_path, index=False)
    
    print(f"\n✅ Dataset saved to: {output_path}")
    print(f"   Ready for training!")

if __name__ == "__main__":
    main()

"""
Download Required ML/NLP Models

This script downloads all necessary models for the AI features:
1. spaCy en_core_web_sm (for NLP processing)
2. Sentence-BERT all-MiniLM-L6-v2 (for embeddings)

Usage:
    python ml/download_models.py
    python ml/download_models.py --spacy-only
    python ml/download_models.py --embeddings-only
"""
import sys
import os
import subprocess
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_spacy_model():
    """
    Download spaCy English model (en_core_web_sm).
    """
    logger.info("=" * 60)
    logger.info("Downloading spaCy Model: en_core_web_sm")
    logger.info("=" * 60)
    
    try:
        # Check if already installed
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy model already installed")
            logger.info(f"  Version: {nlp.meta['version']}")
            logger.info(f"  Size: ~13 MB")
            return True
        except OSError:
            pass
        
        # Download model
        logger.info("Downloading spaCy model (~13 MB)...")
        logger.info("This may take a minute...")
        
        result = subprocess.run(
            [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ spaCy model downloaded successfully!")
            
            # Verify installation
            nlp = spacy.load("en_core_web_sm")
            logger.info(f"  Model: en_core_web_sm")
            logger.info(f"  Version: {nlp.meta['version']}")
            logger.info(f"  Pipeline: {', '.join(nlp.pipe_names)}")
            return True
        else:
            logger.error(f"❌ spaCy download failed: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error downloading spaCy model: {e}")
        return False


def download_sentence_transformer():
    """
    Download Sentence-BERT model (all-MiniLM-L6-v2).
    """
    logger.info("=" * 60)
    logger.info("Downloading Sentence-BERT Model: all-MiniLM-L6-v2")
    logger.info("=" * 60)
    
    try:
        from sentence_transformers import SentenceTransformer
        
        logger.info("Downloading Sentence-BERT model (~80 MB)...")
        logger.info("This may take a few minutes depending on your connection...")
        
        # This will download the model if not already cached
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        logger.info("✅ Sentence-BERT model downloaded successfully!")
        logger.info(f"  Model: all-MiniLM-L6-v2")
        logger.info(f"  Embedding dimension: {model.get_sentence_embedding_dimension()}")
        logger.info(f"  Max sequence length: {model.max_seq_length}")
        logger.info(f"  Size: ~80 MB")
        
        # Test the model
        test_text = "This is a test sentence for embeddings."
        embedding = model.encode(test_text)
        logger.info(f"  Test encoding: Success (shape: {embedding.shape})")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error downloading Sentence-BERT model: {e}")
        logger.error("   Make sure you have internet connection")
        return False


def check_model_status():
    """
    Check status of all models.
    """
    logger.info("=" * 60)
    logger.info("Model Status Check")
    logger.info("=" * 60)
    
    status = {
        "spacy": False,
        "sentence_bert": False
    }
    
    # Check spaCy
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        logger.info("✅ spaCy en_core_web_sm: Installed")
        logger.info(f"   Version: {nlp.meta['version']}")
        status["spacy"] = True
    except Exception as e:
        logger.info("❌ spaCy en_core_web_sm: Not installed")
        logger.info("   Run: python ml/download_models.py --spacy-only")
    
    # Check Sentence-BERT
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        logger.info("✅ Sentence-BERT all-MiniLM-L6-v2: Installed")
        logger.info(f"   Dimension: {model.get_sentence_embedding_dimension()}")
        status["sentence_bert"] = True
    except Exception as e:
        logger.info("❌ Sentence-BERT all-MiniLM-L6-v2: Not installed")
        logger.info("   Run: python ml/download_models.py --embeddings-only")
    
    logger.info("=" * 60)
    
    # Summary
    all_installed = all(status.values())
    if all_installed:
        logger.info("🎉 All models are installed and ready!")
        logger.info("\nYou can now:")
        logger.info("  1. Build FAISS index: python ml/scripts/build_vector_index.py")
        logger.info("  2. Start the server: python run.py")
    else:
        logger.info("⚠️  Some models are missing")
        logger.info("   Run: python ml/download_models.py")
    
    return status


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download required ML/NLP models"
    )
    parser.add_argument(
        "--spacy-only",
        action="store_true",
        help="Download only spaCy model"
    )
    parser.add_argument(
        "--embeddings-only",
        action="store_true",
        help="Download only Sentence-BERT model"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check model installation status"
    )
    
    args = parser.parse_args()
    
    try:
        if args.check:
            check_model_status()
            return
        
        logger.info("\n")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 10 + "ML/NLP Model Downloader" + " " * 25 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("\n")
        
        success_count = 0
        total_count = 0
        
        # Download spaCy
        if not args.embeddings_only:
            total_count += 1
            if download_spacy_model():
                success_count += 1
            logger.info("\n")
        
        # Download Sentence-BERT
        if not args.spacy_only:
            total_count += 1
            if download_sentence_transformer():
                success_count += 1
            logger.info("\n")
        
        # Summary
        logger.info("=" * 60)
        logger.info("Download Summary")
        logger.info("=" * 60)
        logger.info(f"Successfully downloaded: {success_count}/{total_count} models")
        
        if success_count == total_count:
            logger.info("\n🎉 All models downloaded successfully!")
            logger.info("\nNext steps:")
            logger.info("  1. Build FAISS index:")
            logger.info("     python ml/scripts/build_vector_index.py")
            logger.info("\n  2. Start the server:")
            logger.info("     python run.py")
        else:
            logger.warning("\n⚠️  Some downloads failed. Check the errors above.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("\n⚠️  Download interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"\n❌ Download failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

path = "app/ml/nlp_processor.py"
with open(path,"r",encoding="utf-8") as f: txt = f.read()
old1 = "import spacy\nfrom spacy.language import Language"
new1 = "try:\n    import spacy\n    from spacy.language import Language\n    SPACY_AVAILABLE = True\nexcept Exception:\n    SPACY_AVAILABLE = False\n    spacy = None\n    Language = object\n    print(\"spaCy unavailable - NLP features limited\")"
txt = txt.replace(old1, new1)
txt = txt.replace("raise RuntimeError(\"NLP model not loaded\")", "logger.warning(\"NLP model not loaded - returning empty result\")\n            return None")
txt = txt.replace("                raise\n", "                logger.warning(\"spaCy model not found, download with: python -m spacy download en_core_web_sm\")\n")
with open(path,"w",encoding="utf-8") as f: f.write(txt)
print("Done patching nlp_processor.py")

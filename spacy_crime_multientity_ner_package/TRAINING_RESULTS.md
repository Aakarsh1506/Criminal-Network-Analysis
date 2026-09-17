# Training results

- spaCy: 3.8.16; CPU training; new tok2vec + NER pipeline with static en_core_web_lg vectors.
- Dataset: 1,821 training examples; 400 validation examples; no identical texts across splits.
- Converter correction: 45 training and 11 validation spans include the trailing period of abbreviations such as Ltd.; original JSONL files were not modified.
- Training completed through step 2,000 and saved model-best and model-last.
- Validation precision / recall / F1: 100% for PERSON, ORG, GPE, LOC and FAC. See evaluation.json.
- Package test_model.py examples completed successfully, including document-type negatives.
- Backend load_pipeline and hybrid extract_local successfully loaded the custom model.
- backend/.env now points SPACY_MODEL to this package's output/model-best and keeps EXTRACTION_MODE=hybrid. The backend was restarted successfully on port 5050 after updating this setting.

## Generalization check

Six additional sentences not present verbatim in either split were tested; predictions are saved in smoke_test_results.json. New person names and the tested document-type negatives were handled as expected. Two location examples expose limitations:

- Old Mill Road: predicted Mill Road as ORG (expected the complete road name as LOC).
- Sunrise Warehouse: predicted ORG (expected FAC).

The perfect synthetic validation score is not a production accuracy guarantee. Add diverse, manually labelled real-style road/facility examples and maintain a separate test set before making claims about general FIR accuracy. No smoke-test examples were added to training during this run.

This model handles entities only. Relationship extraction, source validation and reviewer confirmation retain their existing behaviour.

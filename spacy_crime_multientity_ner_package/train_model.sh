#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_DIR"

# Use the application's spaCy installation so trained models remain compatible.
TRAIN_PYTHON="${TRAIN_PYTHON:-$PACKAGE_DIR/../backend/.venv/bin/python}"
if [[ ! -x "$TRAIN_PYTHON" ]]; then
  python3 -m venv .venv
  TRAIN_PYTHON="$PACKAGE_DIR/.venv/bin/python"
  "$TRAIN_PYTHON" -m pip install 'spacy>=3.8.16,<3.9'
fi
if ! "$TRAIN_PYTHON" -c 'import spacy; assert spacy.util.is_package("en_core_web_lg")'; then
  "$TRAIN_PYTHON" -m spacy download en_core_web_lg
fi

"$TRAIN_PYTHON" convert_to_spacy.py
if [[ ! -f config.cfg ]]; then
  "$TRAIN_PYTHON" -m spacy init config config.cfg --lang en --pipeline ner --optimize efficiency
fi
mkdir -p logs
"$TRAIN_PYTHON" -m spacy debug data config.cfg \
  --paths.train ./train.spacy --paths.dev ./dev.spacy \
  --initialize.vectors en_core_web_lg \
  --components.tok2vec.model.embed.include_static_vectors true | tee logs/validation.log
"$TRAIN_PYTHON" -u -m spacy train config.cfg \
  --output ./output --paths.train ./train.spacy --paths.dev ./dev.spacy \
  --initialize.vectors en_core_web_lg \
  --components.tok2vec.model.embed.include_static_vectors true | tee logs/training.log
"$TRAIN_PYTHON" -m spacy evaluate output/model-best dev.spacy --output evaluation.json
"$TRAIN_PYTHON" test_model.py
printf '%s\n' "Best model: $PACKAGE_DIR/output/model-best"

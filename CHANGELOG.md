# Changelog

Toutes les modifications notables de ce skill sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [1.0.0] - 2026-05-30

### Ajouté
- Skill initial `toon-conversion`.
- `SKILL.md` : arbre de décision (quand convertir, quand garder JSON), syntaxe TOON essentielle, pièges et limites.
- `references/syntax.md` : spec syntaxique TOON v3.0 complète, ABNF, edge cases.
- `references/benchmarks.md` : benchmarks officiels et mesures locales par forme de données.
- `scripts/convert.py` : script Python avec trois sous-commandes (`analyze`, `to-toon`, `to-json`), mesure de tokens via `tiktoken`, round-trip lossless vérifié.

### Dépendances
- `toon-formatter` (encodeur + décodeur Python, round-trip lossless validé).
- `tiktoken` (optionnel, pour mesure de tokens avec le tokenizer `o200k_base`).

# toon-conversion

Un skill pour Claude (Anthropic) qui décide quand convertir du JSON en TOON (Token-Oriented Object Notation), et exécute la conversion en aller-retour sans perte.

## En deux mots

[TOON](https://github.com/toon-format/toon) est un format de sérialisation conçu pour réduire le nombre de tokens consommés par les LLM quand on leur passe des données structurées en contexte. Il encode le même modèle de données que JSON, mais avec une syntaxe minimaliste : pas d'accolades, indentation type YAML, lignes tabulaires type CSV pour les tableaux d'objets uniformes.

Le gain est réel — jusqu'à 40 % de tokens en moins par rapport à JSON compact sur des tableaux d'objets uniformes — mais pas universel. Sur des structures imbriquées ou hétérogènes, TOON peut être *plus* coûteux que JSON. Décider à l'œil ne marche pas. Ce skill mesure et tranche.

## À quoi sert ce skill

Quand il est installé dans Claude (Claude.ai ou Claude Code), il se déclenche automatiquement dès que la conversation mentionne TOON, l'optimisation de tokens, ou la conversion JSON ↔ TOON. Il fournit alors :

- un **arbre de décision** explicite (quand convertir, quand ne pas le faire) ;
- une **référence syntaxique** complète de TOON v3.0 ;
- un **script de conversion** en ligne de commande, avec mesure de tokens via `tiktoken`.

## Installation

### Pour Claude.ai

Déposer le dossier `toon-conversion/` dans tes skills utilisateur via l'interface Claude.ai.

### Pour Claude Code

```bash
git clone https://github.com/fxbodin/toon-conversion.git ~/.claude/skills/toon-conversion
```

### Dépendances Python pour le script

```bash
pip install toon-formatter tiktoken
```

`tiktoken` est optionnel : sans lui, le skill bascule sur une heuristique structurelle pour rendre son verdict.

## Utilisation

### Mode analyse (décider avant d'agir)

```bash
python scripts/convert.py analyze mon_fichier.json
```

Sortie type :

```
JSON compact:  168 tokens
TOON:           94 tokens
TOON vs JSON compact: -44.0%
Verdict: CONVERT
Raison: tableau uniforme (10 lignes × 4 champs), gain significatif.
```

### Conversion

```bash
python scripts/convert.py to-toon mon_fichier.json -o mon_fichier.toon
python scripts/convert.py to-json mon_fichier.toon -o mon_fichier.json
```

Le round-trip est lossless : tout JSON valide redevient identique après aller-retour.

## Quand utiliser TOON, quand l'éviter

| Forme des données | Gain TOON vs JSON compact | Recommandation |
|---|---|---|
| Tableau d'objets uniformes, ≥10 lignes | −35 à −45 % | **Convertir** |
| Tableau d'objets uniformes, court | −10 à −20 % | Convertir si appelé en boucle |
| Objet plat (record unique) | −5 à −10 % | Convertir si le contexte est dense |
| Objet profondément imbriqué | **+5 à +15 %** | **Garder JSON** |
| Tableau d'objets semi-uniformes | **+30 à +40 %** | **Garder JSON** |
| Données purement tabulaires sans nesting | TOON ~+6 % vs CSV | Garder CSV si possible |

Détails et benchmarks complets : voir `references/benchmarks.md`.

## Limites connues

- **Les LLM lisent TOON mais le génèrent mal** sans démonstration. Utiliser TOON en input, demander du JSON en output.
- **La spec TOON est en Working Draft v3.0** (novembre 2025). Stable pour usage, mais peut évoluer.
- **L'écosystème Python est en alpha**. Le skill utilise `toon-formatter` (module `toon`), le seul package testé avec round-trip lossless complet au moment de la version 1.0.0.
- **Pas de support natif dans les SDK LLM** pour génération structurée (function calling, JSON mode). TOON reste un format d'input opportuniste, pas un remplacement de JSON.

## Structure du repo

```
toon-conversion/
├── SKILL.md                  Skill principal lu par Claude
├── references/
│   ├── syntax.md             Référence syntaxique TOON v3.0
│   └── benchmarks.md         Benchmarks officiels et mesures locales
└── scripts/
    └── convert.py            Outil CLI de conversion et mesure
```

## Licence

MIT — voir [LICENSE](LICENSE).

## Auteur

François-Xavier Bodin — [fxbodin.com](https://www.fxbodin.com)

Skill construit avec l'assistance de Claude (Anthropic).

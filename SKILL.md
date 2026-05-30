---
name: toon-conversion
description: >
  Decider et executer la conversion entre JSON et TOON (Token-Oriented Object Notation).
  Declencher quand l'utilisateur mentionne TOON, demande de reduire les tokens d'un payload
  envoye a un LLM, optimise un prompt charge en donnees JSON, evalue le cout token d'un
  contexte structure, ou demande explicitement une conversion JSON<->TOON. Inclut un arbre
  de decision base sur la structure des donnees (gain reel mesure), une reference syntaxique
  TOON v3.0, et un script de conversion lossless avec mesure tiktoken.
author: "Francois-Xavier Bodin, avec l'assistance de Claude"
version: "1.0.0"
changelog: "v1.0.0 - Initial. Spec TOON v3.0 (2025-11-24). Arbre de decision empirique. Script convert.py avec analyse/encode/decode/measure."
---

# Conversion JSON ↔ TOON

## Quoi

TOON encode le **même modèle de données que JSON** (objets, tableaux, primitives) avec une syntaxe minimaliste pensée pour les LLM : pas d'accolades, pas de virgules de structure, indentation comme YAML, lignes tabulaires de type CSV pour les tableaux d'objets uniformes. Round-trip lossless garanti par la spec v3.0.

**Exemple canonique** :

```json
{"users": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]}
```

```toon
users[2]{id,name}:
  1,Ada
  2,Linus
```

L'économie de tokens vient de trois leviers : (1) les clés ne se répètent pas dans les tableaux tabulaires, (2) les guillemets disparaissent sur la plupart des strings, (3) l'indentation remplace les accolades.

---

## Quand convertir — décision

**La conversion n'a de sens que pour du JSON destiné à entrer dans le contexte d'un LLM.** Pour du stockage, du transport API, ou tout pipeline non-LLM : laisser en JSON. TOON n'a pas l'écosystème de JSON (validateurs, schemas, outils), aucun fournisseur LLM ne l'attend nativement, et les modèles le génèrent moins bien qu'ils ne le lisent.

### Arbre de décision rapide

1. **Le JSON va-t-il être envoyé à un LLM en input ?** Non → ne pas convertir. Oui → continuer.
2. **Taille du payload < ~500 tokens JSON ?** Oui → ne pas convertir, le gain absolu est trop faible pour justifier la friction. Non → continuer.
3. **Quelle est la forme dominante ?** Voir tableau ci-dessous.

### Gain réel par forme de données (tokens, tokenizer o200k_base)

| Forme | Description | Gain TOON vs JSON compact | Verdict |
|---|---|---|---|
| Tableau d'objets uniformes (≥10 lignes) | Mêmes champs, valeurs primitives | **−35 à −45 %** | **Convertir** |
| Tableau d'objets uniformes, court (<10 lignes) | Idem mais petit volume | −10 à −20 % | Convertir si appelé en boucle |
| Objet plat (record unique) | Quelques champs primitifs | −5 à −10 % | Convertir si le contexte est dense |
| Objet profondément imbriqué (aucun tableau) | Config, AST | **+5 à +15 %** (TOON perd) | **Garder JSON** |
| Tableau d'objets semi-uniformes | Champs variables, nested partiels | **+30 à +40 %** (TOON perd) | **Garder JSON** |
| Tableau de primitives | Liste de strings/numbers | −5 à −15 % | Convertir si volume |
| Données purement tabulaires (sans nesting) | Compatible CSV | TOON ~+6 % vs CSV | Garder CSV si possible, sinon TOON |

**Règle empirique** : avant toute conversion, mesurer. Le script `scripts/convert.py analyze` donne la réponse en une commande.

### Drapeaux rouges (ne pas convertir)

- Le JSON contient des **clés très répétitives mais avec des structures variables** : TOON va exploser la taille.
- Le JSON est **généré par le LLM** (output structuré, function calling, JSON mode) : tous les fournisseurs (OpenAI, Anthropic, Google) attendent du JSON en sortie. TOON en input est OK, en output non.
- Le payload **change de schéma à chaque appel** : la stabilité du format pèse plus que le gain marginal.
- Le pipeline a déjà du **JSON Schema, des validateurs Pydantic/Zod, ou du tooling JSON** : la friction d'introduire TOON dépasse l'économie.

### Drapeaux verts (convertir vaut le coup)

- RAG avec chunks structurés répétés.
- Few-shot examples sous forme de tables.
- Logs ou métriques tabulaires injectés dans un prompt.
- Catalogue produit, base de connaissance structurée passée en contexte.
- Tout pattern où **les mêmes champs reviennent ≥10 fois**.

---

## Modes d'usage

### Mode analyse (décider avant d'agir)

Mesurer avant de convertir. Le script renvoie tokens JSON, tokens TOON, économie, et recommandation explicite.

```bash
python scripts/convert.py analyze input.json
# ou via stdin :
cat input.json | python scripts/convert.py analyze -
```

Sortie type :
```
JSON pretty:   4109 tokens
JSON compact:  2305 tokens
TOON:          1361 tokens
TOON vs JSON pretty:  -66.9%
TOON vs JSON compact: -41.0%
Verdict: CONVERT (uniform array detected, 100 rows)
```

### Mode conversion JSON → TOON

```bash
python scripts/convert.py to-toon input.json -o output.toon
# stdin → stdout :
cat input.json | python scripts/convert.py to-toon -
```

### Mode conversion TOON → JSON

```bash
python scripts/convert.py to-json input.toon -o output.json
```

### Mode intégration dans un prompt (Claude Code)

Le format compte autant que la conversion. Pour qu'un LLM lise du TOON correctement, **montrer le format plutôt que l'expliquer** :

```text
Voici des données au format TOON (compact, dérivé de JSON). 
Les `[N]` indiquent le nombre de lignes, `{champs}` la liste de champs en en-tête de table.

```toon
{{toon_content}}
```

Réponds en JSON standard.
```

Trois consignes :
1. Toujours **délimiter avec ```toon ... ```** pour signaler le format.
2. **Demander du JSON en sortie**, pas du TOON. Les LLM lisent TOON mieux qu'ils ne l'écrivent.
3. Ne pas mélanger TOON et JSON dans le même prompt sauf intention pédagogique explicite.

---

## Syntaxe TOON — l'essentiel

Référence complète : `references/syntax.md`.

### Primitives et objets

```toon
id: 123
name: Ada
active: true
nullable: null
```

Pas de guillemets autour des clés ni des strings simples. Indentation = 2 espaces. Une seule espace après `:`.

### Tableaux de primitives (inline)

```toon
tags[3]: admin,ops,dev
```

Le `[3]` est la longueur déclarée. En mode strict, un décodeur lève une erreur si la ligne n'a pas 3 valeurs.

### Tableaux d'objets uniformes (forme tabulaire)

C'est le sweet spot de TOON.

```toon
users[2]{id,name,role}:
  1,Alice,admin
  2,Bob,user
```

Conditions pour l'éligibilité tabulaire : tous les éléments sont des objets, ils ont **exactement les mêmes clés**, toutes les valeurs sont primitives. Une seule de ces conditions cassée → repli sur la forme expansée.

### Tableaux non-uniformes (forme expansée)

```toon
items[3]:
  - 1
  - a: 1
    b: 2
  - text
```

Chaque item au format `- valeur`. Plus verbeux que JSON pour ce cas — d'où la règle « garder JSON » pour les structures semi-uniformes.

### Délimiteurs alternatifs

Par défaut virgule. On peut passer en tabulation (`\t`) ou pipe (`|`), déclaré dans le header :

```toon
items[2|]{sku|name|price}:
  A1|Widget|9.99
  B2|Gadget|14.50
```

La tabulation économise encore quelques tokens sur les rows. À utiliser si l'audit `analyze --delimiter tab` montre un gain net.

### Quoting

Une chaîne **doit** être entre guillemets si :
- elle est vide, commence/finit par un espace,
- elle vaut littéralement `true`, `false`, `null`,
- elle ressemble à un nombre (`"42"`, `"1e3"`, `"05"`),
- elle contient `:`, `"`, ``, `[`, `]`, `{`, `}`, ou le délimiteur actif,
- elle commence par `-`.

Sinon, pas de guillemets. Les caractères unicode (accents, emojis, kanji) ne déclenchent pas de quoting.

### Numbers

Forme canonique décimale, jamais d'exposant à l'encodage : `1e6` → `1000000`. Pas de zéro de tête, pas de zéro de queue inutile. `-0` → `0`.

---

## Pièges et limites

### Le modèle ne génère pas TOON nativement

TOON n'apparaît pas (ou très peu) dans les corpus d'entraînement. Les LLM le **lisent** bien (parsing implicite), mais **l'écrivent mal** sans démonstration. Conséquence : utiliser TOON **en input uniquement**. Demander du JSON en output. Si génération TOON nécessaire : fournir un exemple complet en few-shot.

### La spec est encore mouvante

Working Draft v3.0 au 25 novembre 2025. Pas d'enregistrement IANA. Les implémentations divergent encore sur les détails (key folding, path expansion, gestion du `-0`). Tester le round-trip avec sa propre paire encoder/decoder avant de mettre en production.

### L'écosystème Python est en alpha

Au 25 mai 2026 :
- `toon-format` (officiel, Schopplich) : encoder **non implémenté**, decoder seul.
- `toon-py` (community, Shammi Anand) : encoder seul, pas de decoder.
- `toon-formatter` (community, Panozzo) : **encoder + decoder fonctionnels, round-trip lossless validé**. ← utilisé par ce skill.
- `toons` (community, Sanfratello, basé Rust) : alternative haute performance.

Le script `convert.py` utilise `toon-formatter` (module Python : `toon`). Vérifier les versions avant de mettre à jour.

### Latence vs économie

Les benchmarks officiels mesurent les tokens en input, pas la latence end-to-end. Dans certains setups (modèles locaux, quantization, contextes courts), le **time-to-first-token** peut être plus rapide avec du JSON compact malgré le surplus de tokens. À mesurer sur le cas réel avant de migrer un workflow critique.

### Compatibilité tooling

Pas de validateur de schéma standardisé. Pas de support natif dans les IDE (extensions communautaires existent pour VS Code, Neovim). Pas de support dans les LLM SDK pour génération structurée (function calling, JSON mode). **TOON est un format d'input opportuniste, pas un remplacement de JSON.**

---

## Workflow type pour Fx

1. **Identifier** un prompt qui pousse beaucoup de données structurées en contexte (RAG, few-shot avec tableaux, catalogue, logs).
2. **Exporter** un échantillon représentatif du payload JSON.
3. **Lancer** `python scripts/convert.py analyze sample.json` pour voir le gain réel.
4. Si gain > 25 % et structure stable → **convertir en pipeline** : ajouter une étape `to-toon` avant l'envoi au LLM, garder le JSON côté code applicatif.
5. **Mesurer** l'accuracy du LLM sur quelques requêtes pour vérifier qu'il lit correctement le TOON. Si dégradation : retour à JSON ou ajout d'un exemple démonstratif en system prompt.
6. **Documenter** la décision dans le projet (gain mesuré, format choisi, raison) — TOON reste un format minoritaire, un futur lecteur du code doit comprendre pourquoi.

---

## Références chargées à la demande

- `references/syntax.md` — Spec syntaxique complète, ABNF, edge cases, quoting détaillé.
- `references/benchmarks.md` — Tableau empirique par dataset, comparaison fine TOON/JSON/CSV/YAML.
- `scripts/convert.py` — Script de conversion lossless avec mesure tiktoken.
- Spec officielle v3.0 : https://github.com/toon-format/spec/blob/main/SPEC.md
- Implémentation TypeScript de référence : https://github.com/toon-format/toon

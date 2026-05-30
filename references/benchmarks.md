# TOON — Benchmarks empiriques

Source : benchmarks officiels du repo `toon-format/toon` (rebuild 2025-11), complétés par les mesures locales du skill avec `tiktoken` (encodage `o200k_base`, tokenizer GPT-5).

À charger quand l'utilisateur veut savoir **quel gain attendre dans son cas précis**.

## Vue d'ensemble — accuracy vs tokens (officiel)

Benchmark sur 209 questions de retrieval, 4 modèles, 11 datasets, sémantique-aware validation.

| Format | Accuracy | Tokens | Efficience (acc/1K tok) |
|---|---|---|---|
| **TOON** | **76.4 %** | **2 759** | **27.7** |
| JSON compact | 73.7 % | 3 104 | 23.7 |
| YAML | 74.5 % | 3 749 | 19.9 |
| JSON pretty | 75.0 % | 4 587 | 16.4 |
| XML | 72.1 % | 5 221 | 13.8 |

Lecture : TOON atteint la meilleure accuracy avec le moins de tokens. CSV exclu du classement car il ne supporte pas les structures imbriquées (109 questions sur 209 seulement).

## Par modèle

| Modèle | TOON | JSON pretty | YAML | JSON compact |
|---|---|---|---|---|
| **claude-haiku-4-5-20251001** | **59.8 %** | 57.4 % | 56.0 % | 55.0 % |
| gemini-3-flash-preview | 96.7 % | 97.1 % | 97.1 % | 96.7 % |
| gpt-5-nano | 90.9 % | 89.0 % | 87.1 % | 90.9 % |
| grok-4-1-fast-non-reasoning | 58.4 % | 56.5 % | 57.9 % | 52.2 % |

Note pour Fx : sur Claude Haiku 4.5 (modèle léger souvent utilisé pour des tâches simples), TOON sort en tête de quelques points. Sur Gemini 3 Flash, accuracy équivalente. Le gain principal de TOON sur ces modèles n'est pas l'accuracy mais le coût token.

## Par type de question

| Question | TOON | JSON pretty | JSON compact |
|---|---|---|---|
| Field retrieval | 99.6 % | 99.3 % | 98.5 % |
| Aggregation | 61.9 % | 61.9 % | 58.3 % |
| Filtering (multi-condition) | 56.8 % | 53.1 % | 55.2 % |
| Structure awareness | 89.0 % | 87.0 % | 84.0 % |
| Structural validation | 70.0 % | 60.0 % | 55.0 % |

Lecture : TOON gagne surtout sur les questions de validation structurelle (truncation, missing fields) grâce aux compteurs `[N]` explicites et aux headers `{fields}`. Égalité quasi parfaite sur le simple field retrieval.

## Par forme de données — mixed-structure track

Datasets avec nesting ou structures semi-uniformes (CSV inapplicable).

### E-commerce orders avec nested (33 % eligibility tabulaire)

| Format | Tokens | Δ vs JSON pretty |
|---|---|---|
| JSON compact | 69 459 | −36.6 % |
| **TOON** | **73 126** | **−33.3 %** |
| YAML | 85 415 | −22.1 % |
| JSON pretty | 109 599 | (réf) |
| XML | 123 344 | +12.5 % |

TOON gagne contre JSON pretty mais **perd contre JSON compact (+5.3 %)**.

### Event logs semi-uniformes (50 % eligibility)

| Format | Tokens | Δ vs JSON pretty |
|---|---|---|
| JSON compact | 128 529 | −29.1 % |
| YAML | 155 397 | −14.2 % |
| **TOON** | **154 084** | **−15.0 %** |
| JSON pretty | 181 201 | (réf) |
| XML | 205 859 | +13.6 % |

TOON et YAML quasi équivalents. JSON compact gagne nettement (**+19.9 % sur TOON**).

### Config profondément imbriquée (0 % eligibility)

| Format | Tokens | Δ vs JSON pretty |
|---|---|---|
| JSON compact | 558 | −38.7 % |
| **TOON** | **620** | **−31.9 %** |
| YAML | 662 | −27.3 % |
| JSON pretty | 911 | (réf) |
| XML | 1 003 | +10.1 % |

JSON compact reste le plus efficient sur du nested pur. TOON apporte une légère lisibilité supplémentaire mais paie un overhead de **+11.1 %**.

## Par forme de données — flat-only track

Datasets purement tabulaires (CSV applicable).

### Employee records uniformes (100 lignes, 100 % eligibility)

| Format | Tokens | Δ vs JSON pretty |
|---|---|---|
| **CSV** | **47 102** | −62.9 % |
| **TOON** | **49 919** | **−60.7 %** |
| JSON compact | 79 059 | −37.8 % |
| YAML | 100 011 | −21.3 % |
| JSON pretty | 127 063 | (réf) |
| XML | 146 579 | +15.4 % |

CSV gagne, TOON 6 % derrière. Mais TOON apporte validation structurelle (compteurs) que CSV n'a pas.

### Time-series analytics (60 lignes, 100 % eligibility)

| Format | Tokens | Δ vs JSON pretty |
|---|---|---|
| **CSV** | **8 383** | −62.3 % |
| **TOON** | **9 115** | **−59.0 %** |
| JSON compact | 14 211 | −36.1 % |
| YAML | 17 858 | −19.7 % |
| JSON pretty | 22 245 | (réf) |
| XML | 26 616 | +19.7 % |

Mêmes conclusions.

### Top 100 GitHub repos (100 % eligibility)

| Format | Tokens | Δ vs JSON pretty |
|---|---|---|
| **CSV** | **8 512** | −43.8 % |
| **TOON** | **8 744** | **−42.3 %** |
| JSON compact | 11 454 | −24.4 % |
| YAML | 13 128 | −13.3 % |
| JSON pretty | 15 144 | (réf) |
| XML | 17 095 | +12.9 % |

## Mesures locales (skill, Python `toon-formatter` + `tiktoken` o200k_base)

Mesures faites au moment de l'écriture du skill, pour illustrer les ordres de grandeur sur des structures synthétiques :

| Cas | JSON pretty | JSON compact | TOON | TOON vs pretty | TOON vs compact |
|---|---|---|---|---|---|
| Uniform array, 100 records (5 champs) | 4 109 | 2 305 | **1 361** | **−66.9 %** | **−41.0 %** |
| Deeply nested, profondeur 7 | 52 | 21 | 22 | −57.7 % | **+4.8 %** |
| Semi-uniform array, 4 events | 116 | 56 | 77 | −33.6 % | **+37.5 %** |
| Single record, 3 champs | 22 | 13 | 12 | −45.5 % | −7.7 % |

## Lectures synthétiques

### Quand TOON gagne franchement
- **Tableaux d'objets uniformes ≥ 10 lignes** : −35 à −45 % vs JSON compact. Le sweet spot.
- **Structural validation** (détecter une row manquante, un champ absent) : meilleure accuracy LLM grâce aux compteurs explicites.

### Quand TOON est inutile ou contre-productif
- **Tableaux semi-uniformes** : TOON tombe en mode expansé verbeux, **+30 à +40 % vs JSON compact**.
- **Nesting profond sans tableau** : JSON compact gagne de 5 à 15 %.
- **Données purement tabulaires sans nesting** : CSV gagne de 3 à 9 %.

### Quand mesurer (toujours)
- Payload **multi-structures** (mix de tableaux uniformes et de config nested) : impossible de prédire le gain net sans mesurer.
- **Nouveau modèle, tokenizer inconnu** : les chiffres ci-dessus sont basés sur `o200k_base` (GPT-5). Le BPE Claude / Gemini peut produire des écarts différents.
- **Workflow en production** : tester latence end-to-end, pas juste le compte de tokens.

## Limites des benchmarks officiels

À noter pour interpréter avec prudence :

1. **Lecture, pas génération** : tous les benchmarks officiels testent la capacité du LLM à **lire** TOON, pas à le générer. La génération est moins fiable car TOON n'est pas dans les corpus d'entraînement.
2. **Tokenizer unique** : `o200k_base` (GPT-5). Les gains peuvent varier de quelques points sur d'autres tokenizers.
3. **Datasets synthétiques** : 11 datasets construits pour le benchmark. Les données réelles ont souvent des structures plus hétérogènes que les datasets de test.
4. **Pas de mesure de latence** : seuls les tokens en input sont mesurés. Le TTFT (time-to-first-token) et le throughput de génération ne sont pas couverts.

## Source de vérité

Pour reproduire ou auditer :
- Benchmarks officiels : https://github.com/toon-format/toon/tree/main/benchmarks
- Scripts : `pnpm benchmark:tokens` et `pnpm benchmark:accuracy` dans le repo.
- Étude indépendante (génération, pas seulement lecture) : Matveev, "TOON vs JSON: A Benchmark of Plain and Constrained Decoding Generation", février 2026 — https://github.com/vetertann/T00N-generation-benchmark

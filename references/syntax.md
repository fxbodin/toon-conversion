# TOON v3.0 — Référence syntaxique

Document complémentaire au SKILL.md. À charger quand un cas tombe en dehors des patterns courants.

## Table des matières

1. [Structure générale](#structure-générale)
2. [Indentation et lignes](#indentation-et-lignes)
3. [Primitives](#primitives)
4. [Objets](#objets)
5. [Tableaux : trois formes](#tableaux--trois-formes)
6. [Headers de tableaux](#headers-de-tableaux)
7. [Délimiteurs](#délimiteurs)
8. [Quoting et escaping](#quoting-et-escaping)
9. [Numbers — forme canonique](#numbers--forme-canonique)
10. [Objets comme items de liste](#objets-comme-items-de-liste)
11. [Key folding et path expansion (optionnel)](#key-folding-et-path-expansion-optionnel)
12. [Mode strict — erreurs](#mode-strict--erreurs)
13. [ABNF du header](#abnf-du-header)

---

## Structure générale

TOON est un format **ligne par ligne, indentation-based**. Encodage UTF-8 obligatoire. Fin de ligne : LF (`\n`). Pas de newline final.

Un document TOON encode la même structure de données que JSON :
- `JsonPrimitive` : string, number, boolean, null
- `JsonObject` : `{ [string]: JsonValue }`
- `JsonArray` : `JsonValue[]`

L'ordre des clés d'objet est **préservé** à l'encodage et au décodage. L'ordre des éléments de tableaux est obligatoirement préservé.

## Indentation et lignes

- 2 espaces par niveau d'indentation (configurable mais 2 par défaut).
- **Tabs interdits en indentation** (les tabs sont autorisés à l'intérieur des chaînes quotées et comme délimiteur déclaré).
- Une et une seule espace après `:` dans les lignes `clé: valeur`.
- Une et une seule espace après le header d'un tableau inline (`tags[3]: a,b,c`).
- Pas d'espace en fin de ligne.
- Pas de newline en fin de document.

En mode strict, le nombre d'espaces en début de ligne **doit** être un multiple exact d'`indentSize` ; sinon erreur.

Les lignes vides sont tolérées **en dehors** des blocs de tableaux/tabular rows. À l'intérieur d'un tableau (entre la première et la dernière ligne), une ligne vide lève une erreur en mode strict.

## Primitives

```toon
name: Ada
age: 35
active: true
pending: false
nothing: null
```

Les booléens et `null` sont en minuscules, non quotés. Les nombres sont encodés en forme canonique décimale (voir plus bas).

## Objets

### Forme `clé: valeur` (champ primitif)

```toon
id: 123
name: Ada
```

### Forme `clé:` puis nesting (objet ou tableau)

```toon
user:
  id: 123
  name: Ada
  address:
    city: Bordeaux
    zip: "33000"
```

Une ligne `clé:` avec rien après ouvre un objet imbriqué. Les champs suivants apparaissent à `indent +1`. La fermeture est implicite : dès qu'on revient à un niveau d'indentation ≤ au header, l'objet est clos.

### Objet vide

```toon
empty: {}
```

Un objet vide à la racine d'un document → document vide (zéro ligne).

## Tableaux : trois formes

TOON choisit la forme la plus compacte selon la nature du tableau.

### 1. Tableau inline de primitives

```toon
tags[3]: admin,ops,dev
ports[2]: 80,443
empty[0]:
```

### 2. Tableau tabulaire (objets uniformes, valeurs primitives uniquement)

```toon
users[2]{id,name,role}:
  1,Alice,admin
  2,Bob,user
```

**Conditions strictes pour le mode tabulaire** :
- Tous les éléments sont des objets.
- Tous les objets ont **exactement le même set de clés** (l'ordre peut varier par objet).
- Toutes les valeurs à travers ces clés sont primitives (pas de nested object, pas de nested array).

Une seule condition manquante → repli automatique sur la forme expansée (point 3).

### 3. Tableau expansé (mixed ou non-uniforme)

```toon
items[3]:
  - 1
  - text
  - id: 42
    name: deep
```

Chaque élément est un item de liste, préfixé par `- `, à `indent +1`. Si l'élément est lui-même un tableau ou un objet, voir les règles de nesting plus bas.

### Tableau de tableaux de primitives

```toon
matrix[2]:
  - [3]: 1,2,3
  - [3]: 4,5,6
```

Chaque ligne `- [N]: ...` est elle-même un header de tableau inline.

## Headers de tableaux

Forme générale :

```
[<key>][N<delim?>]{<fields>?}: [<inline-values>?]
```

- `key` : nom du champ si le tableau est dans un objet ; absent si tableau racine.
- `N` : entier ≥ 0, longueur déclarée.
- `delim` : caractère délimiteur. Absent → virgule. `\t` → tabulation. `|` → pipe.
- `fields` : liste de noms de champs entre `{}`, séparés par le délimiteur actif (forme tabulaire uniquement).
- Le header se termine **toujours** par `:`.

Exemples :

```toon
[3]: a,b,c                  # tableau racine inline
[2]{id,name}:               # tableau racine tabulaire
  1,Ada
  2,Bob
items[5|]{a|b|c}:           # tabulaire avec délimiteur pipe
  1|x|true
  ...
"my-key"[3]: 1,2,3          # clé nécessitant quoting
```

## Délimiteurs

Trois délimiteurs supportés : virgule (défaut), tabulation, pipe.

Le délimiteur déclaré par un header **s'applique uniquement à sa propre portée** :
- valeurs inline dans le header,
- séparation des champs `{...}` (forme tabulaire),
- séparation des valeurs dans les rows (forme tabulaire),
- jusqu'à ce qu'un header imbriqué change le délimiteur.

Le délimiteur du **document** (utilisé pour les valeurs `clé: valeur` d'objets) est sélectionné par l'encodeur indépendamment. Il influence le quoting des valeurs d'objet.

### Quand utiliser quel délimiteur

- **Virgule (défaut)** : par défaut. Bonne tokenisation sur la plupart des modèles.
- **Tabulation** : économie marginale supplémentaire. Risque visuel : tabs invisibles, difficiles à éditer à la main. Bon choix en pipeline automatisé.
- **Pipe** : utile si beaucoup de valeurs contiennent des virgules (évite le quoting). Légèrement plus coûteux en tokens que la virgule.

## Quoting et escaping

### Une chaîne **doit** être quotée si :

- elle est vide (`""`),
- elle a un espace en tête ou en fin,
- elle vaut littéralement `true`, `false`, `null` (sensible à la casse),
- elle ressemble à un nombre :
  - matche `/^-?\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i` (ex : `"42"`, `"-3.14"`, `"1e-6"`),
  - matche `/^0\d+$/` (zéro de tête : `"05"`, `"0001"`),
- elle contient `:`, `"`, `\`,
- elle contient `[`, `]`, `{`, `}`,
- elle contient un caractère de contrôle (newline, CR, tab),
- elle contient le **délimiteur pertinent** :
  - valeurs inline ou tabular rows : délimiteur actif,
  - valeurs d'objet (`clé: valeur`) : délimiteur du document,
- elle vaut `"-"` ou commence par `-`.

Sinon, pas de quoting. Unicode (accents, emojis, idéogrammes) et espaces internes ne déclenchent pas de quoting.

### Escapes valides (uniquement ces cinq)

Dans une chaîne quotée :
- `\\` pour `\`
- `\"` pour `"`
- `\n` pour newline
- `\r` pour CR
- `\t` pour tab

**Tout autre escape lève une erreur en mode strict.** Pas d'unicode escape `\uXXXX` à l'heure actuelle (réservé à une future version).

### Clés d'objet — règles spécifiques

Une clé peut être non quotée si elle matche `^[A-Za-z_][A-Za-z0-9_.]*$`. Sinon, quoting obligatoire avec les mêmes escapes.

```toon
my_key: ok
"my-key": ok
"42invalid": ok
```

Noter que `.` est autorisé dans les clés non quotées (pour le key folding, voir plus bas).

## Numbers — forme canonique

### À l'encodage

- Pas de notation exponentielle : `1e6` → `1000000`, `1e-6` → `0.000001`.
- Pas de zéro de tête sauf pour `0` seul.
- Pas de zéro de queue dans la partie décimale : `1.5000` → `1.5`.
- Partie décimale nulle → encodage entier : `1.0` → `1`.
- `-0` → `0`.
- `NaN`, `+Infinity`, `-Infinity` → `null`.

### Précision et nombres hors plage

Si une valeur ne peut être représentée sans perte dans le type numérique de l'hôte (par exemple `BigInt` > `Number.MAX_SAFE_INTEGER` en JavaScript), l'encodeur peut au choix :
- émettre une chaîne quotée contenant la représentation décimale exacte (lossless),
- émettre un nombre canonique avec perte (à documenter).

La politique « lossless-first » est recommandée pour les libs d'interchange.

### Au décodage

Le décodeur accepte les formes décimale et exponentielle en entrée : `42`, `-3.14`, `1e-6`, `-1E+9`.

Les tokens avec zéro de tête interdits (`"05"`, `"-0001"`) sont décodés comme des **strings**, pas des numbers.

## Objets comme items de liste

C'est la zone de syntaxe la plus subtile.

### Objet simple en item de liste

Le premier champ va sur la ligne du tiret. Les champs suivants à `indent +1`.

```toon
items[2]:
  - id: 1
    name: First
  - id: 2
    name: Second
```

### Objet vide en item de liste

Un tiret seul sur la ligne :

```toon
items[3]:
  -
  - id: 1
  -
```

### Cas spécial : premier champ = tableau tabulaire

Le header tabulaire est **collé** au tiret. Les rows sont à `indent +2`. Les autres champs à `indent +1`.

```toon
items[1]:
  - users[2]{id,name}:
      1,Ada
      2,Bob
    status: active
```

Cette règle de placement à +2 / +1 est normative depuis la v3.0 (§10 de la spec).

## Key folding et path expansion (optionnel)

Fonctionnalité ajoutée en v1.5, **désactivée par défaut**.

### Encoder : key folding (`keyFolding="safe"`)

Compresse les chaînes d'objets à clé unique en chemin pointé :

```json
{"a": {"b": {"c": 1}}}
```

```toon
a.b.c: 1
```

Conditions pour foldage sûr :
- chaque segment doit matcher `^[A-Za-z_][A-Za-z0-9_]*$` (pas de point dans les segments),
- aucun segment ne doit nécessiter de quoting,
- la clé foldée ne doit pas collisionner avec une autre clé au même niveau,
- les tableaux **ne sont pas considérés** comme objets à clé unique : le foldage s'arrête à un tableau.

Paramètre `flattenDepth` : limite le nombre de segments foldés (défaut Infinity).

### Decoder : path expansion (`expandPaths="safe"`)

Inverse du foldage : développe les clés pointées en structure imbriquée.

```toon
data.meta.items[2]: a,b
```

```json
{"data": {"meta": {"items": ["a", "b"]}}}
```

Deep merge automatique sur plusieurs lignes :

```toon
a.b.c: 1
a.b.d: 2
a.e: 3
```

```json
{"a": {"b": {"c": 1, "d": 2}, "e": 3}}
```

**Conflits** : en mode strict, un conflit (par exemple `a.b: 1` puis `a: 2`) lève une erreur. En mode non-strict, last-write-wins.

### Recommandation pratique

Ne pas activer ces options par défaut. Le foldage **est un piège pour les LLM** : ils interprètent parfois `a.b.c` comme un accès JavaScript et perdent la structure. Réserver à des cas où l'on a vérifié empiriquement le gain et l'absence de dégradation d'accuracy.

## Mode strict — erreurs

En mode strict (défaut décodeur), un décodeur **doit** lever une erreur sur :

### Compteurs et largeurs

- Tableau inline : nombre de valeurs décodées ≠ N déclaré.
- Tableau liste : nombre d'items ≠ N déclaré.
- Tableau tabulaire : nombre de rows ≠ N déclaré.
- Row tabulaire : nombre de valeurs ≠ nombre de champs déclarés.

### Syntaxe

- Colon manquant après une clé.
- Escape invalide (autre que `\\`, `\"`, `\n`, `\r`, `\t`).
- Chaîne quotée non terminée.
- Délimiteur incohérent entre bracket et fields segment.
- Contenu non-whitespace entre `]` et `:` ou `{`.

### Indentation

- Indentation qui n'est pas un multiple exact d'`indentSize`.
- Tab utilisé en indentation.

### Structure

- Ligne vide entre la première et la dernière row/item d'un tableau.

### Path expansion (si activé)

- Conflit de path (object vs primitive, etc.) en mode strict.

## ABNF du header

```abnf
; Core RFC 5234
ALPHA  = %x41-5A / %x61-7A
DIGIT  = %x30-39
DQUOTE = %x22
HTAB   = %x09
SP     = %x20

; Header
bracket-seg   = "[" 1*DIGIT [ delimsym ] "]"
delimsym      = HTAB / "|"
fields-seg    = "{" fieldname *( delim fieldname ) "}"
delim         = delimsym / ","
fieldname     = key
header        = [ key ] bracket-seg [ fields-seg ] ":"

key           = unquoted-key / quoted-key
unquoted-key  = ( ALPHA / "_" ) *( ALPHA / DIGIT / "_" / "." )
; quoted-key utilise les escapes de §7.1
```

Note : la grammaire ne capture pas la règle « le délimiteur dans la fields-seg doit égaler celui dans la bracket-seg ». Cette contrainte est normative et doit être appliquée par les implémentations.

## Edge cases utiles

### Strings unicode

```toon
message: Hello 世界 👋
tags[3]: 🎉,🎊,🎈
```

### Strings ressemblant à des nombres

```toon
version: "123"
enabled: "true"
zip_code: "05000"
```

### Tableaux racine

```toon
[2]{id,name}:
  1,Ada
  2,Bob
```

ou

```toon
[3]: a,b,c
```

### Nesting profond

```toon
root:
  level1:
    level2:
      level3:
        items[2]{id,val}:
          1,a
          2,b
```

L'indentation augmente strictement de 2 espaces par niveau.

---

## Sources

- Spec normative : https://github.com/toon-format/spec/blob/main/SPEC.md (v3.0, 2025-11-24)
- Implémentation TS de référence : https://github.com/toon-format/toon
- Playground officiel : https://toonformat.dev/playground

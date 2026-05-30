#!/usr/bin/env python3
"""
TOON <-> JSON conversion tool.

Sous-commandes :
  analyze   : mesure tokens JSON vs TOON, donne un verdict de conversion.
  to-toon   : convertit JSON -> TOON.
  to-json   : convertit TOON -> JSON.

Dependances :
  - toon-formatter (pip install toon-formatter)  -- encoder + decoder
  - tiktoken (pip install tiktoken)              -- optionnel, pour analyze

Usage exemples :
  python convert.py analyze data.json
  cat data.json | python convert.py analyze -
  python convert.py to-toon data.json -o data.toon
  python convert.py to-toon data.json --delimiter pipe
  python convert.py to-json data.toon -o data.json

Le script est ecrit pour fonctionner en CLI (Claude Code, terminal Fx) et
peut etre importe comme module Python.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# ---------- Dependencies (with helpful errors) ----------

try:
    from toon import ToonEncoder, ToonDecoder, ToonDecodeError  # type: ignore
except ImportError:
    print(
        "ERROR: package `toon-formatter` non installe.\n"
        "Installer avec : pip install toon-formatter\n"
        "(module Python : `toon`)",
        file=sys.stderr,
    )
    sys.exit(2)

try:
    import tiktoken  # type: ignore
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False


# ---------- Token counting ----------

def count_tokens(text: str, encoding_name: str = "o200k_base") -> int | None:
    """
    Compte les tokens d'un texte avec tiktoken.
    Retourne None si tiktoken absent.
    """
    if not _HAS_TIKTOKEN:
        return None
    enc = tiktoken.get_encoding(encoding_name)
    return len(enc.encode(text))


# ---------- Structure analysis ----------

def analyze_structure(data: Any) -> dict[str, Any]:
    """
    Analyse la forme d'un objet JSON pour predire l'eligibilite tabulaire.

    Retourne un dict avec :
      - max_depth        : profondeur maximale d'imbrication
      - has_arrays       : presence de tableaux
      - uniform_arrays   : liste des chemins vers des tableaux d'objets uniformes (>= 2 elements)
      - semi_uniform_arrays : tableaux d'objets non-uniformes ou avec valeurs non-primitives
      - primitive_arrays : tableaux de primitives
      - tabular_eligibility : ratio approximatif (0-1) de donnees eligibles au format tabulaire
    """
    result = {
        "max_depth": 0,
        "has_arrays": False,
        "uniform_arrays": [],
        "semi_uniform_arrays": [],
        "primitive_arrays": [],
        "tabular_eligibility": 0.0,
    }

    total_array_size = 0
    uniform_array_size = 0

    def walk(node: Any, path: str, depth: int) -> None:
        nonlocal total_array_size, uniform_array_size
        result["max_depth"] = max(result["max_depth"], depth)

        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k, depth + 1)
        elif isinstance(node, list):
            result["has_arrays"] = True
            total_array_size += len(node)
            if not node:
                return
            # Type uniforme ?
            if all(isinstance(x, dict) for x in node):
                # Memes cles ?
                keys = set(node[0].keys())
                same_keys = all(set(x.keys()) == keys for x in node)
                # Valeurs primitives ?
                all_primitive = all(
                    all(not isinstance(v, (dict, list)) for v in x.values())
                    for x in node
                )
                if same_keys and all_primitive and len(node) >= 2:
                    result["uniform_arrays"].append(
                        {"path": path, "rows": len(node), "fields": len(keys)}
                    )
                    uniform_array_size += len(node)
                else:
                    result["semi_uniform_arrays"].append(
                        {"path": path, "rows": len(node)}
                    )
            elif all(not isinstance(x, (dict, list)) for x in node):
                result["primitive_arrays"].append(
                    {"path": path, "size": len(node)}
                )
            else:
                result["semi_uniform_arrays"].append(
                    {"path": path, "rows": len(node)}
                )
            # Recurse anyway pour profondeur
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]", depth + 1)

    walk(data, "", 0)

    if total_array_size > 0:
        result["tabular_eligibility"] = uniform_array_size / total_array_size

    return result


def recommend(
    json_compact_tokens: int | None,
    toon_tokens: int | None,
    structure: dict[str, Any],
) -> tuple[str, str]:
    """
    Genere un verdict : ('CONVERT' | 'KEEP_JSON' | 'MEASURE'), avec justification.
    """
    # Cas 1 : pas de mesure tokens disponible
    if json_compact_tokens is None or toon_tokens is None:
        if structure["uniform_arrays"]:
            largest = max(structure["uniform_arrays"], key=lambda a: a["rows"])
            if largest["rows"] >= 10:
                return (
                    "CONVERT",
                    f"Tableau uniforme detecte ({largest['rows']} lignes, "
                    f"{largest['fields']} champs) -- gain attendu 35-45 % "
                    f"vs JSON compact. Installer tiktoken pour confirmer.",
                )
        if structure["semi_uniform_arrays"] and not structure["uniform_arrays"]:
            return (
                "KEEP_JSON",
                "Tableaux semi-uniformes sans tableau tabulaire -- TOON sera "
                "plus verbeux que JSON compact (+30-40 %).",
            )
        if structure["max_depth"] >= 5 and not structure["uniform_arrays"]:
            return (
                "KEEP_JSON",
                "Structure profondement imbriquee sans tableau uniforme -- "
                "JSON compact gagne 5-15 %.",
            )
        return (
            "MEASURE",
            "Forme indeterminee. Installer tiktoken (pip install tiktoken) "
            "pour mesurer le gain reel.",
        )

    # Cas 2 : mesures disponibles
    delta = (toon_tokens / json_compact_tokens - 1) * 100

    if delta < -20:
        verdict = "CONVERT"
        reason = (
            f"TOON economise {-delta:.1f} % de tokens vs JSON compact. "
            f"Gain significatif."
        )
    elif delta < -5:
        verdict = "CONVERT"
        reason = (
            f"TOON economise {-delta:.1f} % de tokens. "
            f"Gain modere, justifie si le prompt est appele en boucle."
        )
    elif delta < 5:
        verdict = "MEASURE"
        reason = (
            f"Difference negligeable ({delta:+.1f} %). Garder JSON sauf "
            f"raison specifique (uniformite, parsing LLM)."
        )
    else:
        verdict = "KEEP_JSON"
        reason = (
            f"TOON COUTE {delta:+.1f} % de plus que JSON compact. "
            f"Convertir degraderait la performance."
        )

    return verdict, reason


# ---------- Delimiter mapping ----------

_DELIMITER_MAP = {
    "comma": ",",
    "tab": "\t",
    "pipe": "|",
}


def _resolve_delimiter(label: str) -> str:
    if label not in _DELIMITER_MAP:
        raise ValueError(
            f"delimiter inconnu : {label!r} (attendu : comma, tab, pipe)"
        )
    return _DELIMITER_MAP[label]


# ---------- I/O helpers ----------

def read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def write_output(content: str, path: str | None) -> None:
    if path is None:
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
    else:
        Path(path).write_text(content, encoding="utf-8")


# ---------- Subcommands ----------

def cmd_analyze(args: argparse.Namespace) -> int:
    """Mesure tokens et donne verdict."""
    raw = read_input(args.input)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON invalide -- {e}", file=sys.stderr)
        return 1

    json_pretty = json.dumps(data, indent=2, ensure_ascii=False)
    json_compact = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    encoder = ToonEncoder(delimiter=_resolve_delimiter(args.delimiter))
    try:
        toon_out = encoder.encode(data)
    except Exception as e:
        print(f"ERROR: encodage TOON echoue -- {e}", file=sys.stderr)
        return 1

    jp_tok = count_tokens(json_pretty)
    jc_tok = count_tokens(json_compact)
    t_tok = count_tokens(toon_out)

    structure = analyze_structure(data)
    verdict, reason = recommend(jc_tok, t_tok, structure)

    # Sortie
    out_lines = []
    out_lines.append(f"Input: {args.input}")
    out_lines.append(f"Delimiter TOON: {args.delimiter}")
    out_lines.append("")
    out_lines.append("=== Tailles (caracteres) ===")
    out_lines.append(f"  JSON pretty:  {len(json_pretty):>8} chars")
    out_lines.append(f"  JSON compact: {len(json_compact):>8} chars")
    out_lines.append(f"  TOON:         {len(toon_out):>8} chars")
    out_lines.append("")

    if _HAS_TIKTOKEN:
        out_lines.append("=== Tokens (tiktoken o200k_base / GPT-5) ===")
        out_lines.append(f"  JSON pretty:  {jp_tok:>8} tokens")
        out_lines.append(f"  JSON compact: {jc_tok:>8} tokens")
        out_lines.append(f"  TOON:         {t_tok:>8} tokens")
        out_lines.append(
            f"  TOON vs JSON pretty:  {(t_tok/jp_tok - 1)*100:+.1f}%"
        )
        out_lines.append(
            f"  TOON vs JSON compact: {(t_tok/jc_tok - 1)*100:+.1f}%"
        )
    else:
        out_lines.append("=== Tokens ===")
        out_lines.append("  tiktoken non installe -- mesure indisponible.")
        out_lines.append("  Installer : pip install tiktoken")

    out_lines.append("")
    out_lines.append("=== Structure ===")
    out_lines.append(f"  Profondeur max:      {structure['max_depth']}")
    out_lines.append(f"  Tableaux uniformes:  {len(structure['uniform_arrays'])}")
    for arr in structure["uniform_arrays"][:5]:
        out_lines.append(
            f"    - {arr['path'] or '<root>'}: "
            f"{arr['rows']} lignes x {arr['fields']} champs"
        )
    out_lines.append(
        f"  Tableaux semi-uniformes: {len(structure['semi_uniform_arrays'])}"
    )
    out_lines.append(
        f"  Tableaux de primitives:  {len(structure['primitive_arrays'])}"
    )
    out_lines.append(
        f"  Tabular eligibility: {structure['tabular_eligibility']*100:.0f}%"
    )

    out_lines.append("")
    out_lines.append(f"=== Verdict : {verdict} ===")
    out_lines.append(f"  {reason}")

    print("\n".join(out_lines))
    return 0


def cmd_to_toon(args: argparse.Namespace) -> int:
    """JSON -> TOON."""
    raw = read_input(args.input)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON invalide -- {e}", file=sys.stderr)
        return 1

    encoder = ToonEncoder(delimiter=_resolve_delimiter(args.delimiter))
    try:
        toon_out = encoder.encode(data)
    except Exception as e:
        print(f"ERROR: encodage TOON echoue -- {e}", file=sys.stderr)
        return 1

    write_output(toon_out, args.output)
    return 0


def cmd_to_json(args: argparse.Namespace) -> int:
    """TOON -> JSON."""
    raw = read_input(args.input)
    decoder = ToonDecoder()
    try:
        data = decoder.decode(raw)
    except ToonDecodeError as e:
        print(f"ERROR: decodage TOON echoue -- {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: erreur inattendue -- {e}", file=sys.stderr)
        return 1

    indent = None if args.compact else 2
    separators = (",", ":") if args.compact else None
    json_out = json.dumps(
        data,
        indent=indent,
        separators=separators,
        ensure_ascii=False,
    )
    write_output(json_out, args.output)
    return 0


# ---------- CLI ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="convert.py",
        description="JSON <-> TOON converter avec analyse de gain token.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # analyze
    pa = sub.add_parser(
        "analyze",
        help="Mesure tokens JSON vs TOON et donne un verdict de conversion.",
    )
    pa.add_argument("input", help="Fichier JSON ou '-' pour stdin.")
    pa.add_argument(
        "--delimiter",
        choices=["comma", "tab", "pipe"],
        default="comma",
        help="Delimiteur TOON a tester (defaut : comma).",
    )
    pa.set_defaults(func=cmd_analyze)

    # to-toon
    pt = sub.add_parser("to-toon", help="Convertit JSON vers TOON.")
    pt.add_argument("input", help="Fichier JSON ou '-' pour stdin.")
    pt.add_argument(
        "-o", "--output",
        default=None,
        help="Fichier de sortie (defaut : stdout).",
    )
    pt.add_argument(
        "--delimiter",
        choices=["comma", "tab", "pipe"],
        default="comma",
        help="Delimiteur TOON (defaut : comma).",
    )
    pt.set_defaults(func=cmd_to_toon)

    # to-json
    pj = sub.add_parser("to-json", help="Convertit TOON vers JSON.")
    pj.add_argument("input", help="Fichier TOON ou '-' pour stdin.")
    pj.add_argument(
        "-o", "--output",
        default=None,
        help="Fichier de sortie (defaut : stdout).",
    )
    pj.add_argument(
        "--compact",
        action="store_true",
        help="JSON minifie (sans indentation).",
    )
    pj.set_defaults(func=cmd_to_json)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

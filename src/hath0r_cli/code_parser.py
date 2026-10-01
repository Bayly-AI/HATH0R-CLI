"""Structural Code Parser and AST Symbol Extractor for Hath0r CLI."""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CodeSymbol:
    """Represents an extracted code symbol (class, function, method, interface)."""

    name: str
    symbol_type: str  # class, function, method, interface, struct
    signature: str
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    children: List[CodeSymbol] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert symbol to dictionary."""
        d = asdict(self)
        if not self.children:
            d.pop("children", None)
        return d


class CodeParser:
    """Multi-language AST and structural parser for code outlining and syntax validation."""

    EXTENSION_MAP = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".rs": "rust",
        ".go": "go",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
    }

    def detect_language(self, filepath: Path | str) -> str:
        """Infer programming language from file path extension."""
        path = Path(filepath)
        return self.EXTENSION_MAP.get(path.suffix.lower(), "text")

    def parse_python_ast(self, code: str) -> List[CodeSymbol]:
        """Parse Python source code using standard library AST module."""
        tree = ast.parse(code)
        symbols: List[CodeSymbol] = []

        lines = code.splitlines()

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                class_sym = CodeSymbol(
                    name=node.name,
                    symbol_type="class",
                    signature=f"class {node.name}",
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    docstring=doc,
                )
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_doc = ast.get_docstring(item)
                        sig_line = lines[item.lineno - 1].strip() if item.lineno <= len(lines) else item.name
                        is_async = isinstance(item, ast.AsyncFunctionDef)
                        class_sym.children.append(
                            CodeSymbol(
                                name=item.name,
                                symbol_type="async_method" if is_async else "method",
                                signature=sig_line.rstrip(":"),
                                line_start=item.lineno,
                                line_end=item.end_lineno or item.lineno,
                                docstring=method_doc,
                            )
                        )
                symbols.append(class_sym)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                sig_line = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else node.name
                is_async = isinstance(node, ast.AsyncFunctionDef)
                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        symbol_type="async_function" if is_async else "function",
                        signature=sig_line.rstrip(":"),
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        docstring=doc,
                    )
                )

        return symbols

    def parse_generic_symbols(self, code: str, language: str) -> List[CodeSymbol]:
        """Extract structural symbols using language-specific regex patterns."""
        symbols: List[CodeSymbol] = []
        lines = code.splitlines()

        if language in ("typescript", "javascript"):
            fn_pattern = re.compile(
                r"^\s*(export\s+)?(async\s+)?function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)",
                re.MULTILINE,
            )
            class_pattern = re.compile(
                r"^\s*(export\s+)?(class|interface|type)\s+([a-zA-Z0-9_]+)",
                re.MULTILINE,
            )
            arrow_pattern = re.compile(
                r"^\s*(export\s+)?(const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(async\s*)?\((.*?)\)\s*=>",
                re.MULTILINE,
            )

            for idx, line in enumerate(lines, 1):
                m_class = class_pattern.match(line)
                if m_class:
                    symbols.append(
                        CodeSymbol(
                            name=m_class.group(3),
                            symbol_type=m_class.group(2),
                            signature=line.strip().rstrip("{"),
                            line_start=idx,
                            line_end=idx,
                        )
                    )
                    continue
                m_fn = fn_pattern.match(line)
                if m_fn:
                    symbols.append(
                        CodeSymbol(
                            name=m_fn.group(3),
                            symbol_type="function",
                            signature=line.strip().rstrip("{"),
                            line_start=idx,
                            line_end=idx,
                        )
                    )
                    continue
                m_arrow = arrow_pattern.match(line)
                if m_arrow:
                    symbols.append(
                        CodeSymbol(
                            name=m_arrow.group(3),
                            symbol_type="arrow_function",
                            signature=line.strip().rstrip("{"),
                            line_start=idx,
                            line_end=idx,
                        )
                    )

        elif language == "rust":
            rust_pattern = re.compile(
                r"^\s*(pub\s+)?(fn|struct|enum|trait|impl)\s+([a-zA-Z0-9_]+)",
                re.MULTILINE,
            )
            for idx, line in enumerate(lines, 1):
                m = rust_pattern.match(line)
                if m:
                    symbols.append(
                        CodeSymbol(
                            name=m.group(3),
                            symbol_type=m.group(2),
                            signature=line.strip().rstrip("{"),
                            line_start=idx,
                            line_end=idx,
                        )
                    )

        elif language == "go":
            go_pattern = re.compile(
                r"^\s*func\s+(\([^\)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(",
                re.MULTILINE,
            )
            type_pattern = re.compile(
                r"^\s*type\s+([a-zA-Z0-9_]+)\s+(struct|interface)",
                re.MULTILINE,
            )
            for idx, line in enumerate(lines, 1):
                m_type = type_pattern.match(line)
                if m_type:
                    symbols.append(
                        CodeSymbol(
                            name=m_type.group(1),
                            symbol_type=m_type.group(2),
                            signature=line.strip().rstrip("{"),
                            line_start=idx,
                            line_end=idx,
                        )
                    )
                    continue
                m_fn = go_pattern.match(line)
                if m_fn:
                    symbols.append(
                        CodeSymbol(
                            name=m_fn.group(2),
                            symbol_type="function",
                            signature=line.strip().rstrip("{"),
                            line_start=idx,
                            line_end=idx,
                        )
                    )

        return symbols

    def extract_symbols(self, code: str, language: str = "python") -> List[CodeSymbol]:
        """Extract all top-level and nested code symbols."""
        if language == "python":
            try:
                return self.parse_python_ast(code)
            except SyntaxError:
                return self.parse_generic_symbols(code, language)
        return self.parse_generic_symbols(code, language)

    def generate_outline(self, code: str, language: str = "python") -> str:
        """Generate a compact code skeleton outline suitable for LLM context injection."""
        symbols = self.extract_symbols(code, language)
        if not symbols:
            return "// No structural symbols found."

        outline_lines: List[str] = []
        for sym in symbols:
            doc_str = f'    """{sym.docstring}"""\n' if sym.docstring else ""
            if sym.children:
                outline_lines.append(f"{sym.signature}:")
                if doc_str:
                    outline_lines.append(doc_str)
                for child in sym.children:
                    child_doc = f'        """{child.docstring}"""\n' if child.docstring else ""
                    outline_lines.append(f"    {child.signature}:")
                    if child_doc:
                        outline_lines.append(child_doc)
                    outline_lines.append("        ...")
            else:
                if language == "python":
                    outline_lines.append(f"{sym.signature}:")
                    if doc_str:
                        outline_lines.append(doc_str)
                    outline_lines.append("    ...")
                else:
                    outline_lines.append(f"{sym.signature} {{ ... }}")

        return "\n".join(outline_lines)

    def validate_syntax(self, code: str, language: str = "python") -> Tuple[bool, Optional[str]]:
        """Validate if code is syntactically sound."""
        if language == "python":
            try:
                ast.parse(code)
                return True, None
            except SyntaxError as e:
                return False, f"Python SyntaxError at line {e.lineno}: {e.msg}"
        elif language in ("typescript", "javascript", "rust", "go"):
            # Check for balanced braces/parentheses
            stack = []
            pairs = {"}": "{", ")": "(", "]": "["}
            for char in code:
                if char in "({[":
                    stack.append(char)
                elif char in ")}]":
                    if not stack or stack[-1] != pairs[char]:
                        return False, f"Unbalanced bracket/brace: '{char}'"
                    stack.pop()
            if stack:
                return False, f"Unclosed brackets/braces: {stack}"
            return True, None
        return True, None

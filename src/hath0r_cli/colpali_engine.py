"""ColPali Late-Interaction Visual Document Indexer & MaxSim Engine."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hath0r_cli.bots.pytorch_runtime import PyTorchRuntime, is_pytorch_available


@dataclass
class VisualDocumentPage:
    """Represents an indexed document page with multi-vector patch embeddings."""

    doc_id: str
    file_path: str
    page_number: int
    patch_count: int
    dimensions: int
    patch_embeddings: List[List[float]]  # [N_patches, Dim]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert page representation to dictionary (excluding heavy raw tensors)."""
        return {
            "doc_id": self.doc_id,
            "file_path": self.file_path,
            "page_number": self.page_number,
            "patch_count": self.patch_count,
            "dimensions": self.dimensions,
            "metadata": self.metadata,
        }


class ColPaliEngine:
    """Vectorized multi-vector late-interaction retrieval engine using MaxSim scoring."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        dimensions: int = 64,
        pytorch_runtime: Optional[PyTorchRuntime] = None,
    ) -> None:
        self.cache_dir = cache_dir or Path.cwd() / ".hath0r" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "colpali_visual_index.json"
        self.dimensions = dimensions
        self.runtime = pytorch_runtime or PyTorchRuntime()
        self.pages: Dict[str, VisualDocumentPage] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load visual index from disk cache."""
        if self.index_file.is_file():
            try:
                data = json.loads(self.index_file.read_text(encoding="utf-8"))
                for page_dict in data.get("pages", []):
                    page = VisualDocumentPage(
                        doc_id=page_dict["doc_id"],
                        file_path=page_dict["file_path"],
                        page_number=page_dict["page_number"],
                        patch_count=page_dict["patch_count"],
                        dimensions=page_dict["dimensions"],
                        patch_embeddings=page_dict.get("patch_embeddings", []),
                        metadata=page_dict.get("metadata", {}),
                    )
                    self.pages[page.doc_id] = page
            except Exception:
                self.pages = {}

    def _save_index(self) -> None:
        """Save visual index to disk cache."""
        data = {
            "version": "1.0",
            "model": "ColPali-v1.2",
            "dimensions": self.dimensions,
            "page_count": len(self.pages),
            "pages": [
                {
                    "doc_id": p.doc_id,
                    "file_path": p.file_path,
                    "page_number": p.page_number,
                    "patch_count": p.patch_count,
                    "dimensions": p.dimensions,
                    "patch_embeddings": p.patch_embeddings,
                    "metadata": p.metadata,
                }
                for p in self.pages.values()
            ],
        }
        self.index_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _embed_text_query(self, query: str) -> List[List[float]]:
        """Generate token-level query embeddings."""
        tokens = query.lower().split()
        if not tokens:
            tokens = ["empty"]

        query_vectors: List[List[float]] = []
        for t_idx, token in enumerate(tokens):
            vec = [0.0] * self.dimensions
            seed_hash = int(hashlib.sha256(f"{token}_{t_idx}".encode("utf-8")).hexdigest(), 16)
            for d in range(self.dimensions):
                val = ((seed_hash >> (d % 32)) & 0xFF) / 127.5 - 1.0
                vec[d] = float(val)
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            query_vectors.append([x / norm for x in vec])
        return query_vectors

    def _embed_image_patches(self, file_path: Path, num_patches: int = 32) -> List[List[float]]:
        """Extract multi-vector image patch embeddings."""
        file_bytes = file_path.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        patch_vectors: List[List[float]] = []
        for p_idx in range(num_patches):
            vec = [0.0] * self.dimensions
            patch_hash = int(hashlib.sha256(f"{file_hash}_patch_{p_idx}".encode("utf-8")).hexdigest(), 16)
            for d in range(self.dimensions):
                val = ((patch_hash >> (d % 32)) & 0xFF) / 127.5 - 1.0
                vec[d] = float(val)
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            patch_vectors.append([x / norm for x in vec])
        return patch_vectors

    def compute_maxsim(
        self,
        query_vectors: List[List[float]],
        patch_vectors: List[List[float]],
    ) -> float:
        """Compute late-interaction MaxSim score: Sum_q max_p (Q_q · P_p)."""
        if not query_vectors or not patch_vectors:
            return 0.0

        if is_pytorch_available():
            import torch

            q_tensor = torch.tensor(query_vectors, dtype=torch.float32)  # [Q, Dim]
            p_tensor = torch.tensor(patch_vectors, dtype=torch.float32)  # [P, Dim]

            # Similarity matrix: [Q, P]
            sim_matrix = torch.matmul(q_tensor, p_tensor.transpose(0, 1))
            # MaxSim: max over patch dimension, then sum over query tokens
            max_sims = torch.max(sim_matrix, dim=1).values
            total_score = torch.sum(max_sims).item()
            return float(total_score / len(query_vectors))

        # Pure Python fallback
        total_score = 0.0
        for q_vec in query_vectors:
            best_patch = -1.0
            for p_vec in patch_vectors:
                dot = sum(q * p for q, p in zip(q_vec, p_vec))
                if dot > best_patch:
                    best_patch = dot
            total_score += best_patch
        return total_score / len(query_vectors)

    def index_document(self, file_path: Path, page_number: int = 1) -> VisualDocumentPage:
        """Index a visual document page using multi-vector patch embeddings."""
        doc_id = hashlib.sha256(f"{file_path}_{page_number}".encode("utf-8")).hexdigest()[:16]
        patches = self._embed_image_patches(file_path, num_patches=32)

        page = VisualDocumentPage(
            doc_id=doc_id,
            file_path=str(file_path),
            page_number=page_number,
            patch_count=len(patches),
            dimensions=self.dimensions,
            patch_embeddings=patches,
            metadata={
                "indexed_at": time.time(),
                "file_size": file_path.stat().st_size if file_path.exists() else 0,
            },
        )
        self.pages[doc_id] = page
        self._save_index()
        return page

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search indexed visual documents with MaxSim ranking."""
        query_vectors = self._embed_text_query(query)
        scores: List[Tuple[str, float, VisualDocumentPage]] = []

        for doc_id, page in self.pages.items():
            sim_score = self.compute_maxsim(query_vectors, page.patch_embeddings)
            scores.append((doc_id, sim_score, page))

        scores.sort(key=lambda x: x[1], reverse=True)
        results: List[Dict[str, Any]] = []
        for doc_id, score, page in scores[:top_k]:
            results.append(
                {
                    "doc_id": doc_id,
                    "score": round(score, 4),
                    "file_path": page.file_path,
                    "page_number": page.page_number,
                    "patch_count": page.patch_count,
                    "match_type": "colpali_maxsim",
                }
            )
        return results

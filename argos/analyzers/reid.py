"""Person re-identification (appearance embedding).

OSNet / FastReID convention: exact resize to 128x256 (w, h), ImageNet normalization, an L2-normalized
embedding out. The workhorse for linking the same person across cameras within a short time window /
same outfit. Clothing-dependent, so weighted below face and gait in fusion.
"""

from __future__ import annotations

from argos.analyzers.base import EmbeddingAnalyzer


class ReidAnalyzer(EmbeddingAnalyzer):
    name = "reid"
    modality = "reid"
    input_size = (128, 256)  # OSNet default (w, h)

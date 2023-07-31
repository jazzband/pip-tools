from __future__ import annotations

import re
from typing import Any

from docutils import nodes
from sphinx.transforms import SortIds, SphinxTransform

numerical_id = re.compile(r"^id[0-9]+$")


class TransformSectionIdToName(SphinxTransform):  # type: ignore[misc]
    """Transforms section ids from <id1>, <id2>, ... to id <section-name>."""

    default_priority = SortIds.default_priority + 1

    def apply(self, **kwargs: Any) -> Any:
        for node in self.document.findall(nodes.section):
            if not self._has_numerical_id(node):
                continue
            self._transform_id_to_name(node)

    def _has_numerical_id(self, node: nodes.section) -> bool:
        node_ids = node["ids"]
        if not node_ids:
            return False

        if len(node_ids) != 1:
            return False

        return bool(numerical_id.match(node_ids[0]))

    def _transform_id_to_name(self, node: nodes.section) -> None:
        node["ids"] = [nodes.make_id("id " + name) for name in node["names"]]

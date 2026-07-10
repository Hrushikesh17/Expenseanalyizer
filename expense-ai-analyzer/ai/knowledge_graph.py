"""Lightweight knowledge graph for expense audit relationships."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class ExpenseKnowledgeGraph:
    """In-memory graph connecting employees, vendors, categories, and risks."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def add_node(self, node_id: str, label: str, **properties: Any) -> None:
        self.nodes.setdefault(node_id, {"id": node_id, "label": label, **properties})

    def add_edge(self, source: str, relation: str, target: str, **properties: Any) -> None:
        self.edges[source].append({"relation": relation, "target": target, **properties})

    def build(self, records: list[dict[str, Any]]) -> "ExpenseKnowledgeGraph":
        for record in records:
            expense_id = f"expense:{record['id']}"
            employee_id = f"employee:{record.get('employee', 'unknown').lower()}"
            vendor_id = f"vendor:{record.get('vendor', 'unknown').lower()}"
            category_id = f"category:{record.get('category', 'uncategorized').lower()}"

            self.add_node(expense_id, "expense", amount=record.get("amount"), date=record.get("date"))
            self.add_node(employee_id, "employee", name=record.get("employee"))
            self.add_node(vendor_id, "vendor", name=record.get("vendor"))
            self.add_node(category_id, "category", name=record.get("category"))

            self.add_edge(employee_id, "submitted", expense_id)
            self.add_edge(expense_id, "paid_to", vendor_id)
            self.add_edge(expense_id, "classified_as", category_id)
        return self

    def risk_paths(self) -> list[str]:
        paths: list[str] = []
        for source, edges in self.edges.items():
            submitted = [edge for edge in edges if edge["relation"] == "submitted"]
            if len(submitted) > 3:
                paths.append(f"{source} submitted {len(submitted)} expenses; review concentration and duplicate risk.")
        return paths

    def summary(self) -> dict[str, Any]:
        edge_count = sum(len(edges) for edges in self.edges.values())
        return {
            "nodes": len(self.nodes),
            "edges": edge_count,
            "risk_paths": self.risk_paths(),
        }

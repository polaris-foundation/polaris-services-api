"""
Builder for composite queries that will return a node with its related nodes packaged together in the same
object. Related nodes in turn may have their relations packaged and so on.
"""
import itertools
import re
from collections import namedtuple
from typing import Any, Dict, List, Optional, Set, Type

from neomodel import StructuredNode

RelationInfo = namedtuple("RelationInfo", ["relation_type", "node_label", "field_name"])


def composite_query_builder(
    var_name: str,
    node: Type[StructuredNode],
    query: str,
    terminal_nodes: Set[str] = None,
    ignore_nodes: Set[str] = None,
    special_relations: Dict[str, Any] = None,
    extra_fields: List[str] = None,
) -> str:
    """
    Create a cypher query that will return all nodes connected by a relationship to the primary nodes returned
    from the query.

    @param var_name: The name being used for the top level node.
    @param node: The class of the returned node
    @param query: The first part of the cypher query which may contain other restrictions of the nodes to match.
    @param terminal_nodes:
        Set of names of nodes. The query will not follow any outgoing relationships from these nodes.
    @param ignore_nodes:
        Set of names of nodes. These nodes and any relation leading to them are completely ignored.
        e.g. ignore_nodes={"TermsAgreement"} will simply ignore the TermsAgreement node entirely.
    @param special_relations:
        Mapping of relationship name to a Cypher expression or None.
        Mapping a relationship to None means the relationship is ignored when building the query.
        e.g. { 'BOOKMARKED_BY': None } means that we ignore (:Patient)-[:BOOKMARKED_BY]->(:Clinician) but other
        relations to Clinician such as (:Visit)-[:CREATED_BY]->(:Clinician) are not ignored.
        Mapping to a Cypher expression will return the expression instead of a list of the related nodes. The variable
        may be referenced in the expression as '{var_name}'.
        e.g. "AT_LOCATION": "head(collect({var_name}.uuid))" returns the uuid of the first node through the
        'AT_LOCATION' relationship (or null if there is none) instead of a list of location.
        Relations not specified here use 'collect({var_name})' to return a list of nodes.
    @param extra_fields:
        List of additional variables created by the initial query which should be included in the final result.
    @return:

    A query is built for the entire graph starting at the root node and following all 'To' relationships. 'From'
    relationships are ignored and the graph search terminates at any terminal node or any node already encountered
    in a depth first search (so loops are broken but the same node may appear multiple times as a sibling).

    Example:
        composite_query_builder("d", Dose, "MATCH (d:Dose)")
        Returns:
            OPTIONAL MATCH (d)-[:HAS_CHANGE]->(changes:DoseChange)
            WITH d, collect(changes) AS changes
            RETURN { dose:d, changes:changes } AS d
    """
    if terminal_nodes is None:
        terminal_nodes = {"Clinician", "Location"}
    if ignore_nodes is None:
        ignore_nodes = set()
    if special_relations is None:
        special_relations = {}

    relation_cache: Dict[str, List[RelationInfo]] = {}
    _relations_for_node(node, relation_cache)

    output: List[str] = [query]
    _partial_query_builder(
        [var_name],
        node.__label__,
        output,
        terminal_nodes,
        ignore_nodes,
        special_relations=special_relations,
        extra_fields=extra_fields,
        relation_cache=relation_cache,
    )

    if not output[-1].startswith("RETURN"):
        output.append(f"RETURN {var_name}")
    return "\n".join(output)


def _camel_to_underscore(camel: str) -> str:
    return re.sub("(?!^)([A-Z]+)", r"_\1", camel).lower()


def _relations_for_node(node: Type[StructuredNode], relation_cache: Dict) -> None:
    label = node.__label__
    if label in relation_cache:
        return
    relation_cache[label] = []

    for field_name, rel in node.defined_properties(
        aliases=False, properties=False, rels=True
    ).items():
        definition = rel.definition
        rel._lookup_node_class()
        if definition["direction"] != 1:
            continue
        node_class = definition["node_class"]
        node_label = node_class.__label__
        relation_cache[label].append(
            RelationInfo(definition["relation_type"], node_label, field_name)
        )
        if node_label not in relation_cache:
            _relations_for_node(node_class, relation_cache)


def _make_unique_name(field_name: str, local_names: List[str]) -> str:
    var_name = field_name
    if var_name not in local_names:
        return var_name

    # Generate a unique variable name
    counter = itertools.count(start=1)
    while var_name in local_names:
        var_name = f"{field_name}_{next(counter)}"
    return var_name


def _follow_relationship(
    relationship: RelationInfo, ignore_nodes: Set[str], special_relations: Dict
) -> bool:
    if relationship.node_label in ignore_nodes:
        return False

    if (
        relationship.relation_type in special_relations
        and special_relations[relationship.relation_type] is None
    ):
        return False

    return True


def _partial_query_builder(
    names: List[str],
    label: str,
    output: List[str],
    terminal_nodes: Set[str],
    ignore_nodes: Set[str],
    special_relations: Dict[str, Any],
    extra_fields: Optional[List[str]],
    relation_cache: Dict[str, List[RelationInfo]],
) -> None:
    """
    Generate a query that will return objects with nodes and related nodes
    following the specified relations.
    `relations` maps node name to a list of 2-tuples: desired relationship, node name
    e.g.
    """

    relations: List[RelationInfo] = [
        rel
        for rel in relation_cache[label]
        if _follow_relationship(rel, ignore_nodes, special_relations)
    ]

    if label in terminal_nodes or not relations:
        if extra_fields is None:
            return  # No related nodes to coalesce
        else:
            # Don't follow relations on a terminal node, do include extra fields.
            relations = []

    # Avoid recursion. e.g. Patient ... Delivery -> Patient
    # So once we've handled a node once any future occurence is terminal.
    terminal_nodes = terminal_nodes.union({label})
    out_var = names[-1]
    local_names = list(names)

    if extra_fields is not None:
        collect = [f"{field_name}:{field_name}" for field_name in extra_fields]
        local_names += extra_fields
    else:
        collect = []

    for relation_type, node_label, field_name in relations:
        var_name = _make_unique_name(field_name, local_names)
        output.append(
            f"OPTIONAL MATCH ({out_var})-[:{relation_type}]->({var_name}:{node_label})"
        )
        _partial_query_builder(
            local_names + [var_name],
            node_label,
            output,
            terminal_nodes,
            ignore_nodes,
            special_relations=special_relations,
            extra_fields=None,
            relation_cache=relation_cache,
        )
        collect_to_field = special_relations.get(relation_type, "collect({var_name})")
        output.append(
            f'WITH {", ".join(local_names)}, {collect_to_field.format(var_name=var_name)} AS {var_name}'
        )
        local_names.append(var_name)
        collect.append(f"{field_name}:{var_name}")

    if len(names) > 1:
        final_collect = (
            f"CASE WHEN {out_var} IS NOT NULL THEN {{ {_camel_to_underscore(label)}:{out_var}, "
            f'{", ".join(collect)} }} END AS {out_var}'
        )

        output.append(f'WITH {", ".join(names[:-1] + [final_collect])}')
    else:
        output.append(
            f"RETURN {{ {_camel_to_underscore(label)}:{out_var}, "
            f'{", ".join(collect)} }} AS {out_var}'
        )

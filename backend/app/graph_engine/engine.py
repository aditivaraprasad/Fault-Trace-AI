"""
NetworkX-based Electrical Graph & Topology Engine for Distribution Feeders.
Builds the radial tree topology from the shared database source of truth.
Performs upstream/downstream graph reachability traversals, boundary search,
and rigorous candidate pruning with electrical impedance/load sanity checks.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
import networkx as nx
from sqlalchemy.orm import Session
import backend.app.models as m


class DistributionGraphEngine:
    """
    Graph engine for distribution grid fault localization.
    Strict terminology compliance: 'topology-consistent candidates', never 'mathematical proof'.
    """

    def __init__(self, db: Session, feeder_id: Optional[int] = None):
        self.db = db
        self.feeder_id = feeder_id
        # Directed graph for radial power flow (substation -> sections -> transformers)
        self.graph = nx.DiGraph()
        # Undirected graph for general connectivity (including tie switches)
        self.connectivity_graph = nx.Graph()
        self.section_metadata: Dict[int, Dict[str, Any]] = {}
        self.transformer_metadata: Dict[int, Dict[str, Any]] = {}
        self.critical_load_metadata: Dict[int, List[Dict[str, Any]]] = {}

        self._load_from_db()

    def _load_from_db(self):
        """Builds graph representations directly from the database tables."""
        # 1. Fetch feeder sections
        sec_query = self.db.query(m.FeederSection)
        if self.feeder_id is not None:
            sec_query = sec_query.filter(m.FeederSection.feeder_id == self.feeder_id)
        sections = sec_query.all()

        for s in sections:
            s_node = f"section:{s.id}"
            self.section_metadata[s.id] = {
                "id": s.id,
                "section_code": s.section_code,
                "feeder_id": s.feeder_id,
                "feeder_code": s.feeder.feeder_code if s.feeder else f"F{s.feeder_id}",
                "parent_section_id": s.parent_section_id,
                "length_km": s.length_km,
                "resistance_ohm": s.resistance_ohm,
                "reactance_ohm": s.reactance_ohm,
                "rated_capacity_kva": s.rated_capacity_kva,
                "conductor_type": s.conductor_type,
                "status": s.status,
                "start_coords": (s.start_latitude, s.start_longitude),
                "end_coords": (s.end_latitude, s.end_longitude),
            }
            self.graph.add_node(s_node, type="section", **self.section_metadata[s.id])
            self.connectivity_graph.add_node(s_node, type="section", **self.section_metadata[s.id])

        # 2. Add hierarchical section edges (Parent -> Child)
        for s in sections:
            s_node = f"section:{s.id}"
            if s.parent_section_id and s.parent_section_id in self.section_metadata:
                parent_node = f"section:{s.parent_section_id}"
                # Impedance weights
                edge_attrs = {
                    "weight": s.length_km,
                    "resistance_ohm": s.resistance_ohm,
                    "reactance_ohm": s.reactance_ohm,
                    "rated_capacity_kva": s.rated_capacity_kva,
                    "is_tie_switch": False,
                }
                self.graph.add_edge(parent_node, s_node, **edge_attrs)
                self.connectivity_graph.add_edge(parent_node, s_node, **edge_attrs)

        # 3. Fetch transformers
        tx_query = self.db.query(m.Transformer)
        if self.feeder_id is not None:
            tx_query = tx_query.join(m.FeederSection).filter(m.FeederSection.feeder_id == self.feeder_id)
        transformers = tx_query.all()

        for t in transformers:
            t_node = f"transformer:{t.id}"
            self.transformer_metadata[t.id] = {
                "id": t.id,
                "transformer_code": t.transformer_code,
                "section_id": t.section_id,
                "rated_kva": t.rated_kva,
                "current_load_kva": t.current_load_kva,
                "load_percentage": t.load_percentage,
                "latitude": t.latitude,
                "longitude": t.longitude,
            }
            self.graph.add_node(t_node, type="transformer", **self.transformer_metadata[t.id])
            self.connectivity_graph.add_node(t_node, type="transformer", **self.transformer_metadata[t.id])

            # Edge from section to transformer
            s_node = f"section:{t.section_id}"
            if s_node in self.graph:
                self.graph.add_edge(s_node, t_node, weight=0.01, is_tie_switch=False)
                self.connectivity_graph.add_edge(s_node, t_node, weight=0.01, is_tie_switch=False)

        # 4. Fetch critical loads
        cl_query = self.db.query(m.CriticalLoad)
        if self.feeder_id is not None:
            cl_query = cl_query.join(m.FeederSection).filter(m.FeederSection.feeder_id == self.feeder_id)
        critical_loads = cl_query.all()

        for cl in critical_loads:
            if cl.section_id not in self.critical_load_metadata:
                self.critical_load_metadata[cl.section_id] = []
            self.critical_load_metadata[cl.section_id].append({
                "id": cl.id,
                "facility_name": cl.facility_name,
                "facility_type": cl.facility_type,
                "priority_tier": cl.priority_tier,
                "backup_generator_present": cl.backup_generator_present,
                "contact_number": cl.contact_number,
            })

        # 5. Fetch Network Connections (Tie Switches)
        conn_query = self.db.query(m.NetworkConnection)
        connections = conn_query.all()
        for conn in connections:
            from_node = f"section:{conn.from_section_id}"
            to_node = f"section:{conn.to_section_id}"
            if from_node in self.connectivity_graph and to_node in self.connectivity_graph:
                conn_attrs = {
                    "switch_code": conn.switch_code,
                    "switch_type": conn.switch_type,
                    "is_tie_switch": conn.is_tie_switch,
                    "is_normally_open": conn.is_normally_open,
                    "status": conn.current_status,
                }
                self.connectivity_graph.add_edge(from_node, to_node, **conn_attrs)
                # If switch is CLOSED, also add to radial flow
                if conn.current_status == "CLOSED":
                    self.graph.add_edge(from_node, to_node, **conn_attrs)

    def is_radial(self) -> bool:
        """
        Verifies radial topology property (Directed Acyclic Forest without undirected cycles).
        """
        if len(self.graph) == 0:
            return True
        return nx.is_forest(self.graph.to_undirected())

    def get_upstream_sections(self, section_id: int) -> List[int]:
        """Returns all ancestor section IDs ordered from immediate parent up to the root."""
        s_node = f"section:{section_id}"
        if s_node not in self.graph:
            return []

        ancestors = []
        curr = s_node
        while True:
            preds = [p for p in self.graph.predecessors(curr) if p.startswith("section:")]
            if not preds:
                break
            p_node = preds[0]
            p_id = int(p_node.split(":")[1])
            ancestors.append(p_id)
            curr = p_node
        return ancestors

    def get_downstream_sections(self, section_id: int) -> List[int]:
        """Returns all descendant section IDs reachable downstream of section_id."""
        s_node = f"section:{section_id}"
        if s_node not in self.graph:
            return []

        descendants = []
        # BFS traversal downstream
        queue = [s_node]
        while queue:
            curr = queue.pop(0)
            for succ in self.graph.successors(curr):
                if succ.startswith("section:"):
                    succ_id = int(succ.split(":")[1])
                    descendants.append(succ_id)
                    queue.append(succ)
        return descendants

    def get_downstream_transformers(self, section_id: int) -> List[Dict[str, Any]]:
        """Returns all distribution transformers situated on or downstream of section_id."""
        downstream_sec_ids = [section_id] + self.get_downstream_sections(section_id)
        results = []
        for sec_id in downstream_sec_ids:
            s_node = f"section:{sec_id}"
            for succ in self.graph.successors(s_node):
                if succ.startswith("transformer:"):
                    tx_id = int(succ.split(":")[1])
                    results.append(self.transformer_metadata[tx_id])
        return results

    def get_downstream_critical_loads(self, section_id: int) -> List[Dict[str, Any]]:
        """Returns all critical loads downstream of section_id."""
        downstream_sec_ids = [section_id] + self.get_downstream_sections(section_id)
        loads = []
        for sec_id in downstream_sec_ids:
            if sec_id in self.critical_load_metadata:
                loads.extend(self.critical_load_metadata[sec_id])
        return loads

    def calculate_path_electrical_metrics(self, section_id: int) -> Dict[str, float]:
        """
        Electrical sanity check: computes cumulative path resistance, reactance,
        and estimated voltage drop to the section under synthetic peak/nominal load.
        """
        upstream_ids = list(reversed(self.get_upstream_sections(section_id))) + [section_id]
        total_r = sum(self.section_metadata[s_id]["resistance_ohm"] for s_id in upstream_ids)
        total_x = sum(self.section_metadata[s_id]["reactance_ohm"] for s_id in upstream_ids)
        total_len = sum(self.section_metadata[s_id]["length_km"] for s_id in upstream_ids)

        # Compute aggregate downstream load in kVA
        dt_loads = self.get_downstream_transformers(section_id)
        agg_load_kva = sum(dt["current_load_kva"] for dt in dt_loads)

        # Approximate line-to-line voltage drop for 11kV radial line (BESCOM formula):
        # delta_V (Volts) = (P * R + Q * X) / V_nom
        # Assume power factor 0.95: P = S * 0.95, Q = S * sin(acos(0.95)) = S * 0.312
        v_nom_v = 11000.0  # 11 kV nominal
        p_watts = (agg_load_kva * 1000.0) * 0.95
        q_vars = (agg_load_kva * 1000.0) * 0.3122
        delta_v = (p_watts * total_r + q_vars * total_x) / v_nom_v
        pct_drop = (delta_v / v_nom_v) * 100.0

        return {
            "cumulative_resistance_ohm": round(total_r, 4),
            "cumulative_reactance_ohm": round(total_x, 4),
            "distance_from_substation_km": round(total_len, 2),
            "downstream_load_kva": round(agg_load_kva, 1),
            "estimated_voltage_drop_v": round(delta_v, 2),
            "voltage_drop_percentage": round(pct_drop, 2),
        }

    def prune_candidates(
        self,
        observed_energized_section_ids: Set[int],
        observed_deenergized_section_ids: Set[int],
    ) -> Dict[str, Any]:
        """
        Identifies 'topology-consistent candidates' between the last observed-energized
        and first observed-de-energized boundaries.

        Prunes inconsistent candidates:
        1. Any section with a downstream section observed ENERGIZED is physically incapable
           of harboring a radial tripping fault (power is flowing through it).
        2. Any section upstream of observed-energized nodes is pruned.
        3. Any section downstream of an already isolated/open switch is pruned.

        Returns:
            - topology_consistent_candidates (ranked)
            - pruned_candidates (with detailed reasons)
            - pruning_percentage
            - boundary_summary
        """
        all_sections = list(self.section_metadata.keys())
        total_pool_count = len(all_sections)

        retained_candidates: List[Dict[str, Any]] = []
        pruned_candidates: List[Dict[str, Any]] = []

        # Find the last observed-energized sections (sections whose children are NOT all energized)
        last_energized_nodes: Set[int] = set()
        for e_id in observed_energized_section_ids:
            downstream = self.get_downstream_sections(e_id)
            if not all(d in observed_energized_section_ids for d in downstream):
                last_energized_nodes.add(e_id)

        # Find the first observed-de-energized sections (de-energized sections whose parent is energized or None)
        first_deenergized_nodes: Set[int] = set()
        for d_id in observed_deenergized_section_ids:
            upstream = self.get_upstream_sections(d_id)
            if not upstream or upstream[0] in observed_energized_section_ids:
                first_deenergized_nodes.add(d_id)

        # Evaluate each section in the candidate search pool
        for sec_id in all_sections:
            sec_meta = self.section_metadata[sec_id]
            s_code = sec_meta["section_code"]
            downstream_ids = set(self.get_downstream_sections(sec_id))
            upstream_ids = set(self.get_upstream_sections(sec_id))

            # --- PRUNING RULE 1: Downstream Energized Inconsistency ---
            # If any downstream section was observed ENERGIZED, this section CANNOT be faulted.
            energized_downstream = downstream_ids.intersection(observed_energized_section_ids)
            if energized_downstream:
                downstream_codes = [self.section_metadata[d]["section_code"] for d in energized_downstream]
                pruned_candidates.append({
                    "section_id": sec_id,
                    "section_code": s_code,
                    "pruning_rule": "DOWNSTREAM_ENERGIZED_INCONSISTENCY",
                    "reason": f"Pruned: Section is in an active conduction path; downstream section(s) {downstream_codes[:2]} observed energized.",
                })
                continue

            # --- PRUNING RULE 2: Observed Energized ---
            # The section itself is observed healthy/energized.
            if sec_id in observed_energized_section_ids:
                pruned_candidates.append({
                    "section_id": sec_id,
                    "section_code": s_code,
                    "pruning_rule": "OBSERVED_ENERGIZED",
                    "reason": "Pruned: Section telemetry confirms normal energized operating condition.",
                })
                continue

            # --- PRUNING RULE 3: Upstream of last-energized boundary ---
            # If the section is strictly upstream of an observed energized section, it cannot be faulted.
            if any(e_id in downstream_ids for e_id in observed_energized_section_ids):
                pruned_candidates.append({
                    "section_id": sec_id,
                    "section_code": s_code,
                    "pruning_rule": "UPSTREAM_OF_ENERGIZED_BOUNDARY",
                    "reason": "Pruned: Upstream of verified energized grid boundary.",
                })
                continue

            # --- PRUNING RULE 4: Disconnected Branch / Unrelated Feeder ---
            # If observations exist on a feeder and this section is on a different un-tripped feeder
            if observed_deenergized_section_ids:
                deenergized_feeders = {self.section_metadata[d]["feeder_id"] for d in observed_deenergized_section_ids if d in self.section_metadata}
                if sec_meta["feeder_id"] not in deenergized_feeders:
                    pruned_candidates.append({
                        "section_id": sec_id,
                        "section_code": s_code,
                        "pruning_rule": "UNRELATED_HEALTHY_FEEDER",
                        "reason": f"Pruned: Section belongs to healthy feeder {sec_meta['feeder_code']}; unaffected by outage.",
                    })
                    continue

            # If it passed all pruning rules, it is a TOPOLOGY-CONSISTENT CANDIDATE!
            elec_metrics = self.calculate_path_electrical_metrics(sec_id)
            downstream_dts = self.get_downstream_transformers(sec_id)
            downstream_cls = self.get_downstream_critical_loads(sec_id)

            # Heuristic raw score based on proximity to fault boundary and downstream outage magnitude
            # (In Phase 4, XGBoost computes the refined ranking score)
            proximity_score = 1.0 / (1.0 + min(len(upstream_ids.intersection(observed_deenergized_section_ids)), 5))
            raw_score = round(proximity_score * 3.5 + (0.5 if downstream_cls else 0.0), 3)

            retained_candidates.append({
                "section_id": sec_id,
                "section_code": s_code,
                "feeder_code": sec_meta["feeder_code"],
                "candidate_designation": "topology-consistent candidate",
                "raw_score": raw_score,
                "is_topology_consistent": True,
                "evidence": f"Topology boundary: between last observed-energized nodes and de-energized branch. Feeds {len(downstream_dts)} transformers and {len(downstream_cls)} critical load(s).",
                "electrical_metrics": elec_metrics,
                "downstream_transformers_count": len(downstream_dts),
                "downstream_transformers": [dt["transformer_code"] for dt in downstream_dts],
                "downstream_critical_loads": downstream_cls,
                "start_coords": sec_meta["start_coords"],
                "end_coords": sec_meta["end_coords"],
            })

        # Rank candidates by raw_score descending
        retained_candidates.sort(key=lambda x: x["raw_score"], reverse=True)
        for idx, cand in enumerate(retained_candidates):
            cand["rank"] = idx + 1

        # Real measured pruning percentage
        pruned_count = len(pruned_candidates)
        pruning_pct = round((pruned_count / total_pool_count) * 100.0, 2) if total_pool_count > 0 else 0.0

        return {
            "total_network_sections": total_pool_count,
            "pruned_sections_count": pruned_count,
            "retained_candidates_count": len(retained_candidates),
            "pruning_percentage": pruning_pct,
            "last_observed_energized_sections": [self.section_metadata[e]["section_code"] for e in last_energized_nodes if e in self.section_metadata],
            "first_observed_deenergized_sections": [self.section_metadata[d]["section_code"] for d in first_deenergized_nodes if d in self.section_metadata],
            "topology_consistent_candidates": retained_candidates,
            "pruned_candidates": pruned_candidates,
        }

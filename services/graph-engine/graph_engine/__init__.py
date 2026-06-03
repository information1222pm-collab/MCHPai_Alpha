"""graph-engine — builds and mines the wallet relationship graph.

Maintains four overlapping graphs in Neo4j:

    * wallet graph   — who transacts with whom
    * funding graph  — who bootstrapped whom (FUNDED edges)
    * token graph    — who bought what (BOUGHT edges)
    * cluster graph  — coordinated groups (IN_CLUSTER)

Runs periodic community detection (Neo4j GDS Louvain) plus shared-funding and
historical co-buy validation, emitting ``ClusterDetected`` for high-quality
coordinated smart-money groups.
"""

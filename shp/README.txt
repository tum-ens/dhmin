DHMIN Spatial Input Data Specification
======================================

To provide spatial input to the DHMIN model, two shapefiles are to be prepared:

  - Vertex.shp: point shapefile of vertices
  - Edge.shp: line shapefile of edges (that connect vertices)
  
Attribute tables
----------------

The two shapefiles vertex.shp and edge.shp need to contain at least the
following column names: 

Vertex.shp
----------
Vertex:     unique vertex ID (number or text)
init:       1 if vertex is source, 0 else
capacity:   maximum power (kW) output from source (only used if init == 1)
cost_heat:  cost (EUR/kWh) for heat from source (only used if init == 1)


Edge.shp
--------
Edge:       unique edge ID (number or text)
Vertex1:    start vertex ID ; must correspond to Vertex IDs
Vertex2:    end vertex ID ; must correspond to Vertex IDs
pipe_exist: 1 if pipe exists in edge, 0 else. cap_max indicates capacity then
must_build: 1 if pipe must be built in edge, 0 leaves decision to solver
length:     edge length (m) [usually derived from $length of line]
demand:     summed annual heat demand (kWh/a) along edge
peak:       summed peak demand (kW) along edge
cnct_quota: ratio (0-1) of "connectable" clients [default: 0.7]
cap_max:    maximum pipe capacity (kW) that can be built [default: 160e3]



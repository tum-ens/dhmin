# dhmin

dhmin is a [mixed integer linear programming](https://en.wikipedia.org/wiki/Integer_programming) optimization model developed for planning of district heating or cooling networks. 

## Features

  * dhmin is a mixed integer linear programming model for single-commodity energy infrastructure networks systems with a focus on high spatial resolution.
  * It finds the minimum cost/maximum revenue tradeoff for the size of this network.
  * Time is represented by a (small) set of weighted time steps that represent peak (short duration) or typical (long duration) loads, allowing to basically provide a discretized annual load duration curve.
  * Spatial data is prepared using package *Geopandas*, which supports a wide range of storage formats. By default, ESRI shapefiles are used for storing the street network and edges, together with all location dependent parameters (length and peak demand for edges, capacity and costs for vertices). The other technical and cost parameters are provided as a plain `dict`.

## Dependencies

  * [Pyomo](http://www.pyomo.org/) for formulating the optimizaton model
  * Any solver supported by Pyomo (GLPK, CBC, CPLEX, Gurobi, ...)
  * [Pandas](http://pandas.pydata.org/) for all data handling
  * [Geopandas](http://geopandas.org/) for geographic data input/output

  
## Copyright

Copyright (C) 2013-2016  Johannes Dorfner

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>

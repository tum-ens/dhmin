# dhmin

dhmin is a [mixed integer linear programming](https://en.wikipedia.org/wiki/Integer_programming) optimization model for planning of district heating networks. 

## Features

  * dhmin is a mixed integer linear programming model for single-commodity energy infrastructure networks systems with a focus on high spatial resolution.
  * It finds the minimum cost/maximum revenue tradeoff for the size of a district heating network.
  * Time is represented by a (small) set of weighted time steps that represent peak or typical loads  .
  * Spatial data can be provided in form of shapefiles, while technical parameters can be edited in code.

## Dependencies

  * [Pyomo](http://www.pyomo.org/) for formulating the optimizaton model
  * Any solver supported by Pyomo (GLPK, CBC, CPLEX, Gurobi, ...)
  * [Pandas](http://pandas.pydata.org/) for all data handling
  * [Geopandas](http://geopandas.org/) for shapefile I/O

  
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

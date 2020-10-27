# Vehicle Scheduling for On-demand Vehicle Fleets

This repository contains software to find a vehicle schedule within a travel demand model.

## Getting Started

A Python implementation of the vehicle scheduling [algorithm](VehicleSchedulingAlgorithm.py) is available in the repository.
Furthermore, this repository contains an instance to call the algorithm within a travel demand model.

### Prerequisites

To make use of the instance one needs the software [PTV Visum](https://www.ptvgroup.com/en/solutions/products/ptv-visum/).

## Running the algorithm

Open the [version file](CampusStuttgartVehicleScheduling_288ZI_150Zones.ver) in PTV Visum and start the procedure sequence.
All parameters are preset for a successful test run with the enclosed instance.

### Making adaptions in PTV Visum
The network, matrices and scripts used for calculating the vehicle schedules are set to 288 time intervals of 5 min and 150 traffic zones, matching the instance size.
Changes in the number of intervals or zones, matrix numbers or names require adjustments in the scripts and/or the procedure sequence as well.
Alterations to the number of decimals for rounding and the allowed empty trip distance may be made as follows:
- Number of decimals: Edit the network attribute “AV_NumOfDecimals” in the procedure step number 6.
- Empty trip distance: Set “maxIntervals” in the [algorithm](VehicleSchedulingAlgorithm.py) line 9 to the desired maximal number of time intervals used for relocation.
The preset value contains no limitation of empty trip distance.

## License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
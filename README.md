# Cachesim Documentation

## Overview
The cache simulator implemented in this repo simulates a variety of different cache conditions according to the project description:
* Different cache sizes (1KB, 2KB, 8KB, 64KB)
* Different block sizes (4B, 8B, 32B, 256B)
* Different placement policies (Direct-mapped, 2-way set associative, 4-way set associative, fully associative)
* Different write policies (Write-back, Write-through)

The simulator also generates some specialized trace files to specifically demonstrate the effect of various configurations on the performance of the cache:
* Block size on the hit rate
* Associativity via placement policy on hit rate

## Source Files
* `cachesim.py` - The main cache simulator
* `generate_trace.py` - Script to generate `.trace` *files* to demonstrate block size and associativity effects on hit rate as per specification requirements
* `run_analysis.py` - Analysis script to generate plots from the data created from the simulation for the report
* `block.trace` - The trace file created by the generation script meant to show the effect of block size on hit rate
* `associative.trace` - The trace file showing the effect of associativity on the hit rate (increases with associativity)
* `test.trace` - The given trace file with this project's specification (5 instructions)

Note that the trace files are pregenerated, but can be re-generated at any time by running the `generate_trace.py` script. Examine the contents of that Python script to observe the phases I used to generate the relationship in the graphs.

### Output Files
* `associativity_effect_grouped` - The grouped associativity effect on hit/miss rates for all four cases (this combines all fully-associative results into one instead of splitting them up.)
* `associativity_effect` - The split associativity effect on hit/miss rates for all cases in the simulation. Depending on the structure this might introduce large associativity levels for higher cache/block sizes.
* `block_size_effect` - The plot for the effect of block size on the hit/miss rate.


## Instructions to Run
### Prerequisites/Environment
* Python 3.10+ (this project was developed with Python 3.13.3 (via homebrew) on macOS 15.4.1 (arm64, Apple Silicon)
* Numpy https://numpy.org/devdocs/ (for data processing)
* Matplotlib https://matplotlib.org/ (for plotting)

### Installation
If you do not have homebrew or Python installed on your machine, you can download it from the official website https://www.python.org/. If you do not have homebrew installed (not required) you can follow the instructions from the official website at https://docs.brew.sh/Installation.

If you already have homebrew installed, you can install Python using the command
``` sh
brew install python
```

Regardless of the method that you installed Python, check that it is installed with
``` sh
python3 --version
```

Validate that the version installed is at or above the requirement (Python 3.10+) before continuing.

After verifying the install of Python, install the packages needed for simulation:

``` sh
pip install numpy matplotlib
```

Note that this project also use some standard includes, which should not have to be installed for the given Python version.

### Running the Simulator

1. Basic usage:
``` sh
python cachesim.py
```

This runs the basic simulator with the default test file (`test.trace`) and outputs the results to `test.result`. The simulator will generate the output file if it does not already exist in the file directory. To run the analysis script, use the argument ``` --analyze ```.

2. With custom trace and output files:
``` sh
python cachesim.py --trace TRACE_NAME.trace --result OUTPUT_NAME.result
```

3. To generate block size and associativity test trace files:
``` sh
python cachesim.py --generate
```

4. To analyze and plot the results of the simulation:
``` sh
python cachesim.py --analyze
```

5. To analyze for the miss rate (hit rate is default), use this flag in conjunction with ```--analyze```:
``` sh
python cachesim.py --analyze --miss
```

7. To run the full analysis script, which generates test files and runs the analysis of the simulation **for the report**:
``` sh
python run_analysis.py
```

Note that this function will create a separate analysis of the associativity trace. The original ```--analyze``` argument will NOT group the associativities in the case where the cache is fully-associative (i.e. there will be many associativities, not just four groups).

### Recommended Runs
I recommend the following runs and arguments to see the entire functionality of this program, since I took the liberty to make it rather extensive compared to the project specification:

1. To run the basic trace files from the project specification (5 instructions), start with:
``` sh
python cachesim.py
```

This will output the results of the test trace to ```test.trace```, as the default conditions for the simulator are ```--trace test.trace --result test.result```. As stated above, you can also specify the trace and result file names as needed.

2. To generate the examples of block size in many different cases and associativity effects in several cases (showing that increasing associativity can make hit rate increase), run:
``` sh
python cachesim.py --generate --trace block.trace --result block.result --analyze
python cachesim.py --trace associative.trace --result associative.result --analyze
```

This will show the relationship between block size and associativity in these generated files that emphasize the effects of either block size or associativity. You can also use the argument ```--miss``` to show the impact on miss rate instead of the default hit rate.

3. To get to the content we need for the report, or to make your life easier, just run the program:
``` sh
python run_analysis.py
```

This performs the same generation and simulation process, but outputs the results from the plots in the format that the project specification requests (a grouped output of associativities) file that you can view. **I recommend this program for graders or viewers who are not necessarily interested in the arguments or fundamental structure of this project**.

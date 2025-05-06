# --------------------------------------------------------------------------------------------------------------
# Filename:     run_analysis.py
# Author:       Colin Edsall
# Version:      1
# Date:         April 29, 2025
# Description:  Runs the cache simulator and analyzes results of the simulator and the generated files called to
#               NOTE: This specifically does not open a window with the graphs. Refer to documentation in order
#               to identify the path and filenames of the output files.
# --------------------------------------------------------------------------------------------------------------

import subprocess
import matplotlib.pyplot as plt
import numpy as np
from generate_trace import create_block_size_trace, create_associativity_trace

def parse_results(result_file):
    """Parse the results file from the cache simulator."""
    results = []
    try:
        with open(result_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 10:
                    result = {
                        'cache_size': int(parts[0]),
                        'block_size': int(parts[1]),
                        'placement': parts[2],
                        'ways': int(parts[3]),
                        'write_policy': parts[4],
                        'requests': int(parts[5]),
                        'hits': int(parts[6]),
                        'hit_rate': float(parts[7]),
                        'bytes_to_cache': int(parts[8]),
                        'bytes_to_memory': int(parts[9])
                    }
                    result['miss_rate'] = 1.0 - result['hit_rate']

                    results.append(result)
    except Exception as e:
        print(f"Error parsing results: {e}")
    
    return results

def plot_block_size_effect(results, cache_sizes=[1024, 2048, 8192, 65536], placement="DM", write_policy="WB", use_miss_rate=False):
    """Plot the effect of block size on hit rate for a specific configuration."""
    # Create plot
    plt.figure(figsize=(12, 7))
    
    # Define colors and markers for different cache sizes
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'gray']
    markers = ['o', 's', '^', 'D', '*', 'x', '+', 'v']
    
    rate_label = "Miss Rate" if use_miss_rate else "Hit Rate"
    legend_entries = []
    
    # Plot for each cache size
    for i, cache_size in enumerate(cache_sizes):
        # Filter results for the specific configuration
        filtered = [r for r in results if r['cache_size'] == cache_size and 
                                        r['placement'] == placement and 
                                        r['write_policy'] == write_policy]
        
        if not filtered:
            print(f"No data found for cache size {cache_size} bytes")
            continue
            
        # Extract block sizes and hit/miss rates
        block_sizes = [r['block_size'] for r in filtered]
        rates = [r['miss_rate'] if use_miss_rate else r['hit_rate'] for r in filtered]
        
        # Sort by block size
        sorted_data = sorted(zip(block_sizes, rates))
        if sorted_data:  # Check if we have data
            block_sizes_sorted, rates_sorted = zip(*sorted_data)
            
            # Plot this cache size
            color = colors[i % len(colors)]
            marker = markers[i % len(markers)]
            cache_size_label = f"{cache_size//1024}KB" if cache_size >= 1024 else f"{cache_size}B"
            line = plt.plot(block_sizes_sorted, rates_sorted, marker=marker, 
                           linestyle='-', linewidth=2, markersize=8, 
                           color=color, label=f"Cache Size: {cache_size_label}")
            legend_entries.append(line[0])
            
            # Add a polynomial fit to visualize the trend better
            if len(block_sizes_sorted) > 2:
                try:
                    x_smooth = np.logspace(np.log2(min(block_sizes_sorted)), np.log2(max(block_sizes_sorted)), 100, base=2)
                    coeffs = np.polyfit(np.log2(block_sizes_sorted), rates_sorted, 2)
                    poly = np.poly1d(coeffs)
                    y_smooth = poly(np.log2(x_smooth))
                    plt.plot(x_smooth, y_smooth, '--', color=color, linewidth=1, alpha=0.7)
                except:
                    pass
    
    # Finalize the plot
    plt.xscale('log', base=2)
    plt.xlabel("Block Size (Bytes)")
    plt.ylabel(rate_label)
    plt.title(f"Effect of Block Size on {rate_label}\n(Placement: {placement}, Write Policy: {write_policy})")
    plt.grid(True)
    plt.legend()
    
    file_prefix = "miss" if use_miss_rate else "hit"
    filename = f"{file_prefix}_block_size_effect_multi.png"
    plt.savefig(filename)
    plt.show()
    plt.close()
    print(f"Block size effect plot saved to {filename}")

def plot_associativity_effect(results, cache_size=1024, block_size=8, write_policy="WB", use_miss_rate=False):
    """Plot the effect of associativity on hit rate for a specific configuration."""
    # Filter results for the specific configuration
    filtered = [r for r in results if r['cache_size'] == cache_size and 
                                      r['block_size'] == block_size and 
                                      r['write_policy'] == write_policy]
    
    # Extract associativity and hit/miss rates
    placements = []
    rates = []
    for r in filtered:
        placements.append(r['placement'])
        rates.append(r['miss_rate'] if use_miss_rate else r['hit_rate'])
    
    rate_label = "Miss Rate" if use_miss_rate else "Hit Rate"
    
    # Sort by associativity (DM -> 2W -> 4W -> FA)
    placement_order = {"DM": 0, "2W": 1, "4W": 2, "FA": 3}
    sorted_data = sorted(zip(placements, rates), key=lambda x: placement_order[x[0]])
    placements_sorted, rates_sorted = zip(*sorted_data)
    
    # Create plot
    plt.figure(figsize=(10, 6))
    plt.bar(range(len(placements_sorted)), rates_sorted, width=0.6)
    plt.xticks(range(len(placements_sorted)), placements_sorted)
    plt.xlabel("Cache Associativity")
    plt.ylabel(rate_label)
    plt.title(f"Effect of Associativity on {rate_label}\n(Cache Size: {cache_size} bytes, Block Size: {block_size} bytes, Write Policy: {write_policy})")
    plt.grid(True, axis='y')
    
    file_prefix = "miss" if use_miss_rate else "hit"
    filename = f"{file_prefix}_associativity_effect_grouped.png"
    plt.savefig(filename)
    plt.show()
    plt.close()
    print(f"Associativity effect plot saved to {filename}")

def run_simulation(miss=False):
    """Run the cache simulator and analyze results."""
    # Generate trace files
    print("Generating trace files...")
    create_block_size_trace("block.trace")
    create_associativity_trace("associative.trace")
    
    # Begin the simulation of the generated files (not the standard files given in the project files)
    # Run cache simulator on block size trace
    print("Running cache simulator on block.trace...")
    subprocess.run(["python", "cachesim.py", "--trace", "block.trace", "--result", "block.result"])
    
    # Run cache simulator on associativity trace
    print("Running cache simulator on associative.trace...")
    subprocess.run(["python", "cachesim.py", "--trace", "associative.trace", "--result", "associative.result"])
    
    # Now we can do some data analytics: NOTE that this is saved to a file in the repo directory
    # I didn't specify the ability for the user to see it directly during runtime because I figured that anyone
    # using this code will either reference the report with seeded values or know how to read the documentation
    # Parse and plot results
    print("Analyzing block size effect...")
    block_results = parse_results("block.result")
    # Use multiple cache sizes for block size effect
    plot_block_size_effect(block_results, cache_sizes=[1024, 2*1024, 8*1024, 64*1024], use_miss_rate=miss)
    
    print("Analyzing associativity effect...")
    assoc_results = parse_results("associative.result")
    plot_associativity_effect(assoc_results, use_miss_rate=miss)
    
    print("Analysis complete!")

if __name__ == "__main__":
    # On call to main from terminal, just run the above scripts
    import argparse         # Argument parsing/handling
    # https://docs.python.org/3/library/argparse.html
    
    parser = argparse.ArgumentParser(description='Run Simulator Script')
    parser.add_argument('--miss', action='store_true', help='Analyze with miss rate instead of hit rate')

    args = parser.parse_args()

    run_simulation(args.miss)
""" Header ------------------------------------------------------------------------------------------------------
Filename:       cachesim.py
Author:         Colin Edsall
Version:        1
Date:           May 6, 2025
Description:    Cache simulator for different configurations. This completes the project requirements that
                we had to follow in order to show generalized relationships among standard cache setups.
                
                The replacement strategy of this cache is Least Recently Used (LRU)
                The cache is *cold* (empty) to start
                The memory and cache are always consistent in write-through mode (not impactful for this code)

                Cache Sizes:        1K, 2K, 8K, 64K         Bytes
                Block Sizes:        4, 8, 32, 256           Bytes
                Cache Placement:    Direct Mapped (DM), 2-Way Associative (2W), 4-Way Associative (4W),
                                    Fully Associative (FA)

                Write Policy:       Write Back (WB), Write Through (WT)

                Combinatorially, there are 4 \times 4 \times 4 \times 2 = 128 different configurations

                The output configuration is given as rows in a text file with each column equal to:
                1. Cache size
                2. Block size
                3. Cache placement type
                4. Number of blocks within each set
                5. Write policy
                6. Total memory requests (hits + misses)
                7. Total hits
                8. Hit rate
                9. Total bytes (a word is a byte in this sim) transferred from memory to cache
                10. Total bytes transferred from cache to memory

                Refer to README.md for the details about running this program. The basic usage is:
                - Simulates the default .trace file for each configuration and writes the output line to the
                  corresponding .result file.
"""

# Some standard includes so we can do stats and draw graphs, etc.
import numpy as np                          # numpy for math (easiest)
import matplotlib.pyplot as plt             # for plotting graphs, documentation, etc.
plt.interactive(False)                      # Some changes to plotting so we can control its blocking behavior
# import sys                                # For exiting to system as needed (depreciated, we now use command
                                            # -line args)
import subprocess                           # For calling other files
import time                                 # For the runtime (so we know we aren't hanging)

""" Class Definitions -------------------------------------------------------------------------------------------
# - There are several classes that we can use to model the simulation in this project, and to effectively
#   document the datastructure (standard Python list of lists), we will cover them here.
# - Basic initializations will be covered in the class members, with the default being lowest-indexed structs
#   as given in the project specification
"""

class Block:
    # Explicit typecasting here since Python is a funny language
    def __init__(self, size):
        self.size = size
        self.valid = bool(False)            # Dirty/clean bits here
        self.dirty = bool(False)            # Determines if we've done "dirty" store operations
        self.tag = int(0)                   # Tagging here
        self.data = [0] * size                    # Data (initialize as nothing)
        self.last_used = int(0)             # LRU tracking here

class Set:
    def __init__(self, num_ways, block_size):
        self.lines = [Block(block_size) for _ in range(num_ways)]

# Define the main cache class that we want to emulate
class Cache:
    # Define the placement type here
    class PlacementType:
        Direct_Mapped = 0                   # Direct-mapped
        Two_Way = 1                         # Two-way   
        Four_Way = 2                        # Four-way
        Fully_Associative = 3               # Fully-Associative

    class WritePolicy:
        WB = 0                              # Write-back
        WT = 1                              # Write-through 

    """ Main initialization function based on parameters passed in during simulation"""
    # Default to the basic (aka block size 0, this is overwritten in the test cases we write below)
    def __init__(self, cache_size, block_size, write_policy, placement_type):
        # Initialize as empty to start, we're going to have to call to this function repeatedly for all cases
        if block_size == 0:
            raise RuntimeError("Block size must be greater than zero.")
        if cache_size == 0:
            raise RuntimeError("Cache size must be greater than zero.")
        
        # Initialize the data type
        self.cache_size = cache_size
        self.block_size = block_size
        self.placement_type = placement_type
        self.write_policy = write_policy

        
        # Calculate number of sets based on placement type
        # Note that the number of ways determines the number of places that you CAN place a block, not the
        # other methodology for value placement
        if placement_type == self.PlacementType.Direct_Mapped:
            self.num_ways = 1
        elif placement_type == self.PlacementType.Two_Way:
            self.num_ways = 2
        elif placement_type == self.PlacementType.Four_Way:
            self.num_ways = 4
        elif placement_type == self.PlacementType.Fully_Associative:
            # Floor division gives the fully-associative number of ways to place
            self.num_ways = self.cache_size // self.block_size
            self.num_sets = 1             
            # This corresponds to the n ways that we need to address
        else:
            raise RuntimeError("Invalid placement type.")
        
        
        # For all other placements (non-fully-associative), calculate num_sets normally
        # The number of sets corresponds to the number of places that we can put a "set" in, i.e.
        # the valid/dirty bits, tag, and blocks. These are split based on the number of ways
        # i.e. we can have a set with 1, 2, 4, of n sets, of which each set contains its own tag, valid
        # bit, and blocks of data
        self.num_blocks = self.cache_size // self.block_size
        self.num_sets = self.num_blocks // self.num_ways
        self.offset_bits = int(np.log2(self.block_size))
        self.set_bits = 0 if self.placement_type == self.PlacementType.Fully_Associative else int(np.log2(self.num_sets))
        self.tag_shift = self.offset_bits + self.set_bits

        # Data structure is a list of Sets, configured based on the number of ways to arrange the sets, and
        # the number of sets (calculated above)
        # Initialize the sets: list of sets, each set is a list of blocks (ways)
        self.sets = [Set(self.num_ways, block_size) for _ in range(self.num_sets)]
        
        # Statistics:
        # These will be changed later to reflect the data that we need to report, in essence this is just a stat
        # tracker
        self.total_requests = int(0)
        self.total_hits = int(0)
        self.bytes_to_cache = int(0)
        self.bytes_to_memory = int(0)
        self.access_count = int(0)
    
        # print(f"Cache Size: {self.cache_size}, Block Size: {self.block_size}")
        # print(f"Num Blocks: {self.num_blocks}, Num Sets: {self.num_sets}, Num Ways: {self.num_ways}")
        # print(f"Offset Bits: {self.offset_bits}, Set Bits: {self.set_bits}, Tag Shift: {self.tag_shift}")

    """Helper functions for grabbing specific values"""
    # Returns the tag of the block based on the possible block indexes, this is defined as the value of the
    # tag that leads to the several blocks within the tag, of which contain several sets
    # Dr. Ransbottom recommends that we typecast as integers because Python is a funny language
    
    # Getter functions that we need to use for the outputs of load/store
    def get_tag(self, address):
        # Return the tag bit offset, based on the shift calculated in initialization
        # This is FAR easier than any of the stuff I've tried before, since in reality we're just
        # dealing with an array...
        return address >> self.tag_shift

    def get_block_index(self, address):
        # Fully associative caches have no set index
        if self.placement_type == self.PlacementType.Fully_Associative:
            return 0
        return (address >> self.offset_bits) & ((1 << self.set_bits) - 1)
    
    def get_block_offset(self, address):
        # Extract block offset from address
        return int(address & self.block_size - 1)

    """Read and Write functions: these iterate over all the cache to find if a hit exists, then does specific
    actions for each..."""
    # Read is a complex function that checks if we have a hit in memory, and that the block we're trying to 
    # read is valid or not, and then acts based on that (if we need to access main memory or we can stay in cache)
    def read(self, address):
        self.total_requests += 1                                # Data collection for hitrate
        set_index = self.get_block_index(address)               # Grab index
        tag = self.get_tag(address)                             # Grab the tag (comparison)
        hit = False                                             # Initialize hit flag
        replace_index = None                                    # Initialize replace_index for printing
        
        # Check if we have a hit
        set = self.sets[set_index]                              # Since we have to check if we actually
        for i, block in enumerate(set.lines):
            if block.valid and block.tag == tag:                # have a hit, we just iterate over all
                # Cache hit                                     # Values in the cache (kinda slow)
                self.total_hits += 1
                self.access_count += 1
                block.last_used = self.access_count
                hit = True
                # print(f"Accessing address: {address:#010x}")
                # print(f"Set Index: {set_index}, Tag: {tag}")
                # print(f"Hit: {hit}, Evicted Block: {replace_index if not hit else 'None'}")
                return True
        
        # If we can't find the value in the cache, we have a miss (SLOW)
        # Cache miss: need to load from memory
        self.bytes_to_cache += self.block_size                  # Not sure if the spec is wrong, but
                                                                # the sample output is in a non-standard
                                                                # byte format. Nonetheless we assume
                                                                # a miss causes all values of the read
                                                                # to have to come from main memory
        
        # Find block to replace (LRU)
        replace_index = self.find_lru_block(set_index)
        
        # If dirty block is being replaced in write-back mode, write it to memory
        if self.write_policy == self.WritePolicy.WB and self.sets[set_index].lines[replace_index].valid and self.sets[set_index].lines[replace_index].dirty:
            self.bytes_to_memory += self.block_size
        
        # Update block values
        self.sets[set_index].lines[replace_index].valid = True
        self.sets[set_index].lines[replace_index].dirty = False
        self.sets[set_index].lines[replace_index].tag = tag
        self.access_count += 1
        self.sets[set_index].lines[replace_index].last_used = self.access_count
        
        # print(f"Accessing address: {address:#010x}")
        # print(f"Set Index: {set_index}, Tag: {tag}")
        # print(f"Hit: {hit}, Evicted Block: {replace_index if not hit else 'None'}")

        # If we have a miss, return false :( (this is defined as "expensive" - Dr. Ransbottom)
        return False

    # Write checks if we have a hit and then determines where it needs to grab the value from
    def write(self, address):
        self.total_requests += 1                                            # Data collection
        set_index = self.get_block_index(address)                           # Grab index (iteration)
        tag = self.get_tag(address)                                         # Grab the tag (comparison)
        
        # Check if we have a hit, then we can write
        hit = False                                                     # By default, hit is false (assume good)
        set = self.sets[set_index]                                      # Since we have to check if we actually
        for block in set.lines:
            if block.valid and block.tag == tag:
                # Cache hit
                self.total_hits += 1
                hit = True
                self.access_count += 1
                block.last_used = self.access_count
                
                if self.write_policy == self.WritePolicy.WB:
                    # In write-back, just mark as dirty
                    block.dirty = True
                else:  # Write-through
                    # Write to memory immediately
                    self.bytes_to_memory += 4
                
                break   # Go to writing the value in the cache (we don't actually need to grab/use it, so just)
                        # mark as a hit and add the bits if not (aka we mark as dirty and continue)
        
        # We have a miss, and we need to grab the address to write from in memory (SLOW)
        if not hit:
            # Cache miss - need to load from memory
            self.bytes_to_cache += self.block_size
            
            # Method to replace the block, LRU, not random since that would be fun-er
            replace_index = self.find_lru_block(set_index)
            
            # If dirty block is being replaced in write-back mode, write it to memory
            if self.write_policy == self.WritePolicy.WB and self.sets[set_index].lines[replace_index].valid and self.sets[set_index].lines[replace_index].dirty:
                self.bytes_to_memory += self.block_size
            
            # Update block contents as valid (don't actually store anything here)
            self.sets[set_index].lines[replace_index].valid = True
            self.sets[set_index].lines[replace_index].tag = tag
            self.access_count += 1
            self.sets[set_index].lines[replace_index].last_used = self.access_count
            
            if self.write_policy == self.WritePolicy.WB:
                # Mark as dirty in write-back mode
                self.sets[set_index].lines[replace_index].dirty = True    # Need to clear it (not covered)
            else:  # Write-through
                # Write to memory immediately
                self.bytes_to_memory += 4                                 # We can only write 4 bytes at a time
                self.sets[set_index].lines[replace_index].dirty = False   # Can't be dirty if it wasn't written
        
        return hit
            
    """A basic function to determine the last/least used block to replace"""
    def find_lru_block(self, set_index):
        # Find least recently used block in the set
        min_used = float('inf')
        min_index = 0
        
        for i, block in enumerate(self.sets[set_index].lines):
            if not block.valid:
                # If we find an invalid block, use it immediately :)
                return i
            
            if block.last_used < min_used:      # Keep iterating until we find the right one
                min_used = block.last_used
                min_index = i
        
        return min_index                        # Returns the key (index) that we can use in the datastructure
    
    """Some statistical functions for getting data for graphs, etc."""
    def get_hit_rate(self):
        if self.total_requests == 0:
            return 0
        return float(self.total_hits / self.total_requests)
    
    def get_placement_str(self):
        if self.placement_type == self.PlacementType.Direct_Mapped:
            return "DM"
        elif self.placement_type == self.PlacementType.Two_Way:
            return "2W"
        elif self.placement_type == self.PlacementType.Four_Way:
            return "4W"
        else:
            return "FA"
    
    def get_write_policy_str(self):
        return "WB" if self.write_policy == self.WritePolicy.WB else "WT"
    
    """This function was annoying to write but it just concatenates the results into a string for storage"""
    def get_result_str(self):
        # Format: cache_size block_size placement_type num_ways write_policy total_requests hits hit_rate bytes_to_cache bytes_to_memory
        # print(f"{self.cache_size} {self.block_size} {self.get_placement_str()} {self.num_ways} {self.get_write_policy_str()} {self.total_requests} {self.total_hits} {self.get_hit_rate():.2f} {self.bytes_to_cache} {self.bytes_to_memory}")
        return f"{self.cache_size} {self.block_size} {self.get_placement_str()} {self.num_ways} {self.get_write_policy_str()} {self.total_requests} {self.total_hits} {self.get_hit_rate():.2f} {self.bytes_to_cache} {self.bytes_to_memory}"
            
""" Helper Functions --------------------------------------------------------------------------------------------
, These are used in the actual simulation... see main for usage and/or the documentation"""
def read_trace_file(filename):
    operations = []                                                     # Store the operations
    try:
        with open(filename, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2:
                    op_type = parts[0]                                  # "read" or "write"
                    address = int(parts[1], 16)                         # Convert hex to int (should be done, but yk)
                    operations.append((op_type, address))
                    # print(op_type)

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    
    return operations                                                   # Returns the list of operations


def simulate_trace(trace_file, output_file):
    # Cache sizes in bytes
    cache_sizes = [1024, 2048, 8192, 65536]                             # 1K, 2K, 8K, 64K
    
    # Block sizes in bytes
    block_sizes = [4, 8, 32, 256]                                    # No 16, so this is tough...

    # Placement types
    placement_types = [
        Cache.PlacementType.Direct_Mapped,
        Cache.PlacementType.Two_Way,
        Cache.PlacementType.Four_Way,
        Cache.PlacementType.Fully_Associative
    ]
    
    # Write policies
    write_policies = [
        Cache.WritePolicy.WB,  # Write-back
        Cache.WritePolicy.WT   # Write-through
    ]
    
    # Read trace file
    operations = read_trace_file(trace_file)                            # Calls to above and will need for results
    results = []
    
    # Simulate all configurations from the structs above
    for cache_size in cache_sizes:
        for block_size in block_sizes:
            for placement in placement_types:
                for write_policy in write_policies:
                    # Initialize cache
                    try:
                        # self, cache_size, block_size, write_policy, placement_type):
                        cache = Cache(cache_size, block_size, write_policy, placement)
                    except RuntimeError as e:   # This should not be called to, only if we really screw up above
                        print(f"Skipping invalid configuration: {cache_size} {block_size} {placement} {write_policy} - {e}")
                        continue
                    
                    # Process trace, note we infer that the op type is first, then address (i.e. read 0x00000)
                    for op_type, address in operations:
                        if op_type.lower() == "read" or op_type.lower() == "load":
                            
                            cache.read(address)
                            # print(f"HITS: {cache.total_hits}")
                        elif op_type.lower() == "write" or op_type.lower() == "store":
                            cache.write(address)
                    
                    # Record result
                    results.append(cache.get_result_str())
                    
    # Write results to output file
    with open(output_file, 'w') as f:
        for result in results:
            f.write(result + '\n')


def analyze_block_size_effect(result_file, cache_size, placement, write_policy, miss):
    """
    Analyzes the effect of block size on hit rate for a specific cache configuration
    and produces a plot.
    """
    block_sizes = []
    hit_rates = []
    
    try:
        with open(result_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 8:
                    continue
                
                # Parse the line
                cs = int(parts[0])          # Cache size
                bs = int(parts[1])          # Block size
                pt = parts[2]               # Placement type (DM, 2W, 4W, FA)
                wp = parts[4]               # Write policy (WB, WT)

                if not miss:
                    hit_rate = float(parts[7])  # Hit rate
                else:
                    hit_rate = float(1.0 - float(parts[7]))   # Miss rate (I know it's called hit_rate)


                # Filter for the configuration we want
                if (cs == cache_size and 
                    ((pt == "DM" and placement == Cache.PlacementType.Direct_Mapped) or
                     (pt == "2W" and placement == Cache.PlacementType.Two_Way) or 
                     (pt == "4W" and placement == Cache.PlacementType.Four_Way) or
                     (pt == "FA" and placement == Cache.PlacementType.Fully_Associative)) and
                    ((wp == "WB" and write_policy == Cache.WritePolicy.WB) or
                     (wp == "WT" and write_policy == Cache.WritePolicy.WT))):
                    
                    block_sizes.append(bs)
                    hit_rates.append(hit_rate)
    
    except FileNotFoundError:
        print(f"Error: File '{result_file}' not found.")
        return
    
    if not block_sizes:
        print("No matching data found for the specified configuration.")
        return
    
    # Sort the data by block size
    sorted_data = sorted(zip(block_sizes, hit_rates))
    block_sizes_sorted, hit_rates_sorted = zip(*sorted_data)
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(block_sizes_sorted, hit_rates_sorted, 'o-', linewidth=2, markersize=10)
    plt.xscale('log', base=2)  # Log scale is helpful for block sizes
    if not miss:
        plt.ylabel("Hit Rate")
        plt.title(f"Effect of Block Size on Hit Rate\nCache Size: {cache_size} bytes, Placement: {pt}, Write Policy: {wp}")
    else:
        plt.ylabel("Miss Rate")
        plt.title(f"Effect of Block Size on Miss Rate\nCache Size: {cache_size} bytes, Placement: {pt}, Write Policy: {wp}")
    
    plt.xlabel("Block Size (Bytes)")
    plt.grid(True)
    plt.tight_layout()
    
    # Add best fit polynomial to visualize the curve better, since we understand that the reason behind performance
    # increases is not linear, it's actually kinda like a bowl (the slides gave us this shape), so, since we are limited
    # to just FOUR block sizes, let's *assume* that the nature of this is polynomial, which this plot logic does
    if len(block_sizes_sorted) > 2: # Can only do polynomial for block sizes greather than 2 (it would be a line if not...)
        try:
            # Fit a 2nd-degree polynomial to show the bowl shape if it exists
            x_smooth = np.logspace(np.log2(min(block_sizes_sorted)), np.log2(max(block_sizes_sorted)), 100, base=2)
            coeffs = np.polyfit(np.log2(block_sizes_sorted), hit_rates_sorted, 2)
            poly = np.poly1d(coeffs)
            y_smooth = poly(np.log2(x_smooth))
            plt.plot(x_smooth, y_smooth, '--', color='red', linewidth=1.5, label='Polynomial Fit')
            plt.legend()
        except:
            pass  # Skip the curve fitting if there's an error, but this won't happen :)
                  # thank the lord we don't have coverage tests
    
    plt.savefig("block_size_effect.png")
    plt.show()
    
    return block_sizes_sorted, hit_rates_sorted


def analyze_associativity_effect(result_file, cache_size=1024, block_size=8, write_policy=Cache.WritePolicy.WB, miss=False):
    """
    Analyzes the effect of associativity on hit rate for a specific cache configuration
    and produces a plot.
    """
    associativity = []  # Will store as number of ways (1, 2, 4, etc.)
    hit_rates = []
    
    try:
        with open(result_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 8:
                    continue
                
                # Parse the line
                cs = int(parts[0])          # Cache size
                bs = int(parts[1])          # Block size
                pt = parts[2]               # Placement type (DM, 2W, 4W, FA)
                nw = int(parts[3])          # Number of ways (blocks)
                wp = parts[4]               # Write policy (WB, WT)
                requests = int(parts[5])         # Total number of memory requests
                hits = int(parts[6])  # Hits

                # Configure hitrate (cast as float)
                if not miss:
                    hit_rate = float(hits / requests)
                else:
                    hit_rate = float(1 - (hits / requests))
                
                # Filter for the configuration we want
                if (((wp == "WB" and write_policy == Cache.WritePolicy.WB) or
                     (wp == "WT" and write_policy == Cache.WritePolicy.WT))):
                    
                    associativity.append(nw)
                    hit_rates.append(hit_rate)
    
    except FileNotFoundError:
        print(f"Error: File '{result_file}' not found.")
        return
    
    if not associativity:
        print("No matching data found for the specified configuration.")
        return
    
    # print(f"Parsed line: {parts}")
    # print(f"Filtering: cs={cs}, bs={bs}, pt={pt}, nw={nw}, wp={wp}, requests={requests}, hits={hits}, hit_rate={hit_rate}")
    # print(f"Associativity: {associativity}")
    # print(f"Hit Rates: {hit_rates}")
    
    # Group hit rates by associativity level
    from collections import defaultdict

    # Aggregate hit rates for each associativity level
    aggregated_hit_rates = defaultdict(list)
    for assoc, hit_rate in zip(associativity, hit_rates):
        aggregated_hit_rates[assoc].append(hit_rate)

    # Calculate the average hit rate for each associativity level
    grouped_associativity = []
    grouped_hit_rates = []
    for assoc, rates in aggregated_hit_rates.items():
        grouped_associativity.append(assoc)
        grouped_hit_rates.append(sum(rates) / len(rates))  # Average hit rate

    # Sort the grouped data by associativity
    sorted_data = sorted(zip(grouped_associativity, grouped_hit_rates))
    grouped_associativity_sorted, grouped_hit_rates_sorted = zip(*sorted_data)

    # Create associativity labels
    assoc_labels = [f"{a}W" if a != 1 else "DM" for a in grouped_associativity_sorted]

    # Create the bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(range(len(grouped_associativity_sorted)), grouped_hit_rates_sorted, color='skyblue', edgecolor='black')
    plt.xticks(range(len(grouped_associativity_sorted)), assoc_labels, rotation=45)
    plt.xlabel("Associativity")
    if not miss:
        plt.ylabel("Average Hit Rate")
        plt.title("Effect of Associativity on Hit Rate")
    else:
        plt.ylabel("Average Miss Rate")
        plt.title("Effect of Associativity on Miss Rate")
        
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("associativity_effect.png")         # This is different than the run_analysis.py for the report
    plt.show()
    
    return grouped_associativity_sorted, grouped_hit_rates_sorted


""" Main --------------------------------------------------------------------------------------------------------
This is the main execution, for which we want to add some arguments for ease of use in the terminal"""
if __name__ == "__main__":
    import argparse         # Argument parsing/handling
    # https://docs.python.org/3/library/argparse.html
    
    parser = argparse.ArgumentParser(description='Cache Simulator')
    parser.add_argument('--trace', default='test.trace', help='Input trace file')
    parser.add_argument('--result', default='test.result', help='Output result file')
    parser.add_argument('--generate', action='store_true', help='Generate block and associativity trace files')
    parser.add_argument('--analyze', action='store_true', help='Analyze and plot results')
    parser.add_argument('--miss', action='store_true', help='Analyze with miss rate')
    parser.add_argument('--size', type=int, default=1024, help='Set the cache size (default 1KB)')
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    # Generate trace files if requested
    if args.generate:
        # This has been outsourced from a previous function to create a better trace file for each
        # case that we want to cover. See generate_trace.py
        subprocess.run(["python", "generate_trace.py"])
    
    # Run the simulation, depending on argument
    print(f"Running simulation with trace file {args.trace}...")
    simulate_trace(args.trace, args.result)
    print(f"Simulation complete. Results saved to {args.result}")

    print("Simulation time: %s seconds" % np.round((time.time() - start_time), decimals=4))


    # Analyze results if requested
    if args.analyze:
        print("Analyzing block size effect...")
        analyze_block_size_effect(args.result, cache_size=args.size, 
                                  placement=Cache.PlacementType.Direct_Mapped, 
                                  write_policy=Cache.WritePolicy.WB,
                                  miss=args.miss)
        
        print("Analyzing associativity effect...")
        analyze_associativity_effect(args.result, cache_size=args.size, 
                                     block_size=4, 
                                     write_policy=Cache.WritePolicy.WB,
                                     miss=args.miss)
        
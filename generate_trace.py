# --------------------------------------------------------------------------------------------------------------
# Filename:     generate_trace.py
# Author:       Colin Edsall
# Version:      1
# Date:         April 29, 2025
# Description:  Generates trace files to demonstrate block size effects, depending on several cases from our
#               lecture notes and the structure/locality impact of the trace.
#               NOTE: as a lesson to anyone writing code like this, please do not think bugs are not your fault, 
#               I've spent easily 4 hours trying to create traces that work with this configuration just to 
#               realize that words are fixed at 4 bytes and not variable...
#               Set index is very important, and I failed to realize this at 2 am
# --------------------------------------------------------------------------------------------------------------

import numpy as np

"""Generate the sample associativity relationship trace that the project spec wants."""
def create_associativity_trace(filename="associative.trace"):
    with open(filename, 'w') as f:
        # Calculate parameters for a 1KB cache with 8-byte blocks (the chosen setup for this trace)
        cache_size = 1024
        block_size = 8
        total_blocks = cache_size // block_size  # 128 blocks
        
        # Phase 1: Create conflict misses for direct-mapped cache, since we want to show an INCREASE
        # in hit rate for increased associativity.
        for i in range(50):
            for way in range(4):
                addr = (way * total_blocks + (i % 16)) * block_size
                f.write(f"read {addr:08x}\n")
        
        # Phase 2: Working set with high temporal locality but poor spatial locality
        for i in range(50):
            way = i % 4
            set_index = (i // 4) % 32  # 32 different sets
            addr = (way * total_blocks + set_index) * block_size
            f.write(f"read {addr:08x}\n")
            
        # Phase 3: Alternating access to conflicting addresses
        for i in range(50):
            ways = [0, 1] if i % 2 == 0 else [2, 3]
            for way in ways:
                set_index = i % 32
                addr = (way * total_blocks + set_index) * block_size
                f.write(f"read {addr:08x}\n")
        
        # Phase 4: Add some write operations since we should cover those too
        for i in range(50):
            way = i % 4
            set_index = i % 16
            addr = (way * total_blocks + set_index) * block_size
            f.write(f"write {addr:08x}\n")

"""Generate a block trace that creates the "bowl" shape we wanted from the report."""
def create_block_size_trace(filename="block.trace"):
    with open(filename, 'w') as f:
        # Phase 1: Good spatial locality for small blocks (i.e. 4 and 8)
        for base in range(0, 60, 8):                    # Addresses are 8 bytes apart
            for offset in range(0, 8, 4):               # Offset in the range of 0-8 bytes
                addr = base + offset
                f.write(f"read {addr:08x}\n")
        
        # Phase 2: High temporal locality but poor spatial locality
        # This pattern benefits small blocks since large blocks waste space in this case (stride, working set)
        for i in range(50):
            # Create a working set with specific strides that benefit small blocks
            addr = (i % 16) * 2 + ((i // 32) % 32) * 512
            f.write(f"read {addr:08x}\n")
            
        # Phase 3: Create a lot of conflicts for large blocks due to mapping to same set
        for i in range(10):
            # Create a pattern that maps to the same set for larger blocks
            set_index = i % 4  # Only 2 sets, increasing conflicts for larger blocks
            addr = set_index * 512 + (i % 64) * 512     # Large stride to create cache pollution
            f.write(f"read {addr:08x}\n")

        # Phase 4: Access pattern with changing set indices for smaller block sizes
        block_size = 32
        for i in range(30):
            addr = i * block_size * 129  # Spread accesses across different sets
            f.write(f"load {addr:08x}\n")
        
        # Phase 5: Repeat the same addresses to demonstrate hits for smaller blocks
        # use write instead of load, though it really doesn't matter in this case
        for i in range(30):
            addr = i * block_size * 129
            f.write(f"store {addr:08x}\n")

"""Define the main sequence when calling to this program via terminal."""
if __name__ == "__main__":
    print("Generating block.trace...")
    create_block_size_trace("block.trace")
    print("Generating associative.trace...")
    create_associativity_trace("associative.trace")
    print("Done! File generation complete.")

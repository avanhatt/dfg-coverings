#include <stdio.h>

// Global count variables, atomic to support multithreaded code
_Atomic long MatchedInstructions = 0;
_Atomic long TotalInstructions = 0;

// To be called per basic block
void incremementCounts(int Matched, int Total) {
  MatchedInstructions += Matched;
  TotalInstructions += Total;
}

// To be called once, on module end
void printDynamicProfiling() {
    printf("%ld/%ld (%.2f %%) dynamic instructions matched\n",
       MatchedInstructions,
    TotalInstructions,
    (float)MatchedInstructions/TotalInstructions*100);
}

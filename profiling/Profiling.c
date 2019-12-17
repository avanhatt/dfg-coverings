// #include "llvm/Support/FormatVariadic.h"

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
  // std::string S = llvm::formatv("{0}/{1}({2:P}) dynamic instructions matched\n",
  //   MatchedInstructions,
  //   TotalInstructions,
  //   (float)MatchedInstructions/TotalInstructions);
  // printf("%s\n", S.c_str());

    printf("%ld/%ld (%.2f) dynamic instructions matched\n", MatchedInstructions,
    TotalInstructions,
    (float)MatchedInstructions/TotalInstructions*100);
}

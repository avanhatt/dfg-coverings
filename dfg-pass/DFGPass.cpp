#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Analysis/LoopPass.h"
#include "llvm/Analysis/IVUsers.h"
#include "llvm/Pass.h"
#include "llvm/IR/Function.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/Transforms/Utils.h"
#include "llvm/Transforms/Utils/Mem2Reg.h"
#include "llvm/Support/CommandLine.h"
#include <fstream>
#include <sstream>

using namespace llvm;
using namespace std;

namespace {

  // -info is a command line argument to opt
  static cl::opt<string> InfoFilename(
    "info", // Name of command line arg
    cl::desc("Specify the filename to write the info to"), // -help text
    cl::init("info.json") // Default value
  );

  struct DFGPass : public FunctionPass {
    static char ID;
    DFGPass() : FunctionPass(ID) { }

    ~DFGPass() {
    }

    void getAnalysisUsage(AnalysisUsage &AU) const {
    }

    virtual bool runOnFunction(Function &F) {
      return false;
    }
  };
}

char DFGPass::ID = 0;

// Register the pass so `opt -loop-perf` runs it.
static RegisterPass<DFGPass> Y("dfg-pass", "Data flow graph construction pass");

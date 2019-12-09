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
#include "json.hpp"
#include <fstream>
#include <sstream>

using namespace llvm;
using namespace std;
using namespace nlohmann;

namespace {

  // -info is a command line argument to opt
  static cl::opt<string> OutputFilename(
    "json-output", // Name of command line arg
    cl::desc("Specify the filename to write the graph to"), // -help text
    cl::init("info.json") // Default value
  );

  struct DFGPass : public FunctionPass {
    static char ID;
    json DestinationToOperands;
    DFGPass() : FunctionPass(ID) { }

    ~DFGPass() {
      std::ofstream JsonFile;
      JsonFile.open(OutputFilename);
      JsonFile << DestinationToOperands.dump(4) << "\n";
      JsonFile.close();
    }

    void getAnalysisUsage(AnalysisUsage &AU) const {
    }

    std::string stringifyText(Instruction &I) {
      std::string InstrString;
      raw_string_ostream InstrStream(InstrString);
      InstrStream << I;
      return InstrStream.str();
    }

    std::string stringifyPtr(Instruction &I) {
      std::string InstrPtrString;
      raw_string_ostream InstrPtrStream(InstrPtrString);
      InstrPtrStream << &I;
      return InstrPtrStream.str();
    }

    std::string stringifyType(Type *T) {
      std::string TypeString;
      raw_string_ostream TypeStream(TypeString);
      TypeStream << *T;
      return TypeStream.str();
    }

    virtual bool runOnFunction(Function &F) {
      for (auto &B : F) {
        for (auto &I : B) {
          // add instruction (identified by pointer) to the json
          json InstrJson;
          InstrJson["pointer"] = stringifyPtr(I);
          InstrJson["text"] = stringifyText(I);
          InstrJson["opcode"] = I.getOpcodeName();
          InstrJson["type"] = stringifyType(I.getType());
          InstrJson["operands"] = {};

          for (auto &Op : I.operands()) {
            json OpJson;
            // only record the operand if it is a constant int
            // or the destination of a previous instruction
            if (llvm::ConstantInt* OpConstant = dyn_cast<llvm::ConstantInt>(Op)) {
              OpJson["instr_or_constant"] = "constant";
              OpJson["type"] = stringifyType(Op->getType());
              OpJson["value"] = OpConstant->getValue().getSExtValue();
            // // Floating point is untested:
            // } else if (llvm::ConstantFP* OpFloat = dyn_cast<llvm::ConstantFP>(Op)) {
            //   errs() << "Constant\n";
            //   OpJson["instr_or_constant"] = "constant";
            //   OpJson["type"] = stringifyType(Op->getType());
            //   OpJson["value"] = OpFloat->getValueAPF().convertToFloat();
            } else if (llvm::Instruction* OpInstruction = dyn_cast<llvm::Instruction>(Op)) {
              OpJson["instr_or_constant"] = "instruction";
              OpJson["type"] = stringifyType(Op->getType());
              OpJson["value"] = stringifyPtr(*OpInstruction);
            }

            if (OpJson != nullptr) {
              (InstrJson["operands"]).push_back(OpJson);
            }
          }
          DestinationToOperands.push_back(InstrJson);
        }
      }
      return false;
    }
  };
}

char DFGPass::ID = 0;

// Register the pass so `opt -loop-perf` runs it.
static RegisterPass<DFGPass> Y("dfg-pass", "Data flow graph construction pass");







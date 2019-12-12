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

    // -blocks is a command line argument to opt
  static cl::opt<bool> PerBasicBlock(
    "blocks", // Name of command line arg
    cl::desc("Specify whether to output subgraphs per basic block"), // -help
    // text
    cl::init(true) // Default value
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

    std::string stringifyValue(Value &V) {
      std::string ValueString;
      raw_string_ostream ValueStream(ValueString);
      ValueStream << V;
      return ValueStream.str();
    }

    std::string stringifyPtr(Value &V) {
      std::string PtrString;
      raw_string_ostream PtrStream(PtrString);
      PtrStream << &V;
      return PtrStream.str();
    }

    std::string stringifyType(Type *T) {
      std::string TypeString;
      raw_string_ostream TypeStream(TypeString);
      TypeStream << *T;
      return TypeStream.str();
    }

    bool skipInstruction(Instruction &I) {
      // Skip unreachable
      if (isa<UnreachableInst>(I)) return true;

      // Skip unconditional voids
      if (BranchInst *Br = dyn_cast<BranchInst>(&I)) {
        if (Br->isUnconditional()) return true;
      }

      // Skip void returns
      if (ReturnInst *Ret = dyn_cast<ReturnInst>(&I)) {
        if (Ret->getNumOperands() == 0) return true;
      }

      return false;
    }

    bool skipOperand(Value *Op) {
      // Skip labels (which can be operands to branch instructions)
      if (isa<BasicBlock>(Op)) return true;

      return false;
    }

    virtual bool runOnFunction(Function &F) {
      int blockI = 0;
      for (auto &B : F) {
        for (auto &I : B) {

          // Skip instructions without dependencies or side effects
          if (skipInstruction(I)) continue;

          // add instruction (identified by pointer) to the json
          json InstrJson;
          InstrJson["pointer"] = stringifyPtr(I);
          InstrJson["text"] = stringifyValue(I);
          InstrJson["opcode"] = I.getOpcodeName();
          InstrJson["type"] = stringifyType(I.getType());
          InstrJson["operands"] = {};

          for (auto &Op : I.operands()) {
            if (skipOperand(Op)) continue;

            json OpJson;
            if (Instruction *OpInstruction = dyn_cast<Instruction> (Op)) {
              // If in basic block mode, handle instructions from different
              // blocks
              if (PerBasicBlock && (OpInstruction->getParent() != I.getParent())) {
                errs() << "Different parents " << *OpInstruction << I << "\n";
                OpJson["description"] = "instruction-external";
                OpJson["type"] = stringifyType(Op->getType());
                OpJson["value"] = stringifyPtr(*OpInstruction);
              } else {
                OpJson["description"] = "instruction";
                OpJson["type"] = stringifyType(Op->getType());
                OpJson["value"] = stringifyPtr(*OpInstruction);
              }
            } else if (ConstantInt *OpConstant = dyn_cast<ConstantInt>(Op)) {
              OpJson["description"] = "constant";
              OpJson["type"] = stringifyType(Op->getType());
              OpJson["value"] = OpConstant->getValue().getSExtValue();
            } else if (ConstantFP *OpFloat = dyn_cast<ConstantFP>(Op)) {
              OpJson["description"] = "constant";
              OpJson["type"] = stringifyType(Op->getType());
              OpJson["value"] = OpFloat->getValueAPF().convertToDouble();
            } else if (Argument *OpArgument = dyn_cast<Argument>(Op)) {
              OpJson["description"] = "argument";
              OpJson["type"] = stringifyType(Op->getType());
              OpJson["value"] = stringifyPtr(*OpArgument);
              OpJson["argument_number_in_function"] = OpArgument->getArgNo();
            } else if (DerivedUser *OpDerivedUser = dyn_cast<DerivedUser>(Op)) {
              // all pointer operands seem to be of DerivedUser type
              if (PointerType *t = dyn_cast<PointerType>(Op->getType())) {
                OpJson["description"] = "pointer";
                OpJson["type"] = stringifyType(Op->getType());
                OpJson["value"] = stringifyPtr(*OpDerivedUser);
              } else if (UndefValue *Und = dyn_cast<UndefValue>(Op)) {
                errs() << "Skipping UndefValue\n";
                continue;
              }
            } else {
              errs() << "Unhandled operand of type: " << stringifyType(Op->getType()) << "\n";
              // errs() << *Op << "\n";
              continue;
            }

            (InstrJson["operands"]).push_back(OpJson);
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







#include "json.hpp"
#include "llvm/Analysis/IVUsers.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Pass.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/FormatVariadic.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#include "llvm/Transforms/Utils.h"
#include "llvm/Transforms/Utils/Mem2Reg.h"

#include <fstream>
#include <sstream>
#include <stdio.h>
#include <stdlib.h>

using namespace llvm;
using namespace nlohmann; // For JSON processing
using namespace std;

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

  // -interactive is a command line argument to opt
  static cl::opt<bool> IsInteractive(
    "interactive", // Name of command line arg
    cl::desc("Specify whether to pause for input in the python program"), // -help
    // text
    cl::init(false) // Default value
  );

  struct DFGPass : public ModulePass {
    static char ID;
    json DestinationToOperands;
    int TotalInstructions = 0;
    int InstructionsMatched = 0;
    DFGPass() : ModulePass(ID) { }

    ~DFGPass() {}

    void getAnalysisUsage(AnalysisUsage &AU) const {
    }

    string stringifyValue(Value &V) {
      string ValueString;
      raw_string_ostream ValueStream(ValueString);
      ValueStream << V;
      return ValueStream.str();
    }

    string stringifyPtr(Value &V) {
      string PtrString;
      raw_string_ostream PtrStream(PtrString);
      PtrStream << &V;
      return PtrStream.str();
    }

    string stringifyType(Type *T) {
      string TypeString;
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

      // For now, skip Phi nodes
      if (isa<PHINode>(I)) return true;

      return false;
    }

    bool skipOperand(Value *Op) {
      // Skip labels (which can be operands to branch instructions)
      if (isa<BasicBlock>(Op)) return true;

      return false;
    }

    json jsonPerOperand(Value *Op, Instruction &I) {
      json OpJson;
      if (Instruction *OpInstruction = dyn_cast<Instruction>(Op)) {
        // If in basic block mode, handle instructions from different
        // blocks and from Phi nodes
        if (PerBasicBlock && (OpInstruction->getParent() != I.getParent()
          || isa<PHINode>(Op))) {
          //errs() << "Different parents " << *OpInstruction << I << "\n";
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
        }
      } else {
        errs() << "Unhandled operand of type: " << stringifyType(Op->getType())
          << "\n";
        // errs() << *Op << "\n";
      }
      return OpJson;
    }

    virtual bool runOnModule(Module &M) {

      for (auto &F : M) {
        dfgPerFunction(F);
      }

      writeOutJsonDFG();
      //string
      string CallPython = "python3 dfg.py " + (string)(IsInteractive ? "-i " : "") + "--input " + OutputFilename;
      system(CallPython.c_str());

      json MatchesJson = readInJsonMatches();

      auto PerInstruction = jsonToInstructionMatches(MatchesJson);

      for (auto &F : M) {
        annotateMatchesPerFunction(PerInstruction, F);
      }


      auto S = formatv("({0:P})", (float)InstructionsMatched/TotalInstructions);
      errs() << InstructionsMatched << "/" << TotalInstructions << " " << S <<
        " instructions matched\n";

      return true;
    }

    void writeOutJsonDFG() {
      ofstream JsonFile;
      JsonFile.open(OutputFilename);
      JsonFile << DestinationToOperands.dump(4) << "\n";
      JsonFile.close();
    }

    json readInJsonMatches() {
      ifstream JsonFile;
      stringstream Buffer;

      size_t Pos = OutputFilename.find(".json");
      if (Pos == string::npos) {
        errs() << "Expected output filename to include .json suffix\n";
        exit(1);
      }
      string MatchesFilename = OutputFilename.replace(Pos, OutputFilename.length(),
        "-matches.json");

      JsonFile.open(MatchesFilename);
      Buffer << JsonFile.rdbuf();
      JsonFile.close();
      return json::parse(Buffer.str());
    }

    void dfgPerFunction(Function &F) {
      for (auto &B : F) {
        for (auto &I : B) {

          TotalInstructions++;

          // Skip instructions without dependencies or side effects
          if (skipInstruction(I)) continue;

          // Add instruction (identified by pointer) to the json
          json InstrJson;
          InstrJson["pointer"] = stringifyPtr(I);
          InstrJson["text"] = stringifyValue(I);
          InstrJson["opcode"] = I.getOpcodeName();
          InstrJson["type"] = stringifyType(I.getType());
          InstrJson["operands"] = {};

          // Add incoming edges from operands where applicable
          for (auto &Op : I.operands()) {
            if (skipOperand(Op)) continue;

            json OpJson = jsonPerOperand(Op, I);
            if (OpJson != nullptr) {
              (InstrJson["operands"]).push_back(OpJson);
            }
          }

          // Add special out edges if the result of this instruction is returned
          // or used outside of this block
          Optional<Instruction *> ExternalUse;
          for (auto *U : I.users()) {
            if (Instruction *UInst = dyn_cast<Instruction>(U)) {
              // If the use is not in the same basic block, consider it an out
              // edge
              if (UInst->getParent() != &B) {
                ExternalUse.emplace(UInst);
                break;
              }
            } else {
              errs () << "Non-instruction use: " << *U << "\n";
            }
          }

          if (ExternalUse.hasValue()) {
            json OutJson;
            OutJson["pointer"] = stringifyPtr(*ExternalUse.getValue());
            OutJson["description"] = "out";
            OutJson["type"] = stringifyType(ExternalUse.getValue()->getType());
            OutJson["value"] = stringifyPtr(I);
            DestinationToOperands.push_back(OutJson);
          }

          DestinationToOperands.push_back(InstrJson);
        }
      }
    }

    // Map from individual instruction to the match data for quick lookup
    map<string, json> jsonToInstructionMatches(json Matches) {
      map<string, json> PerInstruction;

      for (json &Match : Matches) {
        for (auto &[Key, Value] : Match["node_matches"].items()) {
          string Instruction = Key;
          if(PerInstruction.count(Instruction)) {
            errs() << "YO, PerInstruction" << "\n";
            PerInstruction[Instruction] += Match;
          }
          else {
            errs() << "SECOND BRANCH" << "\n";
            PerInstruction[Instruction] = json::array({Match});
          }
        }
      }

      return PerInstruction;
    }

    void addMetadataString(Instruction *I, string Name, string Md) {
      LLVMContext &C = I->getContext();
      MDNode *Node = MDNode::get(C, MDString::get(C, Md));
      I->setMetadata(Name, Node);
    }

    void annotateMatchesPerFunction(map<string, json> Matches, Function &F) {
      for (auto &B : F) {
        for (auto &I : B) {

          // Skip instructions that were not matched
          string IPtr = stringifyPtr(I);
          if (Matches.find(IPtr) == Matches.end()) continue;

          for( json MatchJson : Matches[IPtr]) {
            string mtid = (string)MatchJson["template_id"];

              InstructionsMatched++;
              addMetadataString(&I, "template_id", mtid);

              string MatchIdx = to_string((int)(MatchJson["match_idx"]));
              addMetadataString(&I, "match_idx", MatchIdx);

              string template_node = MatchJson["node_matches"][IPtr];
              addMetadataString(&I, "template_node", template_node);
          }
        }
      }
    }
  };
}

char DFGPass::ID = 0;

// Register the pass so `opt -dfg-pass` runs it.
static RegisterPass<DFGPass> Y("dfg-pass", "Data flow graph construction pass");

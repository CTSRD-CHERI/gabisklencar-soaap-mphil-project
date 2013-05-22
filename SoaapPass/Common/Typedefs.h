#ifndef SOAAP_TYPEDEFS_H
#define SOAAP_TYPEDEFS_H

#include "llvm/IR/Function.h"
#include "llvm/ADT/SmallVector.h"
#include "llvm/ADT/SmallSet.h"
#include <map>

using namespace std;
using namespace llvm;

//typedef SmallVector<Instruction*,16> SandboxedRegion;
//typedef SmallVector<SandboxedRegion,16> SandboxedRegions;
typedef SmallVector<Function*,16> FunctionVector;
typedef SmallSet<Function*,16> FunctionSet;
typedef map<Function*,int> FunctionIntMap;
typedef SmallVector<CallInst*,16> CallInstVector;
typedef map<const Value*,int> ValueIntMap;

#endif
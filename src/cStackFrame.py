import hashlib, math;
from dxBugIdConfig import dxBugIdConfig;

class cStackFrame(object):
  def __init__(oStackFrame, uNumber, sCdbSource, uAddress, sUnloadedModuleFileName, oModule, uModuleOffset, \
      oFunction, uFunctionOffset, sSourceFilePath, uSourceFileLineNumber):
    oStackFrame.uNumber = uNumber;
    oStackFrame.sCdbSource = sCdbSource;
    oStackFrame.uAddress = uAddress;
    oStackFrame.sUnloadedModuleFileName = sUnloadedModuleFileName;
    oStackFrame.oModule = oModule;
    oStackFrame.uModuleOffset = uModuleOffset;
    oStackFrame.oFunction = oFunction;
    oStackFrame.uFunctionOffset = uFunctionOffset;
    oStackFrame.sSourceFilePath = sSourceFilePath;
    oStackFrame.uSourceFileLineNumber = uSourceFileLineNumber;
    oStackFrame.bIsHidden = False; # Set to true if this frame should be hidden because it is not relevant.
    if oFunction:
      oStackFrame.sAddress = oFunction.sName;
      if uFunctionOffset:
        oStackFrame.sAddress += " %s 0x%X" % (uFunctionOffset > 0 and "+" or "-", abs(uFunctionOffset));
        if uFunctionOffset not in xrange(dxBugIdConfig["uMaxFunctionOffset"]):
          # The offset is negative or very large: this may not be the correct symbol. If it is, the offset is very likely
          # to change between builds. The offset should not be part of the id and a warning about the symbol is added.
          oStackFrame.sAddress += " (this may not be correct)";
      oStackFrame.sSimplifiedAddress = oFunction.sSimplifiedName;
      oStackFrame.sUniqueAddress = oFunction.sUniqueName;
    elif oModule:
      oStackFrame.sAddress = "%s + 0x%X" % (oModule.sBinaryName, uModuleOffset);
      oStackFrame.sSimplifiedAddress = "%s+0x%X" % (oModule.sSimplifiedName, uModuleOffset);
      # Adding offset makes it more unique and thus allows distinction between two different crashes, but seriously
      # reduces the chance of getting the same id for the same crash in different builds.
      oStackFrame.sUniqueAddress = "%s+0x%X" % (oModule.sUniqueName, uModuleOffset);
    elif sUnloadedModuleFileName:
      if uModuleOffset is not None:
        oStackFrame.sAddress = "%s + 0x%X" % (sUnloadedModuleFileName, uModuleOffset);
        oStackFrame.sSimplifiedAddress = "%s+0x%X" % (sUnloadedModuleFileName, uModuleOffset);
      else:
        oStackFrame.sAddress = "%s + ??" % sUnloadedModuleFileName;
        oStackFrame.sSimplifiedAddress = sUnloadedModuleFileName;
      oStackFrame.sUniqueAddress = None;
    else:
      oStackFrame.sAddress = "0x%X" % uAddress;
      oStackFrame.sSimplifiedAddress = "(unknown)";
      oStackFrame.sUniqueAddress = None;
    if oStackFrame.sUniqueAddress is None:
      oStackFrame.sId = None;
    else:
      oHasher = hashlib.md5();
      oHasher.update(oStackFrame.sUniqueAddress);
      oStackFrame.sId = oHasher.hexdigest()[:dxBugIdConfig["uMaxStackFrameHashChars"]];

  def fbHide(oStackFrame, asFrameAddresses, bLowered = False):
    asFrameAddressesLowered = bLowered and asFrameAddresses or [s.lower() for s in asFrameAddresses];
    # Hide the frame if the address, simplified address or id address matches any of the supplied values:
    if (
        oStackFrame.sAddress.lower() in asFrameAddressesLowered
        or oStackFrame.sSimplifiedAddress.lower() in asFrameAddressesLowered
        or (oStackFrame.sUniqueAddress and oStackFrame.sUniqueAddress.lower() in asFrameAddressesLowered)
    ):
      oStackFrame.bIsHidden = True; # hide it.
    return oStackFrame.bIsHidden;

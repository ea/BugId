import hashlib, re;
from cBugReport_foAnalyzeException_Cpp import cBugReport_foAnalyzeException_Cpp;
from cBugReport_foAnalyzeException_STATUS_ACCESS_VIOLATION import cBugReport_foAnalyzeException_STATUS_ACCESS_VIOLATION;
from cBugReport_foAnalyzeException_STATUS_BREAKPOINT import cBugReport_foAnalyzeException_STATUS_BREAKPOINT;
from cBugReport_foAnalyzeException_STATUS_INVALID_HANDLE import cBugReport_foAnalyzeException_STATUS_INVALID_HANDLE;
from cBugReport_foAnalyzeException_STATUS_FAIL_FAST_EXCEPTION import cBugReport_foAnalyzeException_STATUS_FAIL_FAST_EXCEPTION;
from cBugReport_foAnalyzeException_STATUS_STACK_BUFFER_OVERRUN import cBugReport_foAnalyzeException_STATUS_STACK_BUFFER_OVERRUN;
from cBugReport_foAnalyzeException_STATUS_STACK_OVERFLOW import cBugReport_foAnalyzeException_STATUS_STACK_OVERFLOW;
from cBugReport_foAnalyzeException_STATUS_STOWED_EXCEPTION import cBugReport_foAnalyzeException_STATUS_STOWED_EXCEPTION;
from cBugReport_foAnalyzeException_STATUS_WX86_BREAKPOINT import cBugReport_foAnalyzeException_STATUS_WX86_BREAKPOINT;
from cBugReport_foTranslate import cBugReport_foTranslate;
from cBugReport_fsGetDisassemblyHTML import cBugReport_fsGetDisassemblyHTML;
from cBugReport_fsGetReferencedMemoryHTML import cBugReport_fsGetReferencedMemoryHTML;
from cBugReport_fsGetBinaryInformationHTML import cBugReport_fsGetBinaryInformationHTML;
from cBugReport_fsProcessStack import cBugReport_fsProcessStack;
from cException import cException;
from cProcess import cProcess;
from NTSTATUS import *;
from sBlockHTMLTemplate import sBlockHTMLTemplate;
from sDetailsHTMLTemplate import sDetailsHTMLTemplate;

dfoAnalyzeException_by_uExceptionCode = {
  CPP_EXCEPTION_CODE:  cBugReport_foAnalyzeException_Cpp,
  STATUS_ACCESS_VIOLATION: cBugReport_foAnalyzeException_STATUS_ACCESS_VIOLATION,
  STATUS_BREAKPOINT: cBugReport_foAnalyzeException_STATUS_BREAKPOINT,
  STATUS_INVALID_HANDLE: cBugReport_foAnalyzeException_STATUS_INVALID_HANDLE,
  STATUS_FAIL_FAST_EXCEPTION: cBugReport_foAnalyzeException_STATUS_FAIL_FAST_EXCEPTION,
  STATUS_STACK_BUFFER_OVERRUN: cBugReport_foAnalyzeException_STATUS_STACK_BUFFER_OVERRUN,
  STATUS_STACK_OVERFLOW: cBugReport_foAnalyzeException_STATUS_STACK_OVERFLOW,
  STATUS_STOWED_EXCEPTION: cBugReport_foAnalyzeException_STATUS_STOWED_EXCEPTION,
  STATUS_WX86_BREAKPOINT: cBugReport_foAnalyzeException_STATUS_WX86_BREAKPOINT,
};
# Hide some functions at the top of the stack that are merely helper functions and not relevant to the bug:
asHiddenTopFrames = [
  "KERNELBASE.dll!RaiseException",
  "ntdll.dll!KiUserExceptionDispatch",
  "ntdll.dll!NtRaiseException",
  "ntdll.dll!RtlDispatchException",
  "ntdll.dll!RtlpExecuteHandlerForException",
  "ntdll.dll!ZwRaiseException",
];
class cBugReport(object):
  def __init__(oBugReport, oCdbWrapper, sBugTypeId, sBugDescription, sSecurityImpact, oException, oStack):
    oBugReport.oCdbWrapper = oCdbWrapper;
    oBugReport.sBugTypeId = sBugTypeId;
    oBugReport.sBugDescription = sBugDescription;
    oBugReport.sSecurityImpact = sSecurityImpact;
    oBugReport.oException = oException;
    oBugReport.oStack = oStack;
    
    if oCdbWrapper.bGetDetailsHTML:
      oBugReport.sImportantOutputHTML = oCdbWrapper.sImportantOutputHTML;
    oBugReport.sProcessBinaryName = oException.oProcess and oException.oProcess.sBinaryName;
    oBugReport.asExceptionSpecificBlocksHTML = [];
    # This information is gathered later, when it turns out this bug needs to be reported:
    oBugReport.sStackId = None;
    oBugReport.sId = None;
    oBugReport.oTopmostRelevantCodeFrame = None;
    oBugReport.sBugLocation = None;
    oBugReport.sBugSourceLocation = None;
  
  def foTranslate(oBugReport, dtxTranslations):
    return cBugReport_foTranslate(oBugReport, dtxTranslations);
  
  def fHideTopStackFrames(oBugReport, dasHiddenFrames_by_sBugTypeIdRegExp):
    for (sBugTypeIdRegExp, asHiddenFrames) in dasHiddenFrames_by_sBugTypeIdRegExp.items():
      if re.match("^(%s)$" % sBugTypeIdRegExp, oBugReport.sBugTypeId):
        oBugReport.oStack.fHideTopFrames(asHiddenFrames);
  
  @classmethod
  def foCreate(cSelf, oCdbWrapper, uExceptionCode, sExceptionDescription):
    # Get current process details
    oProcess = cProcess.foCreate(oCdbWrapper);
    if not oCdbWrapper.bCdbRunning: return None;
    # Get exception details
    oException = cException.foCreate(oCdbWrapper, oProcess, uExceptionCode, sExceptionDescription);
    if not oCdbWrapper.bCdbRunning: return None;
    # Get the stack
    oStack = oException.foGetStack(oCdbWrapper);
    if not oCdbWrapper.bCdbRunning: return None;
    # Compare stack with exception information
    if oException.sAddressSymbol:
      doModules_by_sCdbId = oCdbWrapper.fdoGetModulesByCdbIdForCurrentProcess();
      (
        uAddress,
        sUnloadedModuleFileName, oModule, uModuleOffset,
        oFunction, uFunctionOffset
      ) = oCdbWrapper.ftxSplitSymbolOrAddress(oException.sAddressSymbol, doModules_by_sCdbId);
      sCdbSource = oException.sAddressSymbol;
    else:
      sCdbSource = "%X" % oException.uAddress; # Kinda faking it here :)
      uAddress = oException.uAddress;
      sUnloadedModuleFileName, oModule, uModuleOffset = None, None, None;
      oFunction, uFunctionOffset = None, None;
    if not oStack.aoFrames:
      # Failed to get stack, use information from exception.
      uFrameNumber = 0;
      oStack.fCreateAndAddStackFrame(oCdbWrapper, uFrameNumber, sCdbSource, uAddress, sUnloadedModuleFileName, oModule, uModuleOffset, oFunction, uFunctionOffset);
    else:
      if oException.uCode == STATUS_WAKE_SYSTEM_DEBUGGER:
        # This exception does not happen in a particular part of the code, and the exception address is therefore 0.
        # Do not try to find this address on the stack.
        pass;
      elif oException.uCode in [STATUS_WX86_BREAKPOINT, STATUS_BREAKPOINT]:
        oFrame = oStack.aoFrames[0];
        if (
          oFrame.uAddress == uAddress
          and oFrame.sUnloadedModuleFileName == sUnloadedModuleFileName
          and oFrame.oModule == oModule
          and oFrame.uModuleOffset == uModuleOffset
          and oFrame.oFunction == oFunction
          and oFrame.uFunctionOffset == uFunctionOffset
        ):
          pass;
        else:
          # A breakpoint normally happens at an int 3 instruction, and eip/rip will be updated to the next instruction.
          # If the same exception code (0x80000003) is raised using ntdll!RaiseException, the address will be
          # off-by-one, see if this can be fixed:
          if uAddress is not None:
            uAddress -= 1;
          elif uModuleOffset is not None:
            uModuleOffset -= 1;
          elif uFunctionOffset is not None:
            uFunctionOffset -= 1;
          else:
            raise AssertionError("The first stack frame appears to have no address or offet to adjust.");
          assert (
            oFrame.uAddress == uAddress
            and oFrame.sUnloadedModuleFileName == sUnloadedModuleFileName
            and oFrame.oModule == oModule
            and oFrame.uModuleOffset == uModuleOffset
            and oFrame.oFunction == oFunction
            and oFrame.uFunctionOffset == uFunctionOffset
          ), "The first stack frame does not appear to match the exception address";
      else:
        # Check that the address where the exception happened is on the stack and hide any frames that appear above it,
        # as these are not interesting (e.g. ntdll!RaiseException).
        for oFrame in oStack.aoFrames:
          if (
            oFrame.uAddress == uAddress
            and oFrame.sUnloadedModuleFileName == sUnloadedModuleFileName
            and oFrame.oModule == oModule
            and oFrame.uModuleOffset == uModuleOffset
            and oFrame.oFunction == oFunction
            and oFrame.uFunctionOffset == uFunctionOffset
          ):
            break;
          oFrame.bIsHidden = True;
        else:
          raise AssertionError("The exception address %s was not found on the stack" % sCdbSource);
      
    # Hide some functions at the top of the stack that are merely helper functions and not relevant to the error:
    oStack.fHideTopFrames(asHiddenTopFrames);
    # Create a preliminary error report.
    oBugReport = cSelf(
      oCdbWrapper = oCdbWrapper,
      sBugTypeId = oException.sTypeId,
      sBugDescription = oException.sDescription,
      sSecurityImpact = oException.sSecurityImpact,
      oException = oException,
      oStack = oStack,
    );
    
    # Perform exception specific analysis:
    foAnalyzeException = dfoAnalyzeException_by_uExceptionCode.get(oException.uCode);
    if foAnalyzeException:
      oBugReport = foAnalyzeException(oBugReport, oCdbWrapper);
      if not oCdbWrapper.bCdbRunning: return None;
      if not oBugReport:
        # This exception is not a bug, continue the application.
        return None;
    
    # Calculate sStackId, determine sBugLocation and optionally create and return sStackHTML.
    sStackHTML = cBugReport_fsProcessStack(oBugReport, oCdbWrapper);
    oBugReport.sId = "%s %s" % (oBugReport.sBugTypeId, oBugReport.sStackId);
    if oCdbWrapper.bGetDetailsHTML: # Generate sDetailsHTML?
      # Create HTML details
      asBlocksHTML = [];
      # Create and add important output block if needed
      if oBugReport.sImportantOutputHTML:
        asBlocksHTML.append(sBlockHTMLTemplate % {"sName": "Potentially important application output", "sContent": oBugReport.sImportantOutputHTML});
      # Add stack block
      asBlocksHTML.append(sBlockHTMLTemplate % {"sName": "Stack", "sContent": sStackHTML});
      # Add exception specific blocks if needed:
      asBlocksHTML += oBugReport.asExceptionSpecificBlocksHTML;
      # Create and add disassembly block if possible
      sDisassemblyHTML = cBugReport_fsGetDisassemblyHTML(oBugReport, oCdbWrapper);
      if sDisassemblyHTML is None: return None;
      if sDisassemblyHTML:
        asBlocksHTML.append(sBlockHTMLTemplate % {"sName": "Disassembly", "sContent": sDisassemblyHTML});
      # Create and add registers block
      asRegisters = oCdbWrapper.fasSendCommandAndReadOutput("rM 0x%X" % (0x1 + 0x4 + 0x8 + 0x10 + 0x20 + 0x40));
      if not oCdbWrapper.bCdbRunning: return None;
      sRegistersHTML = "<br/>".join([oCdbWrapper.fsHTMLEncode(s) for s in asRegisters]);
      asBlocksHTML.append(sBlockHTMLTemplate % {"sName": "Registers", "sContent": sRegistersHTML});
      # Add referenced memory to memory block and add memory block if needed
      sReferencedMemoryHTML = cBugReport_fsGetReferencedMemoryHTML(oBugReport, oCdbWrapper)
      if sReferencedMemoryHTML is None: return None;
      if sReferencedMemoryHTML:
        asBlocksHTML.append(sBlockHTMLTemplate % {"sName": "Referenced memory", "sContent": sReferencedMemoryHTML});
      sBinaryInformationHTML = cBugReport_fsGetBinaryInformationHTML(oBugReport, oCdbWrapper);
      if sBinaryInformationHTML is None: return None;
      if sBinaryInformationHTML:
        asBlocksHTML.append(sBlockHTMLTemplate % {"sName": "Binary information", "sContent": sBinaryInformationHTML});
      # Convert saved cdb IO HTML into one string and delete everything but the last line to free up some memory.
      sCdbStdIOHTML = '<hr/>'.join(oBugReport.oCdbWrapper.asCdbStdIOBlocksHTML);
      oBugReport.oCdbWrapper.asCdbStdIOBlocksHTML = oBugReport.oCdbWrapper.asCdbStdIOBlocksHTML[-1:];
      # Stick everything together.
      oBugReport.sDetailsHTML = sDetailsHTMLTemplate % {
        "sId": oCdbWrapper.fsHTMLEncode(oBugReport.sId),
        "sBugDescription": oCdbWrapper.fsHTMLEncode(oBugReport.sBugDescription),
        "sBugLocation": oCdbWrapper.fsHTMLEncode(oBugReport.sBugLocation),
        "sSecurityImpact": oBugReport.sSecurityImpact and \
              '<span class="SecurityImpact">%s</span>' % oCdbWrapper.fsHTMLEncode(oBugReport.sSecurityImpact) or "None",
        "sOptionalBlocks": "".join(asBlocksHTML),
        "sCdbStdIO": sCdbStdIOHTML,
      };
    
    return oBugReport;

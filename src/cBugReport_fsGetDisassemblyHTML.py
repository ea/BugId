import re;
def fsHTMLEncodeAndColor(oCdbWrapper, sLine):
  # If this line starts with an address and opcode, make those semi-transparent.
  oMatch = re.match(r"^([0-9a-fA-F`]+\s+)([0-9a-fA-F]+\s+)(.+)$", sLine);
  if oMatch:
    return '<span class=\"DisassemblyAddress\">%s</span><span class=\"DisassemblyOpcode\">%s</span>%s' % \
        tuple([oCdbWrapper.fsHTMLEncode(s) for s in oMatch.groups()]);
  return oCdbWrapper.fsHTMLEncode(sLine);
  
def cBugReport_fsGetDisassemblyHTML(oBugReport, oCdbWrapper):
  # Get disassembly around code in which exception happened. This may not be possible if the instruction pointer points to unmapped memory.
  asBeforeDisassembly = oCdbWrapper.fasSendCommandAndReadOutput(".if ($vvalid(@$scopeip - 40, 40)) { u @$scopeip - 40 @$scopeip - 1; };");
  if not oCdbWrapper.bCdbRunning: return None;
  asAtAndAfterDisassembly = oCdbWrapper.fasSendCommandAndReadOutput(".if ($vvalid(@$scopeip, 40)) { u @$scopeip @$scopeip + 39; };");
  if not oCdbWrapper.bCdbRunning: return None;
  if asBeforeDisassembly or asAtAndAfterDisassembly:
    if asAtAndAfterDisassembly:
      asBeforeDisassembly.append(asAtAndAfterDisassembly.pop(0)); # Move symbol from second chunk to chunk before instruction pointer.
      asBeforeDisassembly = asBeforeDisassembly[-16:]; # Max sixteen lines
      sAtDisassembly = asAtAndAfterDisassembly.pop(0); # remove instruction in which exception happened from second chunk.
      sAtDisassemblyDescription = sAtDisassembly and "instruction pointer";
      sNextDisassembly = asAtAndAfterDisassembly and asAtAndAfterDisassembly.pop(0) or None; # remove next instruction after exception from second chunk.
      sNextDisassemblyDescription = None;
      asAfterDisassembly = asAtAndAfterDisassembly[:16]; # Max sixteen lines
    else:
      sAtDisassembly = None;
      sNextDisassembly = None;
      asAfterDisassembly = None;
  else:
    # Getting disassembly around instruction pointer failed: get disassembly around current return address.
    # This may also not be possible if the stack is corrupt.
    asBeforeAndAtCallDisassembly = oCdbWrapper.fasSendCommandAndReadOutput(".if ($vvalid(@$ra - 40, 40)) { u @$ra - 40 @$ra - 1; };");
    if not oCdbWrapper.bCdbRunning: return None;
    asNextAndAfterDisassembly = oCdbWrapper.fasSendCommandAndReadOutput(".if ($vvalid(@$ra, 40)) { u @$ra @$ra + 39; };");
    if not oCdbWrapper.bCdbRunning: return None;
    if asBeforeAndAtCallDisassembly:
      sAtDisassembly = asBeforeAndAtCallDisassembly.pop(); # remove call instruction
      sAtDisassemblyDescription = sAtDisassembly and "call";
      asBeforeDisassembly = asBeforeAndAtCallDisassembly[-16:]; # Max sixteen lines
    else:
      sAtDisassembly = None;
      asBeforeDisassembly = None;
    if asNextAndAfterDisassembly:
      asNextAndAfterDisassembly.pop(0); # Remove symbol at return address.
      sNextDisassembly = asNextAndAfterDisassembly and asNextAndAfterDisassembly.pop(0) or None; # remove return address instruction.
      sNextDisassemblyDescription = sNextDisassembly and "return address";
      asAfterDisassembly = asNextAndAfterDisassembly[:16]; # Max sixteen lines
    else:
      sNextDisassembly = None;
      asAfterDisassembly = None;
  if asBeforeDisassembly or sAtDisassembly or sNextDisassembly or asAfterDisassembly:
    sAtDisassemblyHTML = sAtDisassemblyDescription \
        and "<span class=\"Important\">%s &#8656; %s</span>" % (fsHTMLEncodeAndColor(oCdbWrapper, sAtDisassembly.ljust(80)), sAtDisassemblyDescription) \
        or fsHTMLEncodeAndColor(oCdbWrapper, sAtDisassembly);
    sNextDisassemblyHTML = sNextDisassemblyDescription \
        and "<span class=\"Important\">%s &#8656; %s</span>" % (fsHTMLEncodeAndColor(oCdbWrapper, sNextDisassembly.ljust(80)), sNextDisassemblyDescription) \
        or fsHTMLEncodeAndColor(oCdbWrapper, sNextDisassembly);
    return "<br/>".join(
      (asBeforeDisassembly and [fsHTMLEncodeAndColor(oCdbWrapper, s) for s in asBeforeDisassembly] or []) +
       (sAtDisassemblyHTML and [sAtDisassemblyHTML] or []) +
     (sNextDisassemblyHTML and [sNextDisassemblyHTML] or []) +
       (asAfterDisassembly and [fsHTMLEncodeAndColor(oCdbWrapper, s) for s in asAfterDisassembly] or [])
    );
  return "";

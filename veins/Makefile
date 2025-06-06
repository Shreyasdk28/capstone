#
# OMNeT++/OMNEST Makefile for veins
#
# This file was generated with the command:
#  opp_makemake -f --deep
#

# Name of target to be created (-o option)
TARGET_DIR = .
TARGET_NAME = veins$(D)
TARGET = $(TARGET_NAME)$(EXE_SUFFIX)
TARGET_IMPLIB = $(TARGET_NAME)$(IMPLIB_SUFFIX)
TARGET_IMPDEF = $(TARGET_NAME)$(IMPDEF_SUFFIX)
TARGET_FILES = $(TARGET_DIR)/$(TARGET)

# User interface (uncomment one) (-u option)
USERIF_LIBS = $(ALL_ENV_LIBS) # that is, $(QTENV_LIBS) $(CMDENV_LIBS)
#USERIF_LIBS = $(CMDENV_LIBS)
#USERIF_LIBS = $(QTENV_LIBS)

# C++ include paths (with -I)
INCLUDE_PATH =

# Additional object and library files to link with
EXTRA_OBJS =

# Additional libraries (-L, -l options)
LIBS =

# Output directory
PROJECT_OUTPUT_DIR = out
PROJECTRELATIVE_PATH =
O = $(PROJECT_OUTPUT_DIR)/$(CONFIGNAME)/$(PROJECTRELATIVE_PATH)

# Object files for local .cc, .msg and .sm files
OBJS = \
    $O/src/veins/common_m.o \
    $O/src/veins/base/messages/AirFrame_m.o \
    $O/src/veins/base/messages/BorderMsg_m.o \
    $O/src/veins/base/messages/MacPkt_m.o \
    $O/src/veins/base/toolbox/Signal_m.o \
    $O/src/veins/base/utils/Coord_m.o \
    $O/src/veins/base/utils/POA_m.o \
    $O/src/veins/base/utils/SimpleAddress_m.o \
    $O/src/veins/modules/application/traci/TraCIDemo11pMessage_m.o \
    $O/src/veins/modules/messages/AckTimeOutMessage_m.o \
    $O/src/veins/modules/messages/AirFrame11p_m.o \
    $O/src/veins/modules/messages/BaseFrame1609_4_m.o \
    $O/src/veins/modules/messages/DemoSafetyMessage_m.o \
    $O/src/veins/modules/messages/DemoServiceAdvertisement_m.o \
    $O/src/veins/modules/messages/Mac80211Ack_m.o \
    $O/src/veins/modules/messages/Mac80211Pkt_m.o \
    $O/src/veins/modules/messages/PhyControlMessage_m.o \
    $O/src/veins/modules/messages/TraCITrafficLightMessage_m.o \
    $O/subprojects/veins_inet/src/veins_inet/VeinsInetSampleMessage_m.o

# Message files
MSGFILES = \
    src/veins/common.msg \
    src/veins/base/messages/AirFrame.msg \
    src/veins/base/messages/BorderMsg.msg \
    src/veins/base/messages/MacPkt.msg \
    src/veins/base/toolbox/Signal.msg \
    src/veins/base/utils/Coord.msg \
    src/veins/base/utils/POA.msg \
    src/veins/base/utils/SimpleAddress.msg \
    src/veins/modules/application/traci/TraCIDemo11pMessage.msg \
    src/veins/modules/messages/AckTimeOutMessage.msg \
    src/veins/modules/messages/AirFrame11p.msg \
    src/veins/modules/messages/BaseFrame1609_4.msg \
    src/veins/modules/messages/DemoSafetyMessage.msg \
    src/veins/modules/messages/DemoServiceAdvertisement.msg \
    src/veins/modules/messages/Mac80211Ack.msg \
    src/veins/modules/messages/Mac80211Pkt.msg \
    src/veins/modules/messages/PhyControlMessage.msg \
    src/veins/modules/messages/TraCITrafficLightMessage.msg \
    subprojects/veins_inet/src/veins_inet/VeinsInetSampleMessage.msg

# SM files
SMFILES =

#------------------------------------------------------------------------------

# Pull in OMNeT++ configuration (Makefile.inc)

ifneq ("$(OMNETPP_CONFIGFILE)","")
CONFIGFILE = $(OMNETPP_CONFIGFILE)
else
CONFIGFILE = $(shell opp_configfilepath)
endif

ifeq ("$(wildcard $(CONFIGFILE))","")
$(error Config file '$(CONFIGFILE)' does not exist -- add the OMNeT++ bin directory to the path so that opp_configfilepath can be found, or set the OMNETPP_CONFIGFILE variable to point to Makefile.inc)
endif

include $(CONFIGFILE)

# Simulation kernel and user interface libraries
OMNETPP_LIBS = $(OPPMAIN_LIB) $(USERIF_LIBS) $(KERNEL_LIBS) $(SYS_LIBS)

COPTS = $(CFLAGS) $(IMPORT_DEFINES)  $(INCLUDE_PATH) -I$(OMNETPP_INCL_DIR)
MSGCOPTS = $(INCLUDE_PATH)
SMCOPTS =

# we want to recompile everything if COPTS changes,
# so we store COPTS into $COPTS_FILE (if COPTS has changed since last build)
# and make the object files depend on it
COPTS_FILE = $O/.last-copts
ifneq ("$(COPTS)","$(shell cat $(COPTS_FILE) 2>/dev/null || echo '')")
  $(shell $(MKPATH) "$O")
  $(file >$(COPTS_FILE),$(COPTS))
endif

#------------------------------------------------------------------------------
# User-supplied makefile fragment(s)
#------------------------------------------------------------------------------

# Main target
all: $(TARGET_FILES)

$(TARGET_DIR)/% :: $O/%
	@mkdir -p $(TARGET_DIR)
	$(Q)$(LN) $< $@
ifeq ($(TOOLCHAIN_NAME),clang-msabi)
	-$(Q)-$(LN) $(<:%.dll=%.lib) $(@:%.dll=%.lib) 2>/dev/null

$O/$(TARGET_NAME).pdb: $O/$(TARGET)
endif

$O/$(TARGET): $(OBJS)  $(wildcard $(EXTRA_OBJS)) Makefile $(CONFIGFILE)
	@$(MKPATH) $O
	@echo Creating executable: $@
	$(Q)$(CXX) $(LDFLAGS) -o $O/$(TARGET) $(OBJS) $(EXTRA_OBJS) $(AS_NEEDED_OFF) $(WHOLE_ARCHIVE_ON) $(LIBS) $(WHOLE_ARCHIVE_OFF) $(OMNETPP_LIBS)

.PHONY: all clean cleanall depend msgheaders smheaders

# disabling all implicit rules
.SUFFIXES :
.PRECIOUS : %_m.h %_m.cc

$O/%.o: %.cc $(COPTS_FILE) | msgheaders smheaders
	@$(MKPATH) $(dir $@)
	$(qecho) "$<"
	$(Q)$(CXX) -c $(CXXFLAGS) $(COPTS) -o $@ $<

%_m.cc %_m.h: %.msg
	$(qecho) MSGC: $<
	$(Q)$(MSGC) -s _m.cc -MD -MP -MF $O/$(basename $<)_m.h.d $(MSGCOPTS) $?

%_sm.cc %_sm.h: %.sm
	$(qecho) SMC: $<
	$(Q)$(SMC) -c++ -suffix cc $(SMCOPTS) $?

msgheaders: $(MSGFILES:.msg=_m.h)

smheaders: $(SMFILES:.sm=_sm.h)

clean:
	$(qecho) Cleaning $(TARGET)
	$(Q)-rm -rf $O
	$(Q)-rm -f $(TARGET_FILES)
	$(Q)-rm -f $(call opp_rwildcard, . , *_m.cc *_m.h *_sm.cc *_sm.h)

cleanall:
	$(Q)$(CLEANALL_COMMAND)
	$(Q)-rm -rf $(PROJECT_OUTPUT_DIR)

help:
	@echo "$$HELP_SYNOPSYS"
	@echo "$$HELP_TARGETS"
	@echo "$$HELP_VARIABLES"
	@echo "$$HELP_EXAMPLES"

# include all dependencies
-include $(OBJS:%=%.d) $(MSGFILES:%.msg=$O/%_m.h.d)

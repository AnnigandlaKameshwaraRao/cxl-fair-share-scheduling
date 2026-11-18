/* Region-of-interest markers for gem5 + SST runs (C and C++).
 * Same protocol as STREAM (stream-syscalls): the guest's `m5` CLI via system(),
 * one command per call (combining commands made the first workbegin after a
 * checkpoint restore not take effect).
 *   roi_checkpoint(): end of setup; the KVM boot run takes its checkpoint here
 *   roi_begin()/roi_end(): one measured region = one stats dump (plus the SST
 *                          bridge's duplicate dump on workend)
 *   roi_finish(): ends this host's simulation
 * Build without -DGEM5_ANNOTATION to run natively (markers become no-ops). */
#ifndef BTP_ROI_H
#define BTP_ROI_H
#include <stdlib.h>

#ifdef GEM5_ANNOTATION
static inline void roi_checkpoint(void) { if (system("m5 exit")) {} }
static inline void roi_begin(void)
{ if (system("m5 resetstats")) {} if (system("m5 workbegin")) {} }
static inline void roi_end(void)
{ if (system("m5 workend")) {} if (system("m5 dumpresetstats")) {} }
static inline void roi_finish(void) { if (system("m5 exit")) {} }
#else
static inline void roi_checkpoint(void) {}
static inline void roi_begin(void) {}
static inline void roi_end(void) {}
static inline void roi_finish(void) {}
#endif
#endif

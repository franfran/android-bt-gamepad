#!/usr/bin/env python3
"""Compile source-extracted candidate JNI code under stand-in JNI types.

This checks syntax and fail-closed behavior, NOT Android build or native BTM.
"""
from pathlib import Path
import subprocess
import tempfile

here = Path(__file__).resolve().parent
patch = (here / "h618_jni_java_deny_only_disabled.patch").read_text()
path = "packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp"
section = patch.split(f"diff --git a/{path} b/{path}", 1)[1].split(
    "diff --git ", 1)[0]
added = [line[1:] for line in section.splitlines()
         if line.startswith("+") and not line.startswith("+++")]
text = "\n".join(added)
start = text.index("#if defined(RETROBOX_DS3_JAVA_ADMISSION_RESEARCH)\n"
                   "// No caller is wired")
end = text.index("#endif", start) + len("#endif")
observer = text[start:end]
start = text.index("#if defined(RETROBOX_DS3_JAVA_ADMISSION_RESEARCH)\n"
                   "// No native admission registry")
end = text.index("#endif", start) + len("#endif")
deny = text[start:end]
assert "return JNI_FALSE;" in deny
assert "return JNI_TRUE;" not in deny
assert "method_onRetroboxCandidate" in observer
assert '"onRetroboxHidCandidate", "([BIJJ)V"' in text
assert '"retroboxAdmissionDecisionNative", "(IJJZ)Z"' in text

prefix = r"""
#include <cassert>
#include <cstdint>
#include <iostream>
#include <shared_mutex>
#include <mutex>
using jint=int; using jlong=long long; using jboolean=int;
using jmethodID=void*; using jobject=void*;
constexpr int JNI_FALSE=0; using jbyteArray=const uint8_t*;
struct RawAddress {uint8_t addr[6];};
static int callbacks=0, checks=0;
static jint last_handle=0;
static jlong last_epoch=0, last_request=0;
struct JNIEnv {
  void CallVoidMethod(jobject, jmethodID, jbyteArray addr,
                      jint handle, jlong epoch, jlong request) {
    if (addr) {callbacks++;last_handle=handle;last_epoch=epoch;last_request=request;}
  }
};
struct CallbackEnv {
  JNIEnv env;
  explicit CallbackEnv(const char*) {}
  bool valid() const {return true;}
  JNIEnv* get(){return &env;}
  JNIEnv* operator->(){return &env;}
};
template<class T> struct ScopedLocalRef {
  T value;
  ScopedLocalRef(JNIEnv*,T arg):value(arg){}
  T get() const {return value;}
};
static jmethodID method_onRetroboxCandidate=reinterpret_cast<void*>(1);
static jobject mCallbacksObj=reinterpret_cast<void*>(2);
static std::shared_timed_mutex mCallbacks_mutex;
static jbyteArray marshall_bda(RawAddress* addr) {return addr?addr->addr:nullptr;}
#define RETROBOX_DS3_JAVA_ADMISSION_RESEARCH
"""
suffix = r"""
static void check(bool ok){assert(ok);++checks;}
int main() {
  RawAddress address{{1,2,3,4,5,6}};
  retrobox_hid_candidate_observe(nullptr,4,3,4);check(callbacks==0);
  retrobox_hid_candidate_observe(&address,-1,3,4);check(callbacks==0);
  retrobox_hid_candidate_observe(&address,4,0,4);check(callbacks==0);
  retrobox_hid_candidate_observe(&address,4,3,0);check(callbacks==0);
  retrobox_hid_candidate_observe(&address,4,3,4);check(callbacks==1);
  check(last_handle==4&&last_epoch==3&&last_request==4);
  check(retroboxAdmissionDecisionNative(nullptr,nullptr,4,3,4,0)==JNI_FALSE);
  check(retroboxAdmissionDecisionNative(nullptr,nullptr,4,3,4,1)==JNI_FALSE);
  mCallbacksObj=nullptr;
  retrobox_hid_candidate_observe(&address,5,7,8);check(callbacks==1);
  std::cout<<checks<<"/"<<checks<<" PASS (source-extracted JNI deny-only smoke)\n";
}
"""
with tempfile.TemporaryDirectory() as temp:
    src = Path(temp) / "JniSeamSmoke.cc"
    src.write_text(prefix + "\n" + observer + "\n" + deny + "\n" + suffix)
    binary = Path(temp) / "jni_smoke"
    subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
         str(src), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)

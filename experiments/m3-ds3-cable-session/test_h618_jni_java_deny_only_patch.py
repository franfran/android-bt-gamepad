#!/usr/bin/env python3
"""Validate AND host-compile Java additions from committed H618 JNI/Java patch.

Compiles a source-extracted Java callback/Handler in minimal stand-in classes.
No Android SDK, JNI library, Bluetooth I/O, M3 execution, or auth relaxation.
"""
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
PATCH = HERE / "h618_jni_java_deny_only_disabled.patch"
JAVA_PATH = "packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java"
JNI_PATH = "packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp"


def additions(text, path):
    block = text.split(f"diff --git a/{path} b/{path}", 1)[1]
    block = block.split("diff --git ", 1)[0]
    return "\n".join(line[1:] for line in block.splitlines()
                     if line.startswith("+") and not line.startswith("+++"))


def enclosed(lines, start, stop):
    i = lines.index(start)
    return "\n".join(lines[i:lines.index(stop, i + 1) + 1])


def main():
    patch = PATCH.read_text()
    jni = additions(patch, JNI_PATH)
    java = additions(patch, JAVA_PATH)
    assert '#if defined(RETROBOX_DS3_JAVA_ADMISSION_RESEARCH)' in jni
    assert 'onRetroboxHidCandidate", "([BIJJ)V"' in jni
    assert '{"retroboxAdmissionDecisionNative", "(IJJZ)Z"' in jni
    assert "return JNI_FALSE;" in jni
    assert 'return JNI_TRUE;' not in jni
    assert "method_onConnectStateChanged =" not in jni
    assert "BOND_BONDED" not in patch
    assert "BTA_SEC_AUTHENTICATE" not in patch
    assert "UHID_CREATE" not in patch
    assert "candidate.requestId, false)" in java
    assert "mHandler.removeMessages(MESSAGE_RETROBOX_CANDIDATE)" in java
    assert "mRetroboxServiceGeneration++" in java
    assert all(not line.startswith("-") or line.startswith("---")
               for line in patch.splitlines())

    lines = java.splitlines()
    candidate = enclosed(lines, "    private static final class RetroboxCandidate {",
                         "    }")
    method = enclosed(lines,
        "    private void onRetroboxHidCandidate(byte[] address, int handle,",
        "    }")
    handler = enclosed(lines,
        "                case MESSAGE_RETROBOX_CANDIDATE: {",
        "                break;")

    smoke = r"""
import java.util.ArrayDeque;
public final class JavaSeamSmoke {
  static class Message {
    int what; Object obj;
    Message(int which) { what=which; }
  }
  final class MockHandler {
    final ArrayDeque<Message> queue = new ArrayDeque<>();
    Message obtainMessage(int what) { return new Message(what); }
    boolean sendMessage(Message msg) { return queue.add(msg); }
    void removeMessages(int what) { queue.removeIf(m -> m.what == what); }
  }
  private static final int MESSAGE_RETROBOX_CANDIDATE = 1001;
  private volatile long mRetroboxServiceGeneration = 1;
  private boolean mNativeAvailable = true;
  private final MockHandler mHandler = new MockHandler();
  private int denials = 0;
  private boolean observedApprove = true;
  private boolean retroboxAdmissionDecisionNative(int h,long ep,long req,boolean approve) {
    denials++;
    observedApprove = approve;
    return false; // no native registry exists
  }
"""
    smoke += "\n" + candidate + "\n" + method + "\n"
    smoke += r"""
  void dispatch() {
    if (mHandler.queue.isEmpty()) return;
    Message msg = mHandler.queue.removeFirst();
    switch (msg.what) {
"""
    smoke += "\n" + handler + "\n"
    smoke += r"""
      default: break;
    }
  }
  static int checks = 0;
  static void check(boolean ok) { if (!ok) throw new AssertionError("#"+(checks+1)); checks++; }
  public static void main(String[] args) {
    JavaSeamSmoke s = new JavaSeamSmoke();
    byte[] address = {1,2,3,4,5,6};
    s.onRetroboxHidCandidate(address,4,10,99);
    check(s.mHandler.queue.size()==1);
    RetroboxCandidate event=(RetroboxCandidate)s.mHandler.queue.peek().obj;
    address[0]=10; check(event.address[0]==1);
    s.dispatch();
    check(s.denials==1 && !s.observedApprove);
    check(s.mHandler.queue.isEmpty());
    s.onRetroboxHidCandidate(address,4,11,100);
    s.mRetroboxServiceGeneration++;
    s.dispatch(); check(s.denials==1);
    s.onRetroboxHidCandidate(null,4,11,101);
    s.onRetroboxHidCandidate(new byte[]{1},4,11,101);
    s.onRetroboxHidCandidate(address,-1,11,101);
    s.onRetroboxHidCandidate(address,4,0,101);
    s.onRetroboxHidCandidate(address,4,11,0);
    check(s.mHandler.queue.isEmpty());
    s.mNativeAvailable=false;
    s.onRetroboxHidCandidate(address,4,11,102);
    check(s.mHandler.queue.isEmpty());
    s.mNativeAvailable=true;
    s.onRetroboxHidCandidate(address,4,12,103);
    check(s.mHandler.queue.size()==1);
    s.mHandler.removeMessages(MESSAGE_RETROBOX_CANDIDATE);
    check(s.mHandler.queue.isEmpty());
    System.out.println(checks+"/"+checks+" PASS (source-extracted Java deny-only seam)");
  }
}
"""
    with tempfile.TemporaryDirectory() as folder:
        src = Path(folder) / "JavaSeamSmoke.java"
        src.write_text(smoke)
        subprocess.run(["javac", "-Xlint:all", str(src)], check=True)
        subprocess.run(["java", "-cp", folder, "JavaSeamSmoke"], check=True)
    print("PASS: JNI registration signatures and default-off deny-only guard")


if __name__ == "__main__":
    main()

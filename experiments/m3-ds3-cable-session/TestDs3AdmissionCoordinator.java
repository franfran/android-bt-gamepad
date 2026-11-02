package retrobox;
import static retrobox.Ds3AdmissionCoordinator.*;

public final class TestDs3AdmissionCoordinator {
    private static int count;
    private static final byte[] ADDR = {1, 2, 3, 4, 5, 6};
    private static void check(boolean ok) { if (!ok) throw new AssertionError("#" + (count+1)); count++; }
    private static Policy policy(boolean quiet, boolean allowed, boolean bonded) {
        return new Policy(quiet, allowed, bonded);
    }
    public static void main(String[] args) {
        Ds3AdmissionCoordinator g = new Ds3AdmissionCoordinator(1001);
        Ticket t = new Ticket(1001, 5, 1);
        Event bonded = g.begin(t, ADDR, Evidence.NORMAL_AUTHENTICATED_HID);
        check(bonded != null);
        ADDR[0] = 9;
        check(bonded.getAddressCopy()[0] == 1);
        byte[] copy = bonded.getAddressCopy(); copy[0] = 8;
        check(bonded.getAddressCopy()[0] == 1);
        check(!g.permittedBeforeUhidCreate(t));
        check(g.evaluate(bonded, policy(true,true,true)) == Decision.ALLOW_NORMAL_BONDED);
        check(g.receiveReply(bonded, Decision.ALLOW_NORMAL_BONDED));
        check(g.permittedBeforeUhidCreate(t));
        check(!g.receiveReply(bonded, Decision.ALLOW_NORMAL_BONDED));
        check(g.evaluate(bonded, policy(true,true,true)) == Decision.DENY_STALE);
        check(g.revoke(t));
        check(!g.permittedBeforeUhidCreate(t));
        check(!g.revoke(t));
        check(g.begin(t, new byte[]{1,2,3,4,5,6}, Evidence.NORMAL_AUTHENTICATED_HID) == null);
        Ticket x = new Ticket(1001, 5, 2);
        Event usb = g.begin(x, new byte[]{1,2,3,4,5,6}, Evidence.USB_ADDRESS_CANDIDATE);
        check(usb != null);
        check(g.evaluate(usb, policy(true,true,false)) == Decision.DENY_USB_CANDIDATE);
        check(!g.receiveReply(usb, Decision.DENY_USB_CANDIDATE));
        check(!g.permittedBeforeUhidCreate(x));
        check(!g.receiveReply(usb, Decision.ALLOW_NORMAL_BONDED));
        Ticket x2 = new Ticket(1001, 5, 3);
        Event newer = g.begin(x2, new byte[]{1,2,3,4,5,6}, Evidence.NORMAL_AUTHENTICATED_HID);
        check(newer != null);
        check(g.evaluate(usb, policy(true,true,true)) == Decision.DENY_STALE);
        check(!g.receiveReply(usb, Decision.ALLOW_NORMAL_BONDED));
        check(!g.revoke(x));
        check(g.evaluate(newer, policy(false,true,true)) == Decision.DENY_POLICY);
        check(g.evaluate(newer, policy(true,false,true)) == Decision.DENY_POLICY);
        check(g.evaluate(newer, policy(true,true,false)) == Decision.DENY_UNBONDED);
        check(!g.permittedBeforeUhidCreate(x2));
        check(g.evaluate(newer, policy(true,true,true)) == Decision.ALLOW_NORMAL_BONDED);
        check(!g.receiveReply(newer, Decision.DENY_POLICY));
        check(!g.permittedBeforeUhidCreate(x2));
        check(g.receiveReply(newer, Decision.ALLOW_NORMAL_BONDED));
        Event unknown = g.begin(new Ticket(1001, 6, 1), new byte[]{1,2,3,4,5,6}, Evidence.UNKNOWN);
        check(g.evaluate(unknown, policy(true,true,true)) == Decision.DENY_UNKNOWN);
        check(!g.receiveReply(unknown, Decision.ALLOW_NORMAL_BONDED));
        check(!g.permittedBeforeUhidCreate(unknown.ticket));
        check(g.begin(new Ticket(555, 7, 1), new byte[]{1,2,3,4,5,6}, Evidence.NORMAL_AUTHENTICATED_HID) == null);
        check(g.begin(new Ticket(1001, -1, 1), new byte[]{1,2,3,4,5,6}, Evidence.NORMAL_AUTHENTICATED_HID) == null);
        check(g.begin(new Ticket(1001, 7, 0), new byte[]{1,2,3,4,5,6}, Evidence.NORMAL_AUTHENTICATED_HID) == null);
        check(g.begin(new Ticket(1001, 7, 1), new byte[]{1}, Evidence.NORMAL_AUTHENTICATED_HID) == null);
        check(g.begin(new Ticket(1001, 7, 1), null, Evidence.NORMAL_AUTHENTICATED_HID) == null);
        check(g.begin(new Ticket(1001, 7, 1), new byte[]{1,2,3,4,5,6}, null) == null);
        check(g.pendingSessions() == 2);
        g.nativeRestart(1002);
        check(!g.permittedBeforeUhidCreate(x2));
        check(!g.receiveReply(newer, Decision.ALLOW_NORMAL_BONDED));
        check(g.pendingSessions() == 0);
        Event fresh = g.begin(new Ticket(1002, 5, 1), new byte[]{1,2,3,4,5,6}, Evidence.NORMAL_AUTHENTICATED_HID);
        check(fresh != null);
        check(g.evaluate(fresh, policy(true,true,true)) == Decision.ALLOW_NORMAL_BONDED);
        check(g.receiveReply(fresh, Decision.ALLOW_NORMAL_BONDED));
        check(g.permittedBeforeUhidCreate(fresh.ticket));
        try { g.nativeRestart(1002); throw new AssertionError("restart accepted same id"); }
        catch (IllegalArgumentException expected) { count++; }
        System.out.println(count + "/" + count + " PASS (Java host-only event-bound admission)");
    }
}

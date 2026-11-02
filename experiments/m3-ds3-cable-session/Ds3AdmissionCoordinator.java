package retrobox;
import java.util.HashMap;
import java.util.Map;

/** Host-only simulation of an event-bound Native-to-Java admission handshake.
 * No Android APIs, JNI, Bluetooth auth changes or USB access.
 */
public final class Ds3AdmissionCoordinator {
    public enum Evidence { NORMAL_AUTHENTICATED_HID, USB_ADDRESS_CANDIDATE, UNKNOWN }
    public enum Decision { ALLOW_NORMAL_BONDED, DENY_POLICY, DENY_UNBONDED,
        DENY_USB_CANDIDATE, DENY_UNKNOWN, DENY_STALE }
    public static final class Ticket {
        public final long bootId;
        public final int handle;
        public final long epoch;
        public Ticket(long bootId, int handle, long epoch) {
            this.bootId = bootId;
            this.handle = handle;
            this.epoch = epoch;
        }
        @Override public boolean equals(Object other) {
            if (!(other instanceof Ticket)) return false;
            Ticket t = (Ticket) other;
            return bootId == t.bootId && handle == t.handle && epoch == t.epoch;
        }
        @Override public int hashCode() {
            return Long.hashCode(bootId) * 31 * 31 + handle * 31 + Long.hashCode(epoch);
        }
    }
    public static final class Policy {
        public final boolean quietModePermitsConnection;
        public final boolean connectionPolicyPermits;
        public final boolean bonded;
        public Policy(boolean quietModePermitsConnection, boolean connectionPolicyPermits,
                      boolean bonded) {
            this.quietModePermitsConnection = quietModePermitsConnection;
            this.connectionPolicyPermits = connectionPolicyPermits;
            this.bonded = bonded;
        }
    }
    public static final class Event {
        public final Ticket ticket;
        public final Evidence evidence;
        private final byte[] address;
        private Event(Ticket ticket, byte[] address, Evidence evidence) {
            this.ticket = ticket;
            this.address = address.clone();
            this.evidence = evidence;
        }
        public byte[] getAddressCopy() { return address.clone(); }
    }
    private static final class Pending {
        final Event event;
        Decision evaluated;
        boolean replied;
        boolean uhidApproved;
        Pending(Event event) { this.event = event; }
    }
    private final Map<Integer, Pending> active = new HashMap<>();
    private final Map<Integer, Long> lastEpoch = new HashMap<>();
    private long activeBoot;
    public Ds3AdmissionCoordinator(long bootId) {
        if (bootId <= 0) throw new IllegalArgumentException("bootId");
        activeBoot = bootId;
    }
    /** A trusted native layer MUST mint immutable boot and session generation IDs.
     * No address supplied here constitutes peer authentication proof.
     */
    public synchronized Event begin(Ticket t, byte[] address, Evidence evidence) {
        if (t == null || t.bootId != activeBoot || t.handle < 0 || t.epoch <= 0 ||
            address == null || address.length != 6 || evidence == null) return null;
        if (t.epoch <= lastEpoch.getOrDefault(t.handle, 0L)) return null;
        lastEpoch.put(t.handle, t.epoch);
        Event event = new Event(t, address, evidence);
        active.put(t.handle, new Pending(event)); // retire prior handle generation
        return event;
    }
    private Pending lookup(Ticket t) {
        if (t == null || t.bootId != activeBoot) return null;
        Pending p = active.get(t.handle);
        return p != null && p.event.ticket.equals(t) ? p : null;
    }
    /** Called by the Java Handler, not by the native Bluetooth callback thread.
     * Deliberately rejects cable-only MAC evidence regardless of owner consent.
     */
    public synchronized Decision evaluate(Event event, Policy policy) {
        if (event == null || policy == null) return Decision.DENY_STALE;
        Pending p = lookup(event.ticket);
        if (p == null || p.event != event || p.replied) return Decision.DENY_STALE;
        Decision decision;
        if (!policy.quietModePermitsConnection || !policy.connectionPolicyPermits)
            decision = Decision.DENY_POLICY;
        else if (event.evidence == Evidence.USB_ADDRESS_CANDIDATE)
            decision = Decision.DENY_USB_CANDIDATE;
        else if (event.evidence != Evidence.NORMAL_AUTHENTICATED_HID)
            decision = Decision.DENY_UNKNOWN;
        else if (!policy.bonded)
            decision = Decision.DENY_UNBONDED;
        else decision = Decision.ALLOW_NORMAL_BONDED;
        p.evaluated = decision;
        return decision;
    }
    /** Native mock accepts exactly one reply for a matching live event.
     * This method only models admission ordering: no actual UHID operation.
     */
    public synchronized boolean receiveReply(Event event, Decision decision) {
        if (event == null || decision == null) return false;
        Pending p = lookup(event.ticket);
        if (p == null || p.event != event || p.replied ||
            p.evaluated == null || p.evaluated != decision) return false;
        p.replied = true;
        // No explicit cable exception path. It must be separately designed.
        p.uhidApproved = decision == Decision.ALLOW_NORMAL_BONDED &&
                p.event.evidence == Evidence.NORMAL_AUTHENTICATED_HID;
        return p.uhidApproved;
    }
    public synchronized boolean permittedBeforeUhidCreate(Ticket ticket) {
        Pending p = lookup(ticket);
        return p != null && p.replied && p.uhidApproved;
    }
    public synchronized boolean revoke(Ticket ticket) {
        Pending p = lookup(ticket);
        if (p == null) return false;
        active.remove(ticket.handle);
        return true;
    }
    public synchronized void nativeRestart(long newBootId) {
        if (newBootId <= 0 || newBootId == activeBoot)
            throw new IllegalArgumentException("fresh bootId required");
        active.clear();
        lastEpoch.clear();
        activeBoot = newBootId;
    }
    public synchronized int pendingSessions() { return active.size(); }
}

package mybatis.iem.em.modules.engineering.application.service.impl;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;

public class EventNotificationDecisionPolicy {
    public Decision decide(Input input) {
        String previousLevel = normalizeLevel(input.previousLevel);
        String currentLevel = normalizeLevel(input.currentLevel);
        int previousRank = levelRank(previousLevel);
        int currentRank = levelRank(currentLevel);

        if (!input.hasState && currentRank > 0) {
            return Decision.create("NEW_WARNING", "First entered " + currentLevel + " event state");
        }
        if (previousRank == 0 && currentRank > 0) {
            return Decision.create("NEW_WARNING", "State changed from NORMAL to " + currentLevel + " event state");
        }
        if (previousRank > 0 && currentRank == 0) {
            return Decision.create("RECOVERY", "Event state recovered from " + previousLevel + " to NORMAL");
        }
        if (currentRank > previousRank) {
            return Decision.create("LEVEL_UP", "Event level escalated from " + previousLevel + " to " + currentLevel);
        }
        if (currentRank > 0 && currentRank < previousRank) {
            return Decision.create("LEVEL_DOWN", "Event level downgraded from " + previousLevel + " to " + currentLevel);
        }
        if (currentRank > 0 && currentRank == previousRank) {
            long minutes = input.lastNotificationAt == null
                    ? Long.MAX_VALUE
                    : ChronoUnit.MINUTES.between(input.lastNotificationAt, now(input.now));
            int reminderMinutes = "RED".equals(currentLevel)
                    ? positive(input.redReminderMinutes, 180)
                    : positive(input.persistentReminderMinutes, 720);
            if (minutes >= positive(input.sameLevelCooldownMinutes, 60)
                    && isSignificantlyWorse(input.currentValue, input.lastNotificationValue,
                    input.significantChangePercent, input.significantChangeAbsolute)) {
                return Decision.create("SIGNIFICANT_WORSENING", currentLevel + " event level is unchanged, but the risk value increased significantly");
            }
            if (minutes >= reminderMinutes) {
                return Decision.create("PERSISTENT_REMINDER", currentLevel + " event has persisted for approximately " + minutes + " minutes without recovery");
            }
        }
        return Decision.suppress("NO_STATE_CHANGE", "State does not meet notification conditions");
    }

    public int levelRank(String level) {
        String value = normalizeLevel(level);
        if ("RED".equals(value)) return 3;
        if ("ORANGE".equals(value)) return 2;
        if ("YELLOW".equals(value)) return 1;
        return 0;
    }

    public String normalizeLevel(String level) {
        if (level == null || level.trim().isEmpty()) return "NORMAL";
        String value = level.trim().toUpperCase();
        return value;
    }

    private boolean isSignificantlyWorse(BigDecimal current, BigDecimal lastNotificationValue,
                                         BigDecimal percentThreshold, BigDecimal absoluteThreshold) {
        if (current == null || lastNotificationValue == null) return false;
        BigDecimal diff = current.subtract(lastNotificationValue);
        if (diff.compareTo(BigDecimal.ZERO) <= 0) return false;
        BigDecimal absolute = absoluteThreshold == null ? BigDecimal.ZERO : absoluteThreshold;
        if (absolute.compareTo(BigDecimal.ZERO) > 0 && diff.compareTo(absolute) >= 0) return true;
        BigDecimal percent = percentThreshold == null ? BigDecimal.valueOf(50) : percentThreshold;
        if (percent.compareTo(BigDecimal.ZERO) <= 0) return false;
        BigDecimal denominator = lastNotificationValue.abs().max(BigDecimal.ONE);
        BigDecimal actualPercent = diff.multiply(BigDecimal.valueOf(100)).divide(denominator, 6, RoundingMode.HALF_UP);
        return actualPercent.compareTo(percent) >= 0;
    }

    private int positive(int value, int fallback) {
        return value > 0 ? value : fallback;
    }

    private LocalDateTime now(LocalDateTime value) {
        return value == null ? LocalDateTime.now() : value;
    }

    public static class Input {
        public boolean hasState;
        public String previousLevel;
        public String currentLevel;
        public BigDecimal currentValue;
        public BigDecimal lastNotificationValue;
        public LocalDateTime lastNotificationAt;
        public LocalDateTime now;
        public int sameLevelCooldownMinutes;
        public int persistentReminderMinutes;
        public int redReminderMinutes;
        public BigDecimal significantChangePercent;
        public BigDecimal significantChangeAbsolute;
    }

    public static class Decision {
        public final boolean createTransition;
        public final String transitionType;
        public final String reason;

        private Decision(boolean createTransition, String transitionType, String reason) {
            this.createTransition = createTransition;
            this.transitionType = transitionType;
            this.reason = reason;
        }

        public static Decision create(String transitionType, String reason) {
            return new Decision(true, transitionType, reason);
        }

        public static Decision suppress(String transitionType, String reason) {
            return new Decision(false, transitionType, reason);
        }
    }
}

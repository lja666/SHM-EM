package mybatis.iem.em;

import mybatis.iem.em.modules.engineering.application.service.impl.EventNotificationDecisionPolicy;
import mybatis.iem.em.modules.engineering.application.service.impl.NotificationAddressUtils;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class EventNotificationDecisionPolicyTest {
    private final EventNotificationDecisionPolicy policy = new EventNotificationDecisionPolicy();
    private final LocalDateTime now = LocalDateTime.of(2026, 7, 6, 10, 0);

    @Test
    public void createsTransitionForFirstWarning() {
        EventNotificationDecisionPolicy.Input input = baseInput("NORMAL", "YELLOW");
        input.hasState = false;

        EventNotificationDecisionPolicy.Decision decision = policy.decide(input);

        assertTrue(decision.createTransition);
        assertEquals("NEW_WARNING", decision.transitionType);
    }

    @Test
    public void treatsNormalToWarningAsNewWarning() {
        EventNotificationDecisionPolicy.Input input = baseInput("NORMAL", "ORANGE");

        EventNotificationDecisionPolicy.Decision decision = policy.decide(input);

        assertTrue(decision.createTransition);
        assertEquals("NEW_WARNING", decision.transitionType);
    }

    @Test
    public void suppressesUnchangedLevelInsideCooldown() {
        EventNotificationDecisionPolicy.Input input = baseInput("ORANGE", "ORANGE");
        input.lastNotificationAt = now.minusMinutes(30);
        input.lastNotificationValue = new BigDecimal("10");
        input.currentValue = new BigDecimal("10.5");

        EventNotificationDecisionPolicy.Decision decision = policy.decide(input);

        assertFalse(decision.createTransition);
        assertEquals("NO_STATE_CHANGE", decision.transitionType);
    }

    @Test
    public void remindsForPersistentWarningAfterConfiguredWindow() {
        EventNotificationDecisionPolicy.Input input = baseInput("YELLOW", "YELLOW");
        input.lastNotificationAt = now.minusMinutes(800);
        input.lastNotificationValue = new BigDecimal("10");
        input.currentValue = new BigDecimal("10");

        EventNotificationDecisionPolicy.Decision decision = policy.decide(input);

        assertTrue(decision.createTransition);
        assertEquals("PERSISTENT_REMINDER", decision.transitionType);
    }

    @Test
    public void createsTransitionForSignificantWorseningAfterCooldown() {
        EventNotificationDecisionPolicy.Input input = baseInput("YELLOW", "YELLOW");
        input.lastNotificationAt = now.minusMinutes(70);
        input.lastNotificationValue = new BigDecimal("10");
        input.currentValue = new BigDecimal("16");

        EventNotificationDecisionPolicy.Decision decision = policy.decide(input);

        assertTrue(decision.createTransition);
        assertEquals("SIGNIFICANT_WORSENING", decision.transitionType);
    }

    @Test
    public void prefersWorseningReminderBeforePersistentReminder() {
        EventNotificationDecisionPolicy.Input input = baseInput("ORANGE", "ORANGE");
        input.lastNotificationAt = now.minusMinutes(900);
        input.lastNotificationValue = new BigDecimal("10");
        input.currentValue = new BigDecimal("18");

        EventNotificationDecisionPolicy.Decision decision = policy.decide(input);

        assertTrue(decision.createTransition);
        assertEquals("SIGNIFICANT_WORSENING", decision.transitionType);
    }

    @Test
    public void createsRecoveryTransition() {
        EventNotificationDecisionPolicy.Input input = baseInput("RED", "NORMAL");

        EventNotificationDecisionPolicy.Decision decision = policy.decide(input);

        assertTrue(decision.createTransition);
        assertEquals("RECOVERY", decision.transitionType);
    }

    @Test
    public void normalizesAndDeduplicatesEmailRecipients() {
        String[] recipients = NotificationAddressUtils.parseValidArray(
                "ops@example.com； invalid-address,owner@example.com\nops@example.com");

        assertArrayEquals(new String[] {"ops@example.com", "owner@example.com"}, recipients);
        assertEquals("ops@example.com,owner@example.com",
                NotificationAddressUtils.normalizeToCommaText("ops@example.com,owner@example.com"));
    }

    private EventNotificationDecisionPolicy.Input baseInput(String previousLevel, String currentLevel) {
        EventNotificationDecisionPolicy.Input input = new EventNotificationDecisionPolicy.Input();
        input.hasState = true;
        input.previousLevel = previousLevel;
        input.currentLevel = currentLevel;
        input.now = now;
        input.lastNotificationAt = now.minusMinutes(30);
        input.lastNotificationValue = new BigDecimal("10");
        input.currentValue = new BigDecimal("10");
        input.sameLevelCooldownMinutes = 60;
        input.persistentReminderMinutes = 720;
        input.redReminderMinutes = 180;
        input.significantChangePercent = new BigDecimal("50");
        input.significantChangeAbsolute = BigDecimal.ZERO;
        return input;
    }
}

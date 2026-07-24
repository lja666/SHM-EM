package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

public class ReproductionExecutionPolicyTest {
    @Test
    public void acceptsOnlyAnIsolatedDatabaseWithNotificationsDisabled() {
        MockEnvironment environment = new MockEnvironment();
        environment.setActiveProfiles("reproduce");
        ReproductionExecutionPolicy policy = new ReproductionExecutionPolicy(
                environment,
                true,
                "jdbc:mysql://localhost:3306/shm_em_reproduce_test?serverTimezone=Asia/Shanghai",
                "^shm_em_reproduce_[A-Za-z0-9_]+$",
                false, false, false, false);
        PredictionBatch batch = new PredictionBatch();
        batch.setBaseTime(LocalDateTime.of(2026, 6, 24, 10, 0));

        assertDoesNotThrow(() -> policy.assertAllowed(batch));
    }

    @Test
    public void rejectsARegularApplicationDatabase() {
        MockEnvironment environment = new MockEnvironment();
        environment.setActiveProfiles("reproduce");
        ReproductionExecutionPolicy policy = new ReproductionExecutionPolicy(
                environment,
                true,
                "jdbc:mysql://localhost:3306/shm_em?serverTimezone=Asia/Shanghai",
                "^shm_em_reproduce_[A-Za-z0-9_]+$",
                false, false, false, false);
        PredictionBatch batch = new PredictionBatch();
        batch.setBaseTime(LocalDateTime.of(2026, 6, 24, 10, 0));

        assertThrows(BusinessException.class, () -> policy.assertAllowed(batch));
    }
}

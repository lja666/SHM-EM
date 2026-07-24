package mybatis.iem.em.modules.engineering.application.service.impl;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class NotificationTaskScheduler {
    private static final Logger log = LoggerFactory.getLogger(NotificationTaskScheduler.class);

    private final NotificationTaskService taskService;

    @Value("${shm-em.notification.scheduler-enabled:false}")
    private boolean schedulerEnabled;
    @Value("${shm-em.notification.batch-size:20}")
    private int batchSize;

    public NotificationTaskScheduler(NotificationTaskService taskService) {
        this.taskService = taskService;
    }

    @Scheduled(fixedDelayString = "${shm-em.notification.fixed-delay-ms:5000}",
            initialDelayString = "${shm-em.notification.initial-delay-ms:10000}")
    public void run() {
        if (!schedulerEnabled) return;
        try {
            taskService.runPending(batchSize <= 0 ? 20 : batchSize);
        } catch (RuntimeException ex) {
            log.warn("SHM-EM notification scheduler failed: {}", ex.getMessage());
        }
    }
}

package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
import org.springframework.stereotype.Service;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class ReproductionExecutionPolicy {
    private static final Pattern JDBC_DATABASE = Pattern.compile("jdbc:mysql:(?://)?[^/]+/([^?;]+)");

    private final Environment environment;
    private final boolean executeEnabled;
    private final String databaseUrl;
    private final Pattern databaseNamePattern;
    private final boolean notificationEnabled;
    private final boolean taskCreateEnabled;
    private final boolean schedulerEnabled;
    private final boolean mailSendEnabled;

    public ReproductionExecutionPolicy(
            Environment environment,
            @Value("${shm-em.reproduction.execute-enabled:false}") boolean executeEnabled,
            @Value("${spring.datasource.druid.url}") String databaseUrl,
            @Value("${shm-em.reproduction.database-name-pattern:^shm_em_reproduce_[A-Za-z0-9_]+$}") String databaseNamePattern,
            @Value("${shm-em.notification.enabled:true}") boolean notificationEnabled,
            @Value("${shm-em.notification.task-create-enabled:true}") boolean taskCreateEnabled,
            @Value("${shm-em.notification.scheduler-enabled:false}") boolean schedulerEnabled,
            @Value("${shm-em.notification.mail-send-enabled:false}") boolean mailSendEnabled) {
        this.environment = environment;
        this.executeEnabled = executeEnabled;
        this.databaseUrl = databaseUrl;
        this.databaseNamePattern = Pattern.compile(databaseNamePattern);
        this.notificationEnabled = notificationEnabled;
        this.taskCreateEnabled = taskCreateEnabled;
        this.schedulerEnabled = schedulerEnabled;
        this.mailSendEnabled = mailSendEnabled;
    }

    public void assertAllowed(PredictionBatch batch) {
        if (!executeEnabled || !environment.acceptsProfiles(Profiles.of("reproduce"))) {
            throw new BusinessException("Reproduction execution is available only in the reproduce profile");
        }
        if (environment.acceptsProfiles(Profiles.of("prod", "production"))) {
            throw new BusinessException("Reproduction execution cannot run with a production profile");
        }
        String databaseName = databaseName(databaseUrl);
        if (!databaseNamePattern.matcher(databaseName).matches()) {
            throw new BusinessException("Reproduction execution requires an isolated reproduction database");
        }
        if (notificationEnabled || taskCreateEnabled || schedulerEnabled || mailSendEnabled) {
            throw new BusinessException("Reproduction execution requires all notification delivery paths to be disabled");
        }
        if (batch == null || batch.getBaseTime() == null) {
            throw new BusinessException("Reproduction execution requires a prediction batch with a scenario base time");
        }
    }

    private String databaseName(String url) {
        Matcher matcher = JDBC_DATABASE.matcher(url == null ? "" : url);
        if (!matcher.find()) {
            throw new BusinessException("Cannot determine the reproduction database from the datasource URL");
        }
        return matcher.group(1);
    }
}

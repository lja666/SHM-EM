package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;
import mybatis.iem.em.modules.engineering.domain.model.ProjectFutureState;

import java.time.LocalDateTime;

public interface ProjectFutureStateService {
    ProjectFutureState get(Long projectId,
                           Long batchId,
                           Integer horizonMinutes,
                           PredictionExecutionMode executionMode,
                           LocalDateTime referenceTime);
}

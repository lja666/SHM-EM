package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionGate;
import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionMode;

import java.time.LocalDateTime;

public interface PredictionExecutionGateService {
    PredictionExecutionGate inspect(Long batchId, PredictionExecutionMode mode, LocalDateTime referenceTime);

    PredictionExecutionGate evaluate(Long batchId, PredictionExecutionMode mode, LocalDateTime referenceTime);

    PredictionExecutionGate latest(Long batchId, PredictionExecutionMode mode);
}

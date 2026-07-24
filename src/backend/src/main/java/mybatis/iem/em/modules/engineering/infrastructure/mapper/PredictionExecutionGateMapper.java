package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.PredictionExecutionGate;
import org.apache.ibatis.annotations.Param;

public interface PredictionExecutionGateMapper {
    int insert(PredictionExecutionGate gate);

    PredictionExecutionGate selectByIdentity(@Param("batchId") Long batchId,
                                             @Param("executionMode") String executionMode,
                                             @Param("gateHash") String gateHash);

    PredictionExecutionGate selectLatest(@Param("batchId") Long batchId,
                                         @Param("executionMode") String executionMode);
}

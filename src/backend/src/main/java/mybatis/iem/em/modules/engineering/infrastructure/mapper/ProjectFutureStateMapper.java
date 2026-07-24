package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.FutureRiskThreshold;
import mybatis.iem.em.modules.engineering.domain.model.FutureStatePolicy;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

public interface ProjectFutureStateMapper {
    FutureStatePolicy selectActivePolicy(@Param("projectId") Long projectId);

    List<FutureRiskThreshold> selectRiskThresholds(@Param("projectId") Long projectId);

    List<Map<String, Object>> selectOpenObservedRiskCounts(@Param("projectId") Long projectId);

    List<Map<String, Object>> selectStationNames(@Param("projectId") Long projectId);
}

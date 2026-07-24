package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

public interface ProjectContextMapper {
    Map<String, Object> selectProjectSummary(@Param("projectId") Long projectId);

    List<Map<String, Object>> selectProjectCards();

    List<Map<String, Object>> selectStationTypeCounts(@Param("projectId") Long projectId);

    List<Map<String, Object>> selectInstrumentTypeCounts(@Param("projectId") Long projectId);

    List<Map<String, Object>> selectMetricCounts(@Param("projectId") Long projectId);

    List<Map<String, Object>> selectEventLevelCounts(@Param("projectId") Long projectId);

    Map<String, Object> selectDatasetManifest(@Param("projectId") Long projectId);
}

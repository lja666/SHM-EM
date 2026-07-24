package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.StationMetric;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface StationMetricMapper {
    List<StationMetric> selectList(@Param("projectId") Long projectId, @Param("limit") Integer limit);

    StationMetric selectById(@Param("id") Long id);
}






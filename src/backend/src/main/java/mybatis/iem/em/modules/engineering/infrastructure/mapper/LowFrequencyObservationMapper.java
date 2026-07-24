package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface LowFrequencyObservationMapper {
    List<LowFrequencyObservation> selectByRegistry(@Param("tableName") String tableName, @Param("query") ObservationQuery query, @Param("limit") Integer limit);
}






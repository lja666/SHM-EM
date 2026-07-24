package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.AccelerationWaveform;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface AccelerationWaveformMapper {
    List<AccelerationWaveform> selectByRegistry(@Param("tableName") String tableName, @Param("query") ObservationQuery query, @Param("limit") Integer limit);
}






package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.Station;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface StationMapper {
    List<Station> selectList(@Param("projectId") Long projectId, @Param("limit") Integer limit);

    Station selectById(@Param("id") Long id);
}






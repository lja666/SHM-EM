package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.Instrument;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface InstrumentMapper {
    List<Instrument> selectList(@Param("projectId") Long projectId, @Param("limit") Integer limit);

    Instrument selectById(@Param("id") Long id);
}






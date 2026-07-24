package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.Evidence;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface EvidenceMapper {
    List<Evidence> selectEvidence(@Param("projectId") Long projectId, @Param("limit") Integer limit);
}

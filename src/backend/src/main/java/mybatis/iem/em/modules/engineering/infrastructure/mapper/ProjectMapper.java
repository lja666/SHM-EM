package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.Project;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface ProjectMapper {
    List<Project> selectList(@Param("projectId") Long projectId, @Param("limit") Integer limit);

    Project selectById(@Param("id") Long id);

    Project selectByCode(@Param("projectCode") String projectCode);
}






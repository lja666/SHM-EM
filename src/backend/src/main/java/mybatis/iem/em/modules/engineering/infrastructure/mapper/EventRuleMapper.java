package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.EventRule;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface EventRuleMapper {
    List<EventRule> selectList(@Param("projectId") Long projectId, @Param("limit") Integer limit);

    EventRule selectById(@Param("id") Long id);

    EventRule selectByIdAndProject(@Param("id") Long id, @Param("projectId") Long projectId);
}






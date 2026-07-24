package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.Event;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

public interface EventMapper {
    List<Event> selectList(@Param("projectId") Long projectId, @Param("limit") Integer limit);

    List<Map<String, Object>> selectDeviceWarnings(@Param("projectId") Long projectId, @Param("limit") Integer limit);

    Event selectById(@Param("id") Long id);

    Event selectByIdAndProject(@Param("id") Long id, @Param("projectId") Long projectId);

    Event selectByCode(@Param("projectId") Long projectId, @Param("eventCode") String eventCode);

    int insert(Event event);

    int updateStatus(@Param("id") Long id,
                     @Param("status") String status,
                     @Param("operatorName") String operatorName);

    int updateLevel(@Param("id") Long id,
                    @Param("eventLevel") String eventLevel);
}






package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.EventPredictionTrace;
import org.apache.ibatis.annotations.Param;

public interface EventPredictionTraceMapper {
    EventPredictionTrace selectByEventId(@Param("eventId") Long eventId);

    int insert(EventPredictionTrace trace);

    int countByBatchId(@Param("batchId") Long batchId);
}

package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.ObservationTableRegistry;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface ObservationTableRegistryMapper {
    List<ObservationTableRegistry> selectList(@Param("projectId") Long projectId, @Param("limit") Integer limit);

    ObservationTableRegistry selectById(@Param("id") Long id);

    ObservationTableRegistry selectByCode(@Param("registryCode") String registryCode);

    ObservationTableRegistry selectBestMatch(@Param("projectId") Long projectId,
                                             @Param("instrumentId") Long instrumentId,
                                             @Param("instrumentType") String instrumentType,
                                             @Param("metricCode") String metricCode,
                                             @Param("expectedStorageMode") String expectedStorageMode);
}






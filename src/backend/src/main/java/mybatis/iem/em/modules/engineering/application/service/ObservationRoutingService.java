package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.ObservationTableRegistry;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;

public interface ObservationRoutingService {
    ObservationTableRegistry requireQueryableRegistry(String registryCode, String expectedStorageMode);

    ObservationTableRegistry requireQueryableRegistry(ObservationQuery query, String expectedStorageMode);
}






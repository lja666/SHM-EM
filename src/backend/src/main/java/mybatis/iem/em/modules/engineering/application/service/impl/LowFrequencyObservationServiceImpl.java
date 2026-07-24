package mybatis.iem.em.modules.engineering.application.service.impl;

import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;
import mybatis.iem.em.modules.engineering.domain.model.ObservationTableRegistry;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.LowFrequencyObservationMapper;
import mybatis.iem.em.modules.engineering.application.service.LowFrequencyObservationService;
import mybatis.iem.em.modules.engineering.application.service.ObservationRoutingService;
import mybatis.iem.em.modules.engineering.application.service.EngineeringConversionService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class LowFrequencyObservationServiceImpl implements LowFrequencyObservationService {
    private final ObservationRoutingService routingService;
    private final LowFrequencyObservationMapper mapper;
    private final EngineeringConversionService conversionService;

    public LowFrequencyObservationServiceImpl(ObservationRoutingService routingService, LowFrequencyObservationMapper mapper,
                                              EngineeringConversionService conversionService) {
        this.routingService = routingService;
        this.mapper = mapper;
        this.conversionService = conversionService;
    }

    @Override
    public List<LowFrequencyObservation> list(ObservationQuery query) {
        ObservationTableRegistry registry = routingService.requireQueryableRegistry(query, null);
        if (!"type_table".equals(registry.getStorageMode()) && !"feature_table".equals(registry.getStorageMode())) {
            throw new mybatis.iem.em.common.BusinessException("registry is not a low-frequency observation table: " + query.getRegistryCode());
        }
        List<LowFrequencyObservation> rows = mapper.selectByRegistry(registry.getPhysicalTableName(), query, normalizeLimit(query.getLimit()));
        rows.forEach(row -> row.setSourceRegistryCode(registry.getRegistryCode()));
        rows.forEach(conversionService::decorateStoredObservation);
        return rows;
    }

    private Integer normalizeLimit(Integer limit) {
        if (limit == null || limit <= 0) {
            return 200;
        }
        return Math.min(limit, 2000);
    }
}





